import os
import json
import base64
import tempfile
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
from PIL import Image

# นำเข้าโมดูลฐานข้อมูล (ที่เชื่อมกับ Supabase และมี RLS)
from src import db_handler

# โหลด Environment Variables
load_dotenv()
LINE_CHANNEL_ACCESS_TOKEN = os.getenv("LINE_CHANNEL_ACCESS_TOKEN")
LINE_CHANNEL_SECRET = os.getenv("LINE_CHANNEL_SECRET")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

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
CYBOW_11M_STANDARDS = {
    "urobilinogen": [
        {"label": "0.1 (Normal)", "rgb": (251, 226, 212), "value": "0.1 Normal"},
        {"label": "1 (16)", "rgb": (250, 187, 186), "value": "1(16)"},
        {"label": "2 (33)", "rgb": (244, 151, 158), "value": "2(33)"},
        {"label": "4 (66)", "rgb": (233, 114, 137), "value": "4(66)"},
        {"label": "8 (131)", "rgb": (222, 77, 115), "value": "8(131)"}
    ],
    "glucose": [
        {"label": "neg", "rgb": (118, 194, 201), "value": "neg."},
        {"label": "± 100", "rgb": (148, 199, 126), "value": "±100(5.5)"},
        {"label": "+ 250", "rgb": (137, 168, 64), "value": "+250(14)"},
        {"label": "++ 500", "rgb": (120, 111, 48), "value": "++500(28)"},
        {"label": "+++ 1000", "rgb": (99, 61, 43), "value": "+++1000(55)"}
    ],
    "bilirubin": [
        {"label": "neg", "rgb": (242, 222, 210), "value": "neg."},
        {"label": "+", "rgb": (233, 190, 197), "value": "+"},
        {"label": "++", "rgb": (214, 145, 172), "value": "++"},
        {"label": "+++", "rgb": (163, 76, 122), "value": "+++"}
    ],
    "ketones": [
        {"label": "neg", "rgb": (242, 222, 210), "value": "neg."},
        {"label": "± 5", "rgb": (233, 190, 197), "value": "±5(0.5)"},
        {"label": "+ 15", "rgb": (214, 145, 172), "value": "+15(1.5)"},
        {"label": "++ 40", "rgb": (163, 76, 122), "value": "++40(3.9)"},
        {"label": "+++ 100", "rgb": (112, 43, 75), "value": "+++100(10)"}
    ],
    "ph": [
        {"label": "5.0", "rgb": (236, 136, 75), "value": "5"},
        {"label": "6.0", "rgb": (238, 179, 74), "value": "6"},
        {"label": "6.5", "rgb": (207, 189, 64), "value": "6.5"},
        {"label": "7.0", "rgb": (153, 173, 56), "value": "7"},
        {"label": "8.0", "rgb": (59, 131, 101), "value": "8"},
        {"label": "9.0", "rgb": (49, 102, 133), "value": "9"}
    ],
    "protein": [
        {"label": "neg", "rgb": (237, 227, 85), "value": "neg."},
        {"label": "trace", "rgb": (204, 216, 92), "value": "trace"},
        {"label": "+ 30", "rgb": (166, 198, 89), "value": "+30(0.3)"},
        {"label": "++ 100", "rgb": (123, 179, 90), "value": "++100(1.0)"},
        {"label": "+++ 300", "rgb": (85, 160, 93), "value": "+++300(3.0)"},
        {"label": "++++ 1000", "rgb": (70, 140, 115), "value": "++++1000(10)"}
    ],
    "blood": [
        {"label": "neg", "rgb": (245, 245, 245), "value": "neg."},
        {"label": "Hemolysis +10 Ery/µL", "rgb": (148, 199, 126), "value": "Hemolysis +10"},
        {"label": "Hemolysis ++50 Ery/µL", "rgb": (120, 111, 48), "value": "Hemolysis ++50"},
        {"label": "Hemolysis +++250 Ery/µL", "rgb": (99, 61, 43), "value": "Hemolysis +++250"},
        {"label": "Non-Hemolysis +10", "rgb": (148, 199, 126), "value": "Non Hemolysis +10"},
        {"label": "Non-Hemolysis ++50", "rgb": (120, 111, 48), "value": "Non Hemolysis ++50"}
    ],
    "nitrite": [
        {"label": "neg", "rgb": (245, 240, 235), "value": "neg."},
        {"label": "trace", "rgb": (234, 210, 215), "value": "trace"},
        {"label": "pos", "rgb": (220, 180, 195), "value": "pos."}
    ],
    "leukocytes": [
        {"label": "neg", "rgb": (240, 230, 235), "value": "neg."},
        {"label": "+25 Leu/µL", "rgb": (225, 205, 220), "value": "+25"},
        {"label": "++75 Leu/µL", "rgb": (200, 170, 200), "value": "++75"},
        {"label": "+++500 Leu/µL", "rgb": (175, 140, 180), "value": "+++500"}
    ],
    "ascorbic_acid": [
        {"label": "neg", "rgb": (230, 235, 210), "value": "neg."},
        {"label": "+20 mg/dL", "rgb": (210, 215, 185), "value": "+20(1.2)"},
        {"label": "++40 mg/dL", "rgb": (190, 195, 160), "value": "++40(2.4)"}
    ],
    "specific_gravity": [
        {"label": "1.000", "rgb": (180, 200, 180), "value": "1.000"},
        {"label": "1.005", "rgb": (175, 195, 175), "value": "1.005"},
        {"label": "1.010", "rgb": (170, 190, 170), "value": "1.010"},
        {"label": "1.015", "rgb": (165, 185, 165), "value": "1.015"},
        {"label": "1.020", "rgb": (160, 180, 160), "value": "1.020"},
        {"label": "1.025", "rgb": (155, 175, 155), "value": "1.025"},
        {"label": "1.030", "rgb": (150, 170, 150), "value": "1.030"}
    ]
}

