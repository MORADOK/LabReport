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
from PIL import Image

# นำเข้าโมดูลฐานข้อมูล (ที่เชื่อมกับ Supabase และมี RLS)
from src import db_handler
from src.cybow_reference import CYBOW_11M_EXACT_REFERENCE

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
# 🖼️ Image Optimization (In-Memory Processing - Cloud-Native)
# ---------------------------------------------------------
def resize_image_to_base64_from_bytes(image_bytes: bytes, max_dimension: int = 1536) -> str:
    """ฟังก์ชันย่อภาพบน RAM โดยไม่พึ่งพา Harddisk (Cloud-Native & Faster)"""
    try:
        # โหลดรูปจาก Bytes โดยตรง (ไม่ต้องเขียนไฟล์)
        with Image.open(io.BytesIO(image_bytes)) as img:
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

        # 🌟 3. สร้าง Detailed System Prompt พร้อมข้อมูล RGB และคำอธิบายสีแบบละเอียด
        def format_standards_for_prompt():
            """
            แปลง CYBOW_11M_EXACT_REFERENCE เป็นคำแนะนำการอ่านสีแบบละเอียดสำหรับ AI
            รวมข้อมูล RGB จาก CYBOW_11M_STANDARDS และคำอธิบายสีจาก CYBOW_11M_EXACT_REFERENCE
            """
            formatted = []

            # แปลงชื่อพารามิเตอร์ให้ตรงกันระหว่าง 2 dictionaries
            param_mapping = {
                "urobilinogen": "URO",
                "glucose": "GLU",
                "bilirubin": "BIL",
                "ketones": "KET",
                "specific_gravity": "SG",
                "blood": "BLO",
                "ph": "pH",
                "protein": "PRO",
                "nitrite": "NIT",
                "leukocytes": "LEU",
                "ascorbic_acid": "ASC"
            }

            for param_old, param_code in param_mapping.items():
                if param_old not in CYBOW_11M_STANDARDS:
                    continue

                rgb_levels = CYBOW_11M_STANDARDS[param_old]
                ref_data = CYBOW_11M_EXACT_REFERENCE.get(param_code, {})

                # หัวข้อพารามิเตอร์
                param_info = f"\n📍 {param_code} ({param_old.upper()}):"

                # รายละเอียดสีแต่ละระดับ
                for rgb_level in rgb_levels:
                    param_info += f"\n  • {rgb_level['label']}: RGB{rgb_level['rgb']} → ตอบ '{rgb_level['value']}'"

                # เพิ่มคำอธิบายสีจาก reference (ถ้ามี)
                if "color_normal" in ref_data:
                    param_info += f"\n  💡 สีปกติ (Normal): {ref_data['color_normal']}"
                if "color_warning" in ref_data:
                    param_info += f"\n  ⚠️ สีผิดปกติระดับต่ำ (Warning): {ref_data['color_warning']}"
                if "color_critical" in ref_data:
                    param_info += f"\n  🚨 สีผิดปกติระดับสูง (Critical): {ref_data['color_critical']}"
                if "color_high" in ref_data:
                    param_info += f"\n  ⚠️ สีผิดปกติ (High): {ref_data['color_high']}"

                # สำหรับ pH มีหลายสี
                if param_code == "pH":
                    param_info += f"\n  🍊 สีเป็นกรด (Acidic, pH<7): {ref_data.get('color_acidic', 'ส้ม')}"
                    param_info += f"\n  🟡 สีกลางๆ (Neutral, pH=7): {ref_data.get('color_neutral', 'เหลือง')}"
                    param_info += f"\n  🟢 สีเป็นด่าง (Alkaline, pH>7): {ref_data.get('color_alkaline', 'เขียว/ฟ้า')}"

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

        3. SPATIAL GROUNDING - การอ้างอิงตำแหน่ง (สำคัญมาก!):
           แผ่นตรวจมี 11 แถบสีเรียงจาก "ซ้ายไปขวา" ตามลำดับนี้:
           - แถบที่ 1 (ซ้ายสุด): URO (ยูโรบิลิโนเจน)
           - แถบที่ 2: GLU (กลูโคส)
           - แถบที่ 3: BIL (บิลิรูบิน)
           - แถบที่ 4: KET (คีโตน)
           - แถบที่ 5: SG (ความถ่วงจำเพาะ)
           - แถบที่ 6: BLO (เลือด) -> **ถ้าเป็นสีเขียว/เขียวเข้ม = ผิดปกติ!**
           - แถบที่ 7: pH (ความเป็นกรด-ด่าง)
           - แถบที่ 8: PRO (โปรตีน) -> **ถ้าเป็นสีเขียว = ผิดปกติ!**
           - แถบที่ 9: NIT (ไนไตรต์) -> **ถ้าเป็นสีชมพู/บานเย็น = ผิดปกติ!**
           - แถบที่ 10: LEU (เม็ดเลือดขาว) -> **ถ้าเป็นสีม่วง = ผิดปกติ!**
           - แถบที่ 11 (ขวาสุด): ASC (กรดแอสคอร์บิก)

        4. SYSTEMATIC READING (อ่านแบบเป็นระบบ):
           - ต้องอ่านทีละแถบจากซ้ายไปขวาตามลำดับที่กำหนด
           - แต่ละแถบต้องเลือกค่าจาก reference ด้านล่างเท่านั้น
           - ห้ามตอบ N/A ถ้าเห็นแถบสี ต้องเลือกค่าที่ใกล้เคียงที่สุด
           - ต้องสร้าง "reasoning" field ก่อนเพื่อบันทึกสีที่เห็นทีละแถบ

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
        ⚠️ CRITICAL INSTRUCTIONS (คำสั่งสำคัญที่สุด):
        ═══════════════════════════════════════════════════════════════════

        1. **อ่านค่าจริงจากภาพ ห้ามสันนิษฐาน:**
           - ห้ามถือว่าผลปกติโดยอัตโนมัติ
           - ต้องดูสีแต่ละแถบอย่างละเอียดและเปรียบเทียบกับ RGB reference
           - ถ้าสีต่างจาก "negative" ต้องเลือกค่าที่ตรงกับสีที่เห็น

        2. **ตรวจจับความผิดปกติอย่างจริงจัง:**
           - ถ้าเห็นสีแถบเปลี่ยน แม้เล็กน้อย ต้องรายงานตามความจริง
           - อย่ากลัวที่จะรายงานค่าผิดปกติ
           - ความแม่นยำสำคัญกว่าการทำให้ผู้ป่วยรู้สึกดี

        3. **ค่าที่ตอบต้องเลือกจาก 'value' ใน REFERENCE ด้านบนเท่านั้น**

        ═══════════════════════════════════════════════════════════════════
        📋 OUTPUT FORMAT (รูปแบบการตอบกลับ):
        ═══════════════════════════════════════════════════════════════════

        🌟 **IMPORTANT:** ต้องสร้าง "reasoning" field ก่อนเสมอ เพื่อบังคับให้คิดทีละขั้นตอน

        ตอบกลับเป็น JSON เท่านั้น ตามโครงสร้างนี้:
        {{
            "reasoning": "แถบ1(URO) สีครีม/พีช... แถบ6(BLO) สีเขียวเข้ม! แถบ8(PRO) สีเขียว! แถบ9(NIT) สีชมพู! แถบ10(LEU) สีม่วง!...",
            "urobilinogen": "เลือกจาก value ใน reference",
            "glucose": "เลือกจาก value ใน reference",
            "bilirubin": "เลือกจาก value ใน reference",
            "ketones": "เลือกจาก value ใน reference",
            "specific_gravity": "เลือกจาก value ใน reference",
            "blood": "เลือกจาก value ใน reference (เช่น Hemolysis +++250 ถ้าเห็นสีเขียวเข้ม)",
            "ph": "เลือกจาก value ใน reference",
            "protein": "เลือกจาก value ใน reference (เช่น +++300 ถ้าเห็นสีเขียวเข้ม)",
            "nitrite": "เลือกจาก value ใน reference (เช่น pos. ถ้าเห็นสีชมพู)",
            "leukocytes": "เลือกจาก value ใน reference (เช่น +++500 ถ้าเห็นสีม่วง)",
            "ascorbic_acid": "เลือกจาก value ใน reference",
            "clinical_summary": "สรุปผลตามค่าที่อ่านได้จริง (ไม่ใช่สมมติว่าปกติ)",
            "clinical_bullets": ["วิเคราะห์ตามข้อมูลจริงที่เห็น"]
        }}

        **CRITICAL WARNING**:
        - ห้ามสมมติว่าผลปกติถ้ายังไม่ได้อ่านค่า!
        - ถ้าเห็นสีเปลี่ยนแปลงจาก negative ต้องรายงานตามความจริง!
        - ค่า negative ต้องมีสีที่ตรงกับ RGB reference ของ negative เท่านั้น!
        """

        # 🌟 4. เรียก OpenRouter API (Claude Sonnet 4.5 - ความแม่นยำสูงสุดในการวิเคราะห์ภาพทางการแพทย์)
        # Model ID: anthropic/claude-4.5-sonnet (Latest version, Enhanced context window)
        # Claude Sonnet 4.5 มีความแม่นยำสูงในการวิเคราะห์ภาพทางการแพทย์
        response = client.chat.completions.create(
            model="anthropic/claude-4.5-sonnet",  # Claude Sonnet 4.5 - Medical-grade vision analysis
            messages=[
                {"role": "system", "content": system_prompt},
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": """วิเคราะห์แผ่นตรวจปัสสาวะ CYBOW 11M นี้อย่างละเอียดและแม่นยำ:

