import os
import json
import base64
import tempfile
import threading
import logging
from datetime import datetime
from fastapi import FastAPI, Request, HTTPException
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError, LineBotApiError
from linebot.models import MessageEvent, TextMessage, ImageMessage, TextSendMessage
from dotenv import load_dotenv
from openai import OpenAI

# นำเข้าโมดูลฐานข้อมูล (ที่เชื่อมกับ Supabase แล้ว)
from src import db_handler

# โหลด Environment Variables
load_dotenv()
LINE_CHANNEL_ACCESS_TOKEN = os.getenv("LINE_CHANNEL_ACCESS_TOKEN")
LINE_CHANNEL_SECRET = os.getenv("LINE_CHANNEL_SECRET")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

app = FastAPI()
line_bot_api = LineBotApi(LINE_CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(LINE_CHANNEL_SECRET)
client = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=OPENROUTER_API_KEY)

# เก็บสถานะการทำงานชั่วคราว
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
# Endpoints
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
            TextSendMessage(text=f"กำลังวิเคราะห์ผลตรวจของ {patient_name}...\nกรุณารอสักครู่ครับ ⏳")
        )
        
        # ลบ state เพื่อป้องกันการทำงานซ้ำซ้อน
        del user_states[user_id]
        
        # ประมวลผลใน Background
        threading.Thread(target=process_image_with_ai, args=(image_id, user_id, patient_name)).start()