# ---------------------------------------------------------
# 🖼️ Image Optimization (ป้องกัน Error 402 Token ไม่พอ)
# ---------------------------------------------------------
def resize_image_to_base64(image_path: str, max_dimension: int = 1536) -> str:
    """ฟังก์ชันย่อภาพแบบคงสัดส่วน (ปรับความคมชัดสูงสำหรับงาน Medical Vision)"""
    try:
        with Image.open(image_path) as img:
            width, height = img.size
            if max(width, height) > max_dimension:
                scaling_factor = max_dimension / float(max(width, height))
                new_size = (int(width * scaling_factor), int(height * scaling_factor))
                img = img.resize(new_size, Image.Resampling.LANCZOS)
            
            buffered = io.BytesIO()
            # 🌟 แก้ไขตรงนี้: เพิ่ม quality จาก 85 เป็น 95 เพื่อรักษาสีให้ชัดเจน
            img.convert('RGB').save(buffered, format="JPEG", quality=95)
            img_str = base64.b64encode(buffered.getvalue()).decode("utf-8")
            return img_str
    except Exception as e:
        logging.error(f"Image resize error: {e}")
        return None
        
# ---------------------------------------------------------
# 🚀 Endpoints & LINE Webhook
# ---------------------------------------------------------
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
# 🧠 AI Processing Logic
# ---------------------------------------------------------
def process_image_with_ai(image_id, user_id, patient_name):
    temp_path = None
    try:
        # 1. โหลดรูปจาก LINE
        message_content = line_bot_api.get_message_content(image_id)
        with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as tf:
            for chunk in message_content.iter_content():
                tf.write(chunk)
            temp_path = tf.name

        # 2. ย่อภาพและแปลงเป็น Base64 (ใช้ความละเอียด 1536 เพื่อให้ AI เห็นสีชัดที่สุด)
        base64_image = resize_image_to_base64(temp_path, max_dimension=1536)
        if not base64_image:
            raise ValueError("ไม่สามารถประมวลผลไฟล์ภาพได้")

        # 🌟 3. สร้าง Detailed System Prompt พร้อมข้อมูล RGB แบบละเอียด
        def format_standards_for_prompt():
            """แปลง CYBOW_11M_STANDARDS เป็น text ที่อ่านง่ายสำหรับ AI"""
            formatted = []
            for param, levels in CYBOW_11M_STANDARDS.items():
                param_info = f"\n{param.upper()}:"
                for level in levels:
                    param_info += f"\n  • {level['label']}: RGB{level['rgb']} → ใช้ค่า '{level['value']}'"
                formatted.append(param_info)
            return "\n".join(formatted)

        system_prompt = f"""
        คุณคือผู้เชี่ยวชาญด้านเทคนิคการแพทย์และการวิเคราะห์แผ่นตรวจปัสสาวะ CYBOW 11M ระดับ Medical-Grade AI Vision

        ═══════════════════════════════════════════════════════════════════
        🎯 CRITICAL RULES (กฎเหล็กที่ต้องปฏิบัติ):
        ═══════════════════════════════════════════════════════════════════

        1. DETERMINISTIC ANALYSIS (การวิเคราะห์แบบสม่ำเสมอ):
           - ภาพเดียวกันต้องให้ผลเดียวกันเสมอ (100% reproducible)
           - ห้ามใช้การประมาณ ห้ามเดา ต้องอิงจากค่ามาตรฐานเท่านั้น
           - วิเคราะห์แบบเป็นระบบ ไม่สุ่ม ไม่แปรปรวน

        2. COLOR MATCHING PRECISION (การเทียบสีแบบแม่นยำ):
           - เปรียบเทียบสีแต่ละแถบกับค่า RGB มาตรฐาน (ด้านล่าง)
           - ใช้หลักการ Euclidean Distance: sqrt((R1-R2)² + (G1-G2)² + (B1-B2)²)
           - เลือกค่าที่มี distance น้อยที่สุด (สีใกล้เคียงที่สุด)

        3. SYSTEMATIC READING (อ่านแบบเป็นระบบ):
           - อ่านแถบสีจากซ้ายไปขวา: URO → GLU → BIL → KET → SG → BLO → pH → PRO → NIT → LEU → ASC
           - แต่ละแถบต้องเลือกค่าจาก reference ด้านล่างเท่านั้น
           - ห้ามตอบ N/A ถ้าเห็นแถบสี ต้องเลือกค่าที่ใกล้เคียงที่สุด

        ═══════════════════════════════════════════════════════════════════
        📊 CYBOW 11M COLOR REFERENCE STANDARDS (ค่ามาตรฐานอ้างอิง):
        ═══════════════════════════════════════════════════════════════════
        {format_standards_for_prompt()}

        ═══════════════════════════════════════════════════════════════════
        🔬 การวิเคราะห์ทางคลินิก (CLINICAL ANALYSIS):
        ═══════════════════════════════════════════════════════════════════

        'clinical_summary': สรุปผลการตรวจ 1-2 ประโยคที่ชัดเจน ตัวอย่าง:
           - "ผลตรวจปกติทุกค่า ไม่พบความผิดปกติ"
           - "พบความผิดปกติ: ตรวจพบน้ำตาลในปัสสาวะระดับสูง และมีโปรตีนรั่วไหล"

        'clinical_bullets': Array ของข้อความวิเคราะห์แบบละเอียด (3-5 ข้อ) ใช้รูปแบบ "หัวข้อ: รายละเอียด"
           ตัวอย่าง:
           - "สัญญาณการติดเชื้อทางเดินปัสสาวะ (UTI): พบเม็ดเลือดขาว (LEU) +25 Leu/µL และไนไตรต์ (NIT) เป็นบวก บ่งชี้การติดเชื้อแบคทีเรีย"
           - "ภาวะขาดน้ำ: พบความถ่วงจำเพาะ (SG) สูงถึง 1.030 ร่วมกับโปรตีนรั่วไหล แนะนำให้ดื่มน้ำเพิ่มขึ้น"
           - "ความเป็นกรด-ด่างของปัสสาวะ: pH 6.0 (Acidic) อยู่ในเกณฑ์ปกติ"
           - "คำแนะนำ: แนะนำให้พบแพทย์เพื่อตรวจสอบเพิ่มเติม โดยเฉพาะในกรณีที่มีอาการปัสสาวะขุ่น ปวดขณะปัสสาวะ หรือปัสสาวะบ่อย"

        ═══════════════════════════════════════════════════════════════════
        📋 OUTPUT FORMAT (รูปแบบการตอบกลับ):
        ═══════════════════════════════════════════════════════════════════

        ตอบกลับเป็น JSON เท่านั้น ตามโครงสร้างนี้:
        {{
            "urobilinogen": "0.1 Normal",
            "glucose": "neg.",
            "bilirubin": "neg.",
            "ketones": "neg.",
            "specific_gravity": "1.020",
            "blood": "neg.",
            "ph": "6",
            "protein": "neg.",
            "nitrite": "neg.",
            "leukocytes": "neg.",
            "ascorbic_acid": "neg.",
            "clinical_summary": "ผลตรวจปกติทุกค่า ไม่พบความผิดปกติ",
            "clinical_bullets": [
                "ผลตรวจทั่วไป: ไม่พบน้ำตาล โปรตีน เลือด หรือเม็ดเลือดขาวในปัสสาวะ",
                "ความถ่วงจำเพาะและ pH: อยู่ในเกณฑ์ปกติ บ่งชี้การทำงานของไตปกติ",
                "คำแนะนำ: ดูแลสุขภาพต่อไป ดื่มน้ำให้เพียงพอ ตรวจสุขภาพประจำปีตามปกติ"
            ]
        }}

        **สำคัญ**: ค่าที่ตอบต้องเลือกจาก 'value' ใน REFERENCE ด้านบนเท่านั้น ห้ามแต่งเอง!
        """

        # 🌟 4. เรียก OpenRouter API (Claude Sonnet 4.5 - ความแม่นยำสูงสุดในการวิเคราะห์ภาพทางการแพทย์)
        response = client.chat.completions.create(
            model="anthropic/claude-sonnet-4.5",  # Claude Sonnet 4.5 - Medical-grade vision analysis
            messages=[
                {"role": "system", "content": system_prompt},
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": "อ่านค่าผลตรวจจากรูปแผ่นตรวจปัสสาวะนี้อย่างเป็นระบบและแม่นยำ วิเคราะห์สีแต่ละแถบอย่างละเอียด\n\n**สำคัญ**: ตอบกลับเป็น valid JSON เท่านั้น ไม่ต้องมี markdown code blocks"},
                        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}}
                    ]
                }
            ],
            max_tokens=2000,  # เพิ่ม token สำหรับ Claude ที่ตอบยาวกว่า
            temperature=0,    # 🔥 CRITICAL: deterministic output
            # หมายเหตุ: Claude API ไม่รองรับ response_format และ seed parameters ผ่าน OpenRouter
            # แต่ temperature=0 ช่วยให้ผลลัพธ์สม่ำเสมอมากขึ้น
        )

        result_text = response.choices[0].message.content
        print(f"--- AI RESPONSE DEBUG ---\n{result_text}\n-------------------------")
        
        # 5. ทำความสะอาดข้อความและแปลงเป็น JSON
        cleaned_text = re.sub(r'```json\n|\n```|```', '', result_text).strip()
        data = json.loads(cleaned_text)

        # 6. บันทึกลง Database
        date_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        success = db_handler.insert_record(
            date=date_str, 
            urobilinogen=data.get('urobilinogen', 'N/A'), 
            glucose=data.get('glucose', 'N/A'), 
            bilirubin=data.get('bilirubin', 'N/A'), 
            ketones=data.get('ketones', 'N/A'), 
            specific_gravity=float(data.get('specific_gravity', 0.0)) if data.get('specific_gravity') != 'N/A' else 0.0, 
            blood=data.get('blood', 'N/A'), 
            ph=float(data.get('ph', 0.0)) if data.get('ph') != 'N/A' else 0.0, 
            protein=data.get('protein', 'N/A'), 
            nitrite=data.get('nitrite', 'N/A'), 
            leukocytes=data.get('leukocytes', 'N/A'), 
            ascorbic_acid=data.get('ascorbic_acid', 'N/A'), 
            notes=patient_name,
            clinical_summary=data.get('clinical_summary', 'ไม่สามารถสรุปผลได้แน่ชัด'),
            clinical_bullets=json.dumps(data.get('clinical_bullets', [])) # แปลงเป็น string ก่อนเก็บลง DB
        )

        if success:
            reply_msg = (
                f"✅ บันทึกผลตรวจสำเร็จ!\n👤 คนไข้: {patient_name}\n\n"
                f"📝 สรุปผล:\n{data.get('clinical_summary', '')}\n\n"
                f"สามารถกดดูรายงาน PDF ฉบับเต็มได้ที่ระบบ LHome Dashboard ครับ!"
            )
            line_bot_api.push_message(user_id, TextSendMessage(text=reply_msg))
        else:
            raise ValueError("บันทึกข้อมูลลง Database ล้มเหลว")

    except Exception as e:
        error_msg = str(e)
        logging.error(f"Error processing image: {error_msg}")
        
        line_bot_api.push_message(
            user_id,
            TextSendMessage(text=f"❌ ขออภัยครับ ระบบวิเคราะห์ขัดข้อง\nสาเหตุ: {error_msg}\nกรุณาลองส่งรูปใหม่อีกครั้งครับ")
        )
    finally:
        if temp_path and os.path.exists(temp_path):
            os.remove(temp_path)