import os
import json
import base64
import threading
import logging
import re
import io
from datetime import datetime
from fastapi import FastAPI, Request, HTTPException
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, ImageMessage, TextSendMessage
from dotenv import load_dotenv
from openai import OpenAI
from PIL import Image, ImageOps

# นำเข้าโมดูลฐานข้อมูล (ที่เชื่อมกับ Supabase และมี RLS)
from src import db_handler
from src.cybow_reference import enforce_strict_cybow_standards

# โหลด Environment Variables
load_dotenv()
LINE_CHANNEL_ACCESS_TOKEN = os.getenv("LINE_CHANNEL_ACCESS_TOKEN")
LINE_CHANNEL_SECRET = os.getenv("LINE_CHANNEL_SECRET")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

# ตั้งค่า Logging Configuration
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('bot.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

app = FastAPI()
line_bot_api = LineBotApi(LINE_CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(LINE_CHANNEL_SECRET)

# ใช้ OpenAI SDK เชื่อมต่อ OpenRouter
client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=OPENROUTER_API_KEY
)

# เก็บสถานะการทำงานชั่วคราวของผู้ใช้
user_states = {}

# ---------------------------------------------------------
# 🌟 Data Standard: ค่าอ้างอิงจากแผ่น CYBOW 11M (พร้อมค่า RGB แบบละเอียด)
# อ้างอิงจาก: ค่ามาตรฐานตรวจปัสสาวะ.pdf - Approximated RGB values
# ---------------------------------------------------------
from src.standards import ALLOWED_VALUES
from src.image_diagnostics import prepare_image, image_quality, sample_regions
from src.strip_geometry import detect_geometry_regions
from src.ai_guided_regions import detect_ai_guided_regions
from src.strip_signal import detect_strip_signal_regions

# ---------------------------------------------------------
# 🖼️ Image Optimization (In-Memory Processing - Cloud-Native)
# ---------------------------------------------------------
def resize_image_to_base64_from_bytes(image_bytes: bytes, max_dimension: int = 1536) -> str:
    """ฟังก์ชันย่อภาพบน RAM โดยไม่พึ่งพา Harddisk (Cloud-Native & Faster)"""
    try:
        # โหลดรูปจาก Bytes โดยตรง (ไม่ต้องเขียนไฟล์)
        with Image.open(io.BytesIO(image_bytes)) as img:
            img = ImageOps.exif_transpose(img)
            width, height = img.size
            if max(width, height) > max_dimension:
                scaling_factor = max_dimension / float(max(width, height))
                new_size = (int(width * scaling_factor), int(height * scaling_factor))
                img = img.resize(new_size, Image.Resampling.LANCZOS)

            buffered = io.BytesIO()
            img.convert('RGB').save(buffered, format="JPEG", quality=95)
            return base64.b64encode(buffered.getvalue()).decode("utf-8")
    except Exception as e:
        logger.error(f"Image resize error: {e}")
        return None

# ---------------------------------------------------------
# 🛡️ Helper Function: Safe Float Parsing
# ---------------------------------------------------------
def extract_safe_float(value, default=0.0):
    """สกัดเฉพาะตัวเลขออกจากข้อความเพื่อป้องกัน ValueError"""
    try:
        val_str = str(value)
        # ดึงมาเฉพาะตัวเลขและจุดทศนิยม
        match = re.search(r'\d+\.?\d*', val_str)
        if match:
            return float(match.group())
        return default
    except Exception:
        return default

# ---------------------------------------------------------
# 🚀 Endpoints & LINE Webhook
# ---------------------------------------------------------
@app.on_event("startup")
def initialize_database_schema():
    """Apply idempotent schema migrations before accepting analysis jobs."""
    try:
        db_handler.init_db()
        logger.info("Database schema migration check completed")
    except Exception as exc:
        # Keep health endpoint available, but surface the problem clearly in logs;
        # inserts will still fail closed rather than silently losing diagnostics.
        logger.error("Database schema migration check failed: %s", exc)


@app.get("/")
def keep_alive():
    return {"status": "LHome Bot is awake and running!"}

@app.post("/webhook")
async def callback(request: Request):
    signature = request.headers.get("X-Line-Signature", "")
    body = await request.body()
    try:
        handler.handle(body.decode("utf-8"), signature)
    except InvalidSignatureError:
        raise HTTPException(status_code=400, detail="Invalid signature")
    return "OK"

@handler.add(MessageEvent, message=ImageMessage)
def handle_image(event):
    user_id = event.source.user_id
    message_id = event.message.id
    user_states[user_id] = {"step": "waiting_for_name", "image_id": message_id}
    line_bot_api.reply_message(
        event.reply_token,
        TextSendMessage(text="📸 ได้รับรูปแผ่นตรวจแล้วครับ\nกรุณาพิมพ์ชื่อ-นามสกุลของผู้ป่วย เพื่อบันทึกผลครับ")
    )

@handler.add(MessageEvent, message=TextMessage)
def handle_text(event):
    user_id = event.source.user_id
    text = event.message.text.strip()

    if user_id in user_states and user_states[user_id].get("step") == "waiting_for_name":
        patient_name = text
        image_id = user_states[user_id]["image_id"]

        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text=f"กำลังวิเคราะห์ผลตรวจของ {patient_name}...\nขั้นตอนนี้อาจใช้เวลาประมาณ 10-20 วินาที กรุณารอสักครู่ครับ ⏳")
        )

        del user_states[user_id]

        # ส่งงานให้ Background Thread เพื่อไม่ให้ LINE Timeout
        threading.Thread(target=process_image_with_ai, args=(image_id, user_id, patient_name)).start()

