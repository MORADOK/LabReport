import os
import json
import base64
import tempfile
import threading
from fastapi import FastAPI, Request, HTTPException
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, ImageMessage, TextSendMessage
from dotenv import load_dotenv
import datetime
import sys

# ใช้ OpenAI SDK เชื่อมต่อกับ OpenRouter
from openai import OpenAI

# นำเข้า Database
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))
import database

# โหลด .env
load_dotenv()

app = FastAPI(title="Urine Test LINE Webhook (OpenRouter)")

# ตั้งค่า LINE
line_bot_api = LineBotApi(os.getenv('LINE_CHANNEL_ACCESS_TOKEN'))
handler = WebhookHandler(os.getenv('LINE_CHANNEL_SECRET'))

# ตั้งค่า OpenRouter Client
client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=os.getenv("OPENROUTER_API_KEY"),
)

# เลือกใช้ Model ที่รองรับ Vision บน OpenRouter 
# (เช่น 'google/gemini-2.0-flash-001' หรือ 'meta-llama/llama-3.2-11b-vision-instruct')
MODEL_NAME = "openai/gpt-4o-mini"

user_states = {}

@app.post("/webhook")
async def callback(request: Request):
    signature = request.headers.get('X-Line-Signature')
    body = await request.body()
    try:
        handler.handle(body.decode('utf-8'), signature)
    except InvalidSignatureError:
        raise HTTPException(status_code=400, detail="Invalid signature.")
    return "OK"

@handler.add(MessageEvent, message=ImageMessage)
def handle_image(event):
    user_id = event.source.user_id
    image_id = event.message.id
    
    user_states[user_id] = {"status": "waiting_for_name", "image_id": image_id}
    
    line_bot_api.reply_message(
        event.reply_token, 
        TextSendMessage(text="📸 ได้รับรูปแผ่นตรวจเรียบร้อยครับ\n\nพิมพ์ 'ชื่อ-นามสกุล' ของคนไข้เพื่อบันทึกข้อมูลได้เลยครับ")
    )

@handler.add(MessageEvent, message=TextMessage)
def handle_text(event):
    user_id = event.source.user_id
    text = event.message.text
    
    if user_id in user_states and user_states[user_id]["status"] == "waiting_for_name":
        image_id = user_states[user_id]["image_id"]
        patient_name = text
        
        line_bot_api.reply_message(
            event.reply_token, 
            TextSendMessage(text=f"⏳ กำลังใช้ OpenRouter AI วิเคราะห์ผลตรวจปัสสาวะของคุณ {patient_name}...\nกรุณารอสักครู่ครับ")
        )
        
        # Threading ทำงานเบื้องหลัง
        thread = threading.Thread(target=process_image_with_ai, args=(user_id, image_id, patient_name))
        thread.start()
        del user_states[user_id]
    else:
        line_bot_api.reply_message(
            event.reply_token, 
            TextSendMessage(text="กรุณาส่งรูป 'แผ่นตรวจปัสสาวะ (CYBOW 11M)' เข้ามาก่อนนะครับ 🧪")
        )

def process_image_with_ai(user_id, image_id, patient_name):
    temp_file_path = None
    try:
        # 1. โหลดรูปจาก LINE และแปลงเป็น Base64
        message_content = line_bot_api.get_message_content(image_id)
        with tempfile.NamedTemporaryFile(delete=False, suffix='.jpg') as tf:
            for chunk in message_content.iter_content():
                tf.write(chunk)
            temp_file_path = tf.name

        with open(temp_file_path, "rb") as image_file:
            base64_image = base64.b64encode(image_file.read()).decode('utf-8')

        # 2. ส่งรูปและ Prompt ผ่าน OpenRouter API
        prompt = """
        You are a medical data extraction AI. Analyze this CYBOW 11M urine test strip image.
        Compare the colors on the strip to a standard CYBOW 11M reference.
        Extract the 11 parameter values. 
        You MUST respond ONLY with a valid JSON object matching this exact schema:
        {
            "urobilinogen": "value",
            "glucose": "value",
            "bilirubin": "value",
            "ketones": "value",
            "specific_gravity": 1.015,
            "blood": "value",
            "ph": 6.0,
            "protein": "value",
            "nitrite": "value",
            "leukocytes": "value",
            "ascorbic_acid": "value"
        }
        For 'specific_gravity' and 'ph', return numbers (float). For others, return the string label (e.g., 'neg', 'trace', '+30').
        """
        
        response = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{base64_image}"
                            }
                        }
                    ]
                }
            ],
            response_format={"type": "json_object"}
        )
        
        result_text = response.choices[0].message.content.strip()
        data = json.loads(result_text)
        
        # 3. บันทึกลง Database
        date_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        success = database.insert_record(
            date_str, 
            data.get("urobilinogen", "neg"), 
            data.get("glucose", "neg"), 
            data.get("bilirubin", "neg"), 
            data.get("ketones", "neg"),
            float(data.get("specific_gravity", 1.000)), 
            data.get("blood", "neg"), 
            float(data.get("ph", 6.0)), 
            data.get("protein", "neg"), 
            data.get("nitrite", "neg"), 
            data.get("leukocytes", "neg"), 
            data.get("ascorbic_acid", "neg"), 
            notes=f"คนไข้: {patient_name} (Via OpenRouter)"
        )
        
        # 4. แจ้งผลกลับไปยัง LINE
        if success:
            reply_msg = (
                f"✅ วิเคราะห์ผ่าน OpenRouter สำเร็จ!\n"
                f"👤 คนไข้: {patient_name}\n\n"
                f"🔬 ผลตรวจเบื้องต้น:\n"
                f"- pH: {data.get('ph')}\n"
                f"- Protein: {data.get('protein')}\n"
                f"- Blood: {data.get('blood')}\n"
                f"- Ketones: {data.get('ketones')}\n\n"
                f"📊 พร้อมลุยทำ Dashboard ต่อครับ!"
            )
            line_bot_api.push_message(user_id, TextSendMessage(text=reply_msg))
            
    except Exception as e:
        print(f"❌ OpenRouter AI Error: {e}")
        line_bot_api.push_message(
            user_id, 
            TextSendMessage(text="❌ ขออภัยครับ OpenRouter AI ไม่สามารถอ่านค่าจากรูปนี้ได้ หรือระบบขัดข้อง รบกวนถ่ายใหม่อีกครั้งครับ")
        )
    finally:
        if temp_file_path and os.path.exists(temp_file_path):
            os.remove(temp_file_path)