def process_image_with_ai(image_id, user_id, patient_name):
    try:
        # 1. โหลดรูปจาก LINE
        message_content = line_bot_api.get_message_content(image_id)
        with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as tf:
            for chunk in message_content.iter_content():
                tf.write(chunk)
            temp_path = tf.name

        with open(temp_path, "rb") as image_file:
            base64_image = base64.b64encode(image_file.read()).decode('utf-8')
        os.remove(temp_path)

        # 2. บังคับ AI ด้วย System Prompt และ Data Standards
        # (ส่วนการตั้งค่า CYBOW_11M_STANDARDS ยังคงไว้เหมือนเดิม)
        
        # 1. อัปเดต System Prompt
        system_prompt = f"""
        คุณคือผู้เชี่ยวชาญด้านการวิเคราะห์แผ่นตรวจปัสสาวะ หน้าที่ของคุณคือ:

        1. อ่านค่าจากภาพแผ่น CYBOW 11M โดยเลือกค่าให้ตรงกับมาตรฐานนี้เท่านั้น:
           - urobilinogen: {CYBOW_11M_STANDARDS['urobilinogen']}
           - glucose: {CYBOW_11M_STANDARDS['glucose']}
           - bilirubin: {CYBOW_11M_STANDARDS['bilirubin']}
           - ketones: {CYBOW_11M_STANDARDS['ketones']}
           - specific_gravity: {CYBOW_11M_STANDARDS['specific_gravity']} (ต้องเป็นตัวเลขเท่านั้น เช่น "1.020")
           - blood: {CYBOW_11M_STANDARDS['blood']}
           - ph: {CYBOW_11M_STANDARDS['ph']} (ต้องเป็นตัวเลขเท่านั้น เช่น "7")
           - protein: {CYBOW_11M_STANDARDS['protein']}
           - nitrite: {CYBOW_11M_STANDARDS['nitrite']}
           - leukocytes: {CYBOW_11M_STANDARDS['leukocytes']}
           - ascorbic_acid: {CYBOW_11M_STANDARDS['ascorbic_acid']}

        2. เขียน 'clinical_summary' (สรุปผลการตรวจ) เป็นภาษาไทย 1-2 ประโยค
        3. เขียน 'clinical_bullets' (ข้อบ่งชี้ทางคลินิกและวิเคราะห์ผล) เป็นภาษาไทยแบบ Array

        ⚠️ สำคัญ:
        - specific_gravity และ ph ต้องเป็นตัวเลขเท่านั้น (ไม่ใช่คำว่า "normal" หรือ "abnormal")
        - ใช้ค่าจากมาตรฐานข้างบนเท่านั้น ห้ามสร้างค่าใหม่

        ตอบกลับเป็น JSON Format:
        {{
            "urobilinogen": "0.1 Normal",
            "glucose": "neg.",
            "bilirubin": "neg.",
            "ketones": "neg.",
            "specific_gravity": "1.020",
            "blood": "neg.",
            "ph": "7",
            "protein": "neg.",
            "nitrite": "neg.",
            "leukocytes": "neg.",
            "ascorbic_acid": "neg.",
            "clinical_summary": "ผลตรวจปัสสาวะอยู่ในเกณฑ์ปกติทุกพารามิเตอร์",
            "clinical_bullets": ["ไม่พบความผิดปกติ"]
        }}
        """

        response = client.chat.completions.create(
            model="gpt-4o-mini",
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
            max_tokens=2048,  # ลด max_tokens เพื่อประหยัด credits
            response_format={"type": "json_object"}
        )

        result_text = response.choices[0].message.content
        data = json.loads(result_text)

        # 3. จัดเตรียมข้อมูลและบันทึกลง Database
        date_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # ฟังก์ชันแปลงค่าเป็น float อย่างปลอดภัย
        def safe_float(value, default=0.0):
            """แปลงค่าเป็น float โดยจัดการกับค่าที่ไม่ใช่ตัวเลข"""
            if value is None or value == 'N/A':
                return default
            try:
                # ลองแปลงเป็น float
                return float(value)
            except (ValueError, TypeError):
                # ถ้าแปลงไม่ได้ (เช่น "normal", "abnormal") ให้ใช้ค่า default
                logging.warning(f"Cannot convert '{value}' to float, using default {default}")
                return default

        u_urobilinogen = data.get('urobilinogen', 'N/A')
        u_glucose = data.get('glucose', 'N/A')
        u_bilirubin = data.get('bilirubin', 'N/A')
        u_ketones = data.get('ketones', 'N/A')
        u_sg = safe_float(data.get('specific_gravity'), 1.020)  # ค่าปกติคือ 1.020
        u_blood = data.get('blood', 'N/A')
        u_ph = safe_float(data.get('ph'), 7.0)  # ค่าปกติคือ 7.0
        u_protein = data.get('protein', 'N/A')
        u_nitrite = data.get('nitrite', 'N/A')
        u_leukocytes = data.get('leukocytes', 'N/A')
        u_ascorbic_acid = data.get('ascorbic_acid', 'N/A')

        # ดึงข้อมูล clinical analysis จาก AI
        clinical_summary = data.get('clinical_summary', 'ไม่สามารถสรุปผลได้แน่ชัด')
        clinical_bullets = data.get('clinical_bullets', [])

        success = db_handler.insert_record(
            date=date_str, urobilinogen=u_urobilinogen, glucose=u_glucose,
            bilirubin=u_bilirubin, ketones=u_ketones, specific_gravity=u_sg,
            blood=u_blood, ph=u_ph, protein=u_protein, nitrite=u_nitrite,
            leukocytes=u_leukocytes, ascorbic_acid=u_ascorbic_acid, notes=patient_name,
            clinical_summary=clinical_summary, clinical_bullets=clinical_bullets
        )

        # 4. ส่งผลลัพธ์กลับไปยัง LINE
        if success:
            reply_msg = (
                f"✅ บันทึกผลตรวจสำเร็จ!\n👤 คนไข้: {patient_name}\n\n"
                f"🔬 ผลตรวจ CYBOW 11M:\n"
                f"1. Urobilinogen: {u_urobilinogen}\n2. Glucose: {u_glucose}\n"
                f"3. Bilirubin: {u_bilirubin}\n4. Ketones: {u_ketones}\n"
                f"5. S.G.: {data.get('specific_gravity', 'N/A')}\n6. Blood: {u_blood}\n"
                f"7. pH: {data.get('ph', 'N/A')}\n8. Protein: {u_protein}\n"
                f"9. Nitrite: {u_nitrite}\n10. Leukocytes: {u_leukocytes}\n"
                f"11. Ascorbic Acid: {u_ascorbic_acid}\n\n"
                f"📊 ข้อมูลซิงค์เข้า LHome Dashboard แล้วครับ!"
            )
            line_bot_api.push_message(user_id, TextSendMessage(text=reply_msg))

    except Exception as e:
        logging.error(f"Error processing image: {e}")

        # กำหนดข้อความ error ที่เหมาะสมตามประเภทของ error
        error_message = "❌ ขออภัยครับ เกิดข้อผิดพลาดในการวิเคราะห์ภาพ กรุณาลองใหม่อีกครั้ง"

        # ตรวจสอบว่าเป็น OpenRouter API error หรือไม่
        if "402" in str(e) or "credits" in str(e).lower():
            error_message = "❌ ระบบ AI ไม่สามารถประมวลผลได้ในขณะนี้ (ปัญหา credits)\nกรุณาติดต่อผู้ดูแลระบบครับ"
        elif "401" in str(e) or "unauthorized" in str(e).lower():
            error_message = "❌ ระบบ AI มีปัญหาการยืนยันตัวตน กรุณาติดต่อผู้ดูแลระบบครับ"
        elif "timeout" in str(e).lower():
            error_message = "❌ ระบบใช้เวลานานเกินไป กรุณาลองใหม่อีกครั้งครับ"

        line_bot_api.push_message(
            user_id,
            TextSendMessage(text=error_message)
        )