# ---------------------------------------------------------
# 🧠 AI Processing Logic (Production-Ready)
# ---------------------------------------------------------
def process_image_with_ai(image_id, user_id, patient_name):
    try:
        # 1. โหลดรูปจาก LINE เป็น Bytes บน RAM โดยตรง (Cloud-Native, ไม่สร้างไฟล์ขยะ)
        message_content = line_bot_api.get_message_content(image_id)
        image_bytes = b"".join([chunk for chunk in message_content.iter_content()])

        # 2. ย่อภาพและแปลงเป็น Base64 (In-Memory Processing)
        base64_image = resize_image_to_base64_from_bytes(image_bytes, max_dimension=1536)
        if not base64_image:
            raise ValueError("ไม่สามารถประมวลผลไฟล์ภาพได้")

        image = prepare_image(base64.b64decode(base64_image))
        quality = image_quality(image)
        if not quality["accepted"]:
            line_bot_api.push_message(user_id, TextSendMessage(
                text="กรุณาถ่ายภาพใหม่: " + ", ".join(quality["reasons"])))
            return
        system_prompt = """
Read a CYBOW 11M urine reagent strip. The photo MAY contain only the test strip; a manufacturer color chart is NOT required in the same photo.
First identify the strip orientation and all 11 reagent pads. Use your learned visual knowledge of the CYBOW 11M manufacturer scale to classify each pad only when the pad is clearly visible.
Do not require a chart to be visible. Do not reject a strip-only photo merely because the chart is absent.
If the strip is too small, blurred, overexposed, the orientation is uncertain, fewer than 11 pads can be located, or a particular result cannot be read reliably, return null for that result. Never replace unknown results with negative.
Return a single JSON object using these result keys and allowed labels:
""" + json.dumps(ALLOWED_VALUES, ensure_ascii=False) + """
Also return pad_regions: a dictionary keyed by the same parameter names, each value
[x1,y1,x2,y2] normalized to 0..1 for a tight rectangle INSIDE that reagent pad,
excluding borders and neighboring pads. Use null when the location is uncertain.
Do not return guessed RGB or confidence percentages. Do not infer patient diagnoses.
"""

        # Request image analysis; model can be configured by the deployment.
        response = client.chat.completions.create(
            model=os.getenv("VISION_MODEL", "anthropic/claude-4.5-sonnet"),
            messages=[
                {"role": "system", "content": system_prompt},
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": "Read this CYBOW 11M strip. A color chart may be absent; analyze a strip-only photo when all 11 pads are clearly identifiable. Return only the JSON requested by the system."},
                        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}}
                    ]
                }
            ],
            max_tokens=2000,  # เพิ่ม token สำหรับ Claude ที่ตอบยาวกว่า
            temperature=0,    # Reduces variability; does not guarantee identical responses.
            # หมายเหตุ: Claude API ไม่รองรับ response_format และ seed parameters ผ่าน OpenRouter
            # แต่ temperature=0 ช่วยให้ผลลัพธ์สม่ำเสมอมากขึ้น
        )

        result_text = response.choices[0].message.content


        # 5. สกัด JSON อย่างทนทาน (Robust JSON Extraction)
        # หาตำแหน่งตั้งแต่ { ตัวแรก จนถึง } ตัวสุดท้าย
        json_match = re.search(r'\{.*\}', result_text, re.DOTALL)
        if json_match:
            raw_data = json.loads(json_match.group())
        else:
            raise ValueError("AI ไม่ได้ส่งข้อมูลกลับมาในรูปแบบ JSON")

        # Validate labels without inventing missing results.
        data = enforce_strict_cybow_standards(raw_data)
        if not data["is_valid"]:
            line_bot_api.push_message(user_id, TextSendMessage(
                text="ยังบันทึกผลไม่ได้ กรุณาถ่ายแผ่น CYBOW 11M ให้เต็มภาพ แสงสม่ำเสมอ และเห็นแถบสีทั้ง 11 ช่องชัดเจน ช่องที่อ่านไม่ได้: "
                     + ", ".join(data["validation_errors"])))
            return
        ai_regions = raw_data.get("pad_regions")
        geometry = detect_geometry_regions(image, ai_regions)
        signal = None
        guided = None
        if geometry.get("accepted"):
            selected_regions = geometry.get("regions")
            region_source = geometry.get("source")
        else:
            # Second stage: optimize one coherent strip model from a 1-D visual
            # signal. This is preferred over independent per-pad local searches.
            signal = detect_strip_signal_regions(image, ai_regions)
            if signal.get("accepted"):
                selected_regions = signal.get("regions")
                region_source = signal.get("source")
            else:
                # Tertiary fallback: independent pixel anchors with strict residual
                # gating. AI boxes are never sampled directly.
                guided = detect_ai_guided_regions(image, ai_regions)
                if not guided.get("accepted"):
                    logger.warning("Rejected image localization: geometry=%s signal=%s guided=%s", geometry, signal, guided)
                    raise ValueError("ไม่สามารถระบุตำแหน่งแผ่นสีทั้ง 11 ช่องจากพิกเซลได้อย่างปลอดภัย กรุณาถ่ายภาพใหม่ให้แถบตรวจใหญ่และชัดเจนขึ้น")
                selected_regions = guided.get("regions")
                region_source = guided.get("source")
        diagnostics = sample_regions(image, selected_regions, data)
        diagnostics["image_quality"] = quality
        diagnostics["geometry_detection"] = geometry
        diagnostics["signal_detection"] = signal
        diagnostics["guided_detection"] = guided
        diagnostics["region_source"] = region_source
        logger.info("geometry_detection %s", json.dumps({
            "region_source": diagnostics["region_source"],
            "geometry": geometry,
            "signal": signal,
            "guided": guided,
            "ai_pad_regions": ai_regions,
            "sampled_regions": diagnostics.get("sampled_regions"),
            "detected_rgb": diagnostics.get("detected_rgb"),
            "normalized_rgb": diagnostics.get("normalized_rgb"),
            "normalization": diagnostics.get("normalization"),
            "roi_quality": diagnostics.get("roi_quality"),
            "result_fusion": diagnostics.get("result_fusion")
        }, ensure_ascii=False, allow_nan=False))
        if not diagnostics.get("roi_consistency", {}).get("accepted", True):
            logger.warning("Rejected implausible pad ROIs: %s", diagnostics.get("roi_consistency"))
            raise ValueError("ตำแหน่งช่องทดสอบไม่สอดคล้องกับสีในภาพ กรุณาถ่ายภาพใหม่ให้แถบตรวจชัดและใกล้ขึ้น")
        fusion = diagnostics.get("result_fusion", {})
        if not fusion.get("accepted", False):
            review = ", ".join(fusion.get("review", []))
            logger.warning("Rejected unresolved pixel/AI fusion: %s", fusion)
            raise ValueError(f"ยังไม่สามารถยืนยันค่าสีได้อย่างปลอดภัยในช่อง: {review} กรุณาถ่ายภาพใหม่หรือให้ผู้ตรวจสอบผล")
        borderline = fusion.get("borderline", [])
        # Pixel evidence may safely correct an AI label only when calibrated-distance
        # and perceptual-distance gates pass. Borderline values are retained with
        # an explicit review warning; Blood remains AI-led for spotted patterns.
        resolved = fusion.get("resolved_results", {})
        for param in ALLOWED_VALUES:
            if param in resolved and resolved[param] is not None:
                data[param] = resolved[param]
        if len(diagnostics["detected_rgb"]) != len(ALLOWED_VALUES):
            line_bot_api.push_message(user_id, TextSendMessage(
                text="ระบุตำแหน่งแถบสีได้ไม่ครบ กรุณาถ่ายแผ่น CYBOW 11M ให้ใกล้ขึ้น เห็นครบทั้ง 11 ช่อง และหลีกเลี่ยงแสงสะท้อน"))
            return
        data.update(diagnostics)
        # Build the summary from validated labels so it cannot contradict the saved values.
        data["clinical_summary"] = "; ".join(
            p + ": " + data[p] + (" [borderline]" if p in borderline else "")
            for p in ALLOWED_VALUES)
        data["clinical_bullets"] = ["ผลอ่านจากภาพ ต้องตรวจยืนยันกับแผ่นตรวจจริง"]
        if borderline:
            data["clinical_bullets"].append("ค่าก้ำกึ่งที่ควรตรวจเทียบแถบจริง: " + ", ".join(borderline))
        logger.info("strip_diagnostics %s", json.dumps(diagnostics, ensure_ascii=False, allow_nan=False))

        # 6. บันทึกลง Database (ป้องกัน ValueError ด้วย extract_safe_float)
        date_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # 🌟 ใช้ Helper Function แทนการ float() โดยตรง
        sg_val = extract_safe_float(data.get('specific_gravity'), 0.0)
        ph_val = extract_safe_float(data.get('ph'), 0.0)

        success = db_handler.insert_record(
            date=date_str,
            urobilinogen=data.get('urobilinogen', 'N/A'),
            glucose=data.get('glucose', 'N/A'),
            bilirubin=data.get('bilirubin', 'N/A'),
            ketones=data.get('ketones', 'N/A'),
            specific_gravity=sg_val,
            blood=data.get('blood', 'N/A'),
            ph=ph_val,
            protein=data.get('protein', 'N/A'),
            nitrite=data.get('nitrite', 'N/A'),
            leukocytes=data.get('leukocytes', 'N/A'),
            ascorbic_acid=data.get('ascorbic_acid', 'N/A'),
            notes=patient_name,
            clinical_summary=data.get('clinical_summary', 'ไม่สามารถสรุปผลได้แน่ชัด'),
            # 🌟 ensure_ascii=False เพื่อบันทึกภาษาไทยแท้ (ไม่ใช่ \u0e...)
            clinical_bullets=data['clinical_bullets'],
            diagnostics=diagnostics
        )

        if success:
            # สร้างข้อความแสดงผล รวมถึง overall confidence

            reply_msg = (
                f"✅ บันทึกผลตรวจสำเร็จ!\n👤 คนไข้: {patient_name}\n\n"
                f"📝 สรุปผล:\n{data.get('clinical_summary', '')}\n\n"
                "คะแนนความแม่นยำ: ยังไม่มีข้อมูลสอบเทียบ\n"
                + (("⚠️ ค่าก้ำกึ่งจากภาพ: " + ", ".join(borderline) + "\nควรเทียบกับแถบจริงก่อนใช้ประกอบการตัดสินใจ\n\n") if borderline else "\n")
                + f"สามารถกดดูรายงาน PDF ฉบับเต็มได้ที่ระบบ LHome Dashboard ครับ!"
            )
            line_bot_api.push_message(user_id, TextSendMessage(text=reply_msg))
        else:
            raise ValueError("บันทึกข้อมูลลง Database ล้มเหลว")

    except Exception as e:
        error_msg = str(e)
        logger.error(f"Error processing image: {error_msg}")

        if ("ตำแหน่งแผ่นสี" in error_msg or "ตำแหน่งช่องทดสอบ" in error_msg or
                "ผล AI ขัดแย้งกับสี" in error_msg or "ยังไม่สามารถยืนยันค่าสี" in error_msg):
            user_message = "📷 ยังอ่านตำแหน่ง/สีของแถบ CYBOW 11M ได้ไม่ปลอดภัย\n" + error_msg
        else:
            user_message = "❌ ระบบวิเคราะห์ขัดข้อง กรุณาลองใหม่หรือติดต่อผู้ดูแลระบบ"
        line_bot_api.push_message(user_id, TextSendMessage(text=user_message))