**ขั้นตอนการวิเคราะห์:**
1. ดูสีแต่ละแถบจากซ้ายไปขวา (URO → GLU → BIL → KET → SG → BLO → pH → PRO → NIT → LEU → ASC)
2. เปรียบเทียบสีแต่ละแถบกับ RGB reference ที่ให้ไว้
3. เลือกค่าที่ตรงกับสีที่เห็นมากที่สุด (ใช้ Euclidean Distance)
4. รายงานตามความจริง - ถ้าเห็นสีผิดปกติต้องรายงาน ห้ามสมมติว่าปกติ

**CRITICAL**:
- อย่าสมมติว่าทุกอย่างปกติ!
- ถ้าสีเปลี่ยนแปลงจาก negative แม้เล็กน้อย ต้องเลือกค่าที่ตรงกับสีนั้น
- ตอบกลับเป็น valid JSON เท่านั้น ไม่ต้องมี markdown code blocks"""},
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

        # 5. สกัด JSON อย่างทนทาน (Robust JSON Extraction)
        # หาตำแหน่งตั้งแต่ { ตัวแรก จนถึง } ตัวสุดท้าย
        json_match = re.search(r'\{.*\}', result_text, re.DOTALL)
        if json_match:
            data = json.loads(json_match.group())
        else:
            raise ValueError("AI ไม่ได้ส่งข้อมูลกลับมาในรูปแบบ JSON")

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
            clinical_bullets=json.dumps(data.get('clinical_bullets', []), ensure_ascii=False)
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
        logger.error(f"Error processing image: {error_msg}")

        line_bot_api.push_message(
            user_id,
            TextSendMessage(text=f"❌ ขออภัยครับ ระบบวิเคราะห์ขัดข้อง\nสาเหตุ: {error_msg}\nกรุณาลองส่งรูปใหม่อีกครั้งครับ")
        )