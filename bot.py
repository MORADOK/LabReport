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
# 🌟 Data Standard: ค่าอ้างอิงจากแผ่น CYBOW 11M
# ---------------------------------------------------------
CYBOW_11M_STANDARDS = {
    "urobilinogen": ["0.1 Normal", "1(16)", "2(33)", "4(66)", "8(131)"],
    "glucose": ["neg.", "±100(5.5)", "+250(14)", "++500(28)", "+++1000(55)"],
    "bilirubin": ["neg.", "+", "++", "+++"],
    "ketones": ["neg.", "±5(0.5)", "+15(1.5)", "++40(3.9)", "+++100(10)"],
    "specific_gravity": ["1.000", "1.005", "1.010", "1.015", "1.020", "1.025", "1.030"],
    "blood": ["neg.", "Hemolysis +10", "Hemolysis ++50", "Hemolysis +++250", "Non Hemolysis +10", "Non Hemolysis ++50"],
    "ph": ["5", "6", "6.5", "7", "8", "9"],
    "protein": ["neg.", "trace", "+30(0.3)", "++100(1.0)", "+++300(3.0)", "++++1000(10)"],
    "nitrite": ["neg.", "trace", "pos."],
    "leukocytes": ["neg.", "+25", "++75", "+++500"],
    "ascorbic_acid": ["neg.", "+20(1.2)", "++40(2.4)"]
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

        # 2. ย่อภาพและแปลงเป็น Base64 (ป้องกัน Token เกินกำหนด)
        base64_image = resize_image_to_base64(temp_path, max_dimension=1024)
        if not base64_image:
            raise ValueError("ไม่สามารถประมวลผลไฟล์ภาพได้")

        # 3. สร้าง System Prompt รัดคอ AI ให้ทำงานตามมาตรฐาน (เวอร์ชันปรับปรุง)
        system_prompt = f"""
        คุณคือผู้เชี่ยวชาญด้านการวิเคราะห์แผ่นตรวจปัสสาวะ CYBOW 11M
        แผ่นตรวจในภาพจะเรียงแถบสี 11 พารามิเตอร์ 
        
        กฎเหล็ก (CRITICAL RULES):
        1. คุณ "ต้อง" พยายามประเมินและเลือกค่าที่ใกล้เคียงกับสีในภาพมากที่สุด (Best Match) ห้ามตอบ N/A เด็ดขาด ยกเว้นว่าแถบสีนั้นถูกตัดขาดหายไปจากภาพจริงๆ
        2. เลือกค่าจากรายการมาตรฐานเหล่านี้ให้ตรงเป๊ะทุกตัวอักษร:
           - urobilinogen: {CYBOW_11M_STANDARDS['urobilinogen']}
           - glucose: {CYBOW_11M_STANDARDS['glucose']}
           - bilirubin: {CYBOW_11M_STANDARDS['bilirubin']}
           - ketones: {CYBOW_11M_STANDARDS['ketones']}
           - specific_gravity: {CYBOW_11M_STANDARDS['specific_gravity']}
           - blood: {CYBOW_11M_STANDARDS['blood']}
           - ph: {CYBOW_11M_STANDARDS['ph']}
           - protein: {CYBOW_11M_STANDARDS['protein']}
           - nitrite: {CYBOW_11M_STANDARDS['nitrite']}
           - leukocytes: {CYBOW_11M_STANDARDS['leukocytes']}
           - ascorbic_acid: {CYBOW_11M_STANDARDS['ascorbic_acid']}
           
        3. ประเมินสถานะทางคลินิก:
           - เขียน 'clinical_summary' เป็นภาษาไทย 1-2 ประโยค
           - เขียน 'clinical_bullets' เป็นข้อๆ (Array) อธิบายเจาะลึก
        
        ตอบกลับเป็น JSON Format ตามโครงสร้างนี้เท่านั้น:
        {{
            "urobilinogen": "...", "glucose": "...", "blood": "...", "protein": "...",
            "specific_gravity": "...", "ph": "...", "bilirubin": "...", "ketones": "...",
            "nitrite": "...", "leukocytes": "...", "ascorbic_acid": "...",
            "clinical_summary": "...",
            "clinical_bullets": ["ข้อ 1...", "ข้อ 2..."]
        }}
        """

        # 4. เรียก OpenRouter API
        response = client.chat.completions.create(
            model="openai/gpt-4o-mini", # หรือปรับเป็นโมเดล Vision ที่ต้องการ
            messages=[
                {"role": "system", "content": system_prompt},
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": "อ่านค่าผลตรวจจากรูปแผ่นตรวจปัสสาวะนี้ให้หน่อย"},
                        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}}
                    ]
                }
            ],
            max_tokens=1000, # จำกัด Token ลดความเสี่ยง Error 402
            response_format={"type": "json_object"}
        )

        result_text = response.choices[0].message.content
        print(f"--- AI RESPONSE DEBUG ---\n{result_text}\n-------------------------")
        
        # 5. ทำความสะอาดข้อความ (ดักจับ Markdown) และแปลงเป็น JSON
        cleaned_text = re.sub(r'```json\n|\n```|```', '', result_text).strip()
        data = json.loads(cleaned_text)

        # 6. เตรียมข้อมูลบันทึกลง Database
        date_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # ฟังก์ชันแปลงค่าเป็น float อย่างปลอดภัย
        def safe_float(value, default=0.0):
            """แปลงค่าเป็น float โดยจัดการกับค่าที่ไม่ใช่ตัวเลข"""
            if value is None or value == 'N/A':
                return default
            try:
                return float(value)
            except (ValueError, TypeError):
                logging.warning(f"Cannot convert '{value}' to float, using default {default}")
                return default

        success = db_handler.insert_record(
            date=date_str,
            urobilinogen=data.get('urobilinogen', 'N/A'),
            glucose=data.get('glucose', 'N/A'),
            bilirubin=data.get('bilirubin', 'N/A'),
            ketones=data.get('ketones', 'N/A'),
            specific_gravity=safe_float(data.get('specific_gravity'), 1.020),
            blood=data.get('blood', 'N/A'),
            ph=safe_float(data.get('ph'), 7.0),
            protein=data.get('protein', 'N/A'),
            nitrite=data.get('nitrite', 'N/A'),
            leukocytes=data.get('leukocytes', 'N/A'),
            ascorbic_acid=data.get('ascorbic_acid', 'N/A'),
            notes=patient_name,
            clinical_summary=data.get('clinical_summary', 'ไม่สามารถสรุปผลได้แน่ชัด'),
            clinical_bullets=data.get('clinical_bullets', [])
        )

        # 7. ส่งผลลัพธ์กลับไปยัง LINE
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
        # เคลียร์ไฟล์ขยะออกจากระบบ
        if temp_path and os.path.exists(temp_path):
            os.remove(temp_path)
