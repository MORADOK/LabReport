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

# นำเข้าฟังก์ชันจากไฟล์ database.py
from src import database

# Setup Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('bot.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# 1. โหลด Environment Variables
load_dotenv()
LINE_ACCESS_TOKEN = os.getenv('LINE_CHANNEL_ACCESS_TOKEN')
LINE_CHANNEL_SECRET = os.getenv('LINE_CHANNEL_SECRET')
OPENROUTER_API_KEY = os.getenv('OPENROUTER_API_KEY')

if not all([LINE_ACCESS_TOKEN, LINE_CHANNEL_SECRET, OPENROUTER_API_KEY]):
    logger.error("Missing required environment variables in .env file")
    raise ValueError("❌ ตรวจสอบไฟล์ .env ด่วน! ใส่ API Keys ไม่ครบ")
else:
    logger.info("Environment variables loaded successfully")

# 2. ตั้งค่าการเชื่อมต่อต่างๆ
app = FastAPI(title="CYBOW 11M LINE Webhook")
line_bot_api = LineBotApi(LINE_ACCESS_TOKEN)
handler = WebhookHandler(LINE_CHANNEL_SECRET)

# ใช้ GPT-4o-mini ผ่าน OpenRouter (รองรับ Vision เสถียรและบังคับ JSON ได้ดีมาก)
client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=OPENROUTER_API_KEY,
)
MODEL_NAME = "openai/gpt-4o-mini"

# เก็บ State ของผู้ใช้
user_states = {}

@app.post("/webhook")
async def callback(request: Request):
    """Endpoint สำหรับรับข้อมูลจาก LINE"""
    signature = request.headers.get('X-Line-Signature')
    body = await request.body()
    try:
        handler.handle(body.decode('utf-8'), signature)
    except InvalidSignatureError:
        raise HTTPException(status_code=400, detail="Invalid signature.")
    return "OK"

@handler.add(MessageEvent, message=ImageMessage)
def handle_image(event):
    """เมื่อผู้ใช้ส่งรูปภาพแผ่นตรวจเข้ามา"""
    user_id = event.source.user_id
    image_id = event.message.id

    logger.info(f"Received image from user: {user_id}, image_id: {image_id}")

    # อัปเดต State ให้รอรับชื่อ
    user_states[user_id] = {"status": "waiting_for_name", "image_id": image_id}

    reply_text = "📸 ได้รับรูปแผ่นตรวจเรียบร้อยครับ\n\nพิมพ์ 'ชื่อ-นามสกุล' ของคนไข้เพื่อบันทึกข้อมูลได้เลยครับ"
    try:
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text=reply_text))
    except LineBotApiError as e:
        logger.error(f"LINE API error in handle_image: {e}")

@handler.add(MessageEvent, message=TextMessage)
def handle_text(event):
    """เมื่อผู้ใช้พิมพ์ข้อความ (ชื่อคนไข้)"""
    user_id = event.source.user_id
    text = event.message.text

    logger.info(f"Received text from user: {user_id}, text: {text}")

    if user_id in user_states and user_states[user_id]["status"] == "waiting_for_name":
        image_id = user_states[user_id]["image_id"]
        patient_name = text.strip()

        # Validate patient name
        if not patient_name or len(patient_name) < 2:
            logger.warning(f"Invalid patient name: {patient_name}")
            try:
                line_bot_api.reply_message(
                    event.reply_token,
                    TextSendMessage(text="⚠️ กรุณาใส่ชื่อ-นามสกุลที่ถูกต้อง (อย่างน้อย 2 ตัวอักษร)")
                )
            except LineBotApiError as e:
                logger.error(f"LINE API error: {e}")
            return

        try:
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(text=f"⏳ กำลังใช้ AI วิเคราะห์ผลตรวจของคุณ {patient_name}...\nกรุณารอสักครู่ครับ")
            )
        except LineBotApiError as e:
            logger.error(f"LINE API error in handle_text: {e}")

        # ลบ State แล้วโยนงานประมวลผลไปทำ Background (ป้องกัน LINE Timeout)
        del user_states[user_id]
        thread = threading.Thread(target=process_image_with_ai, args=(user_id, image_id, patient_name))
        thread.daemon = True  # Make thread daemon to prevent hanging
        thread.start()
    else:
        try:
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(text="กรุณาส่งรูป 'แผ่นตรวจปัสสาวะ (CYBOW 11M)' เข้ามาก่อนนะครับ 🧪")
            )
        except LineBotApiError as e:
            logger.error(f"LINE API error in handle_text: {e}")

def validate_ai_response(data: dict) -> tuple[bool, str]:
    """Validate AI response contains all required fields"""
    required_fields = [
        'urobilinogen', 'glucose', 'bilirubin', 'ketones',
        'specific_gravity', 'blood', 'ph', 'protein',
        'nitrite', 'leukocytes', 'ascorbic_acid'
    ]

    missing_fields = [field for field in required_fields if field not in data]

    if missing_fields:
        return False, f"Missing fields: {', '.join(missing_fields)}"

    # Validate numeric fields
    try:
        sg = float(data.get('specific_gravity', 0))
        if not (0.9 <= sg <= 1.1):
            return False, f"Invalid specific_gravity: {sg}"
    except (ValueError, TypeError):
        return False, "specific_gravity must be a number"

    try:
        ph = float(data.get('ph', 0))
        if not (4.0 <= ph <= 9.0):
            return False, f"Invalid pH: {ph}"
    except (ValueError, TypeError):
        return False, "pH must be a number"

    return True, "Valid"

def process_image_with_ai(user_id, image_id, patient_name):
    """ฟังก์ชันหลัก: โหลดรูป -> ยิง AI -> เซฟลง Database -> ตอบ LINE"""
    temp_file_path = None
    logger.info(f"Starting AI processing for user: {user_id}, patient: {patient_name}")

    try:
        # Step 1: ดาวน์โหลดรูปจาก LINE และแปลงเป็น Base64
        logger.info(f"Downloading image: {image_id}")
        message_content = line_bot_api.get_message_content(image_id)
        with tempfile.NamedTemporaryFile(delete=False, suffix='.jpg') as tf:
            for chunk in message_content.iter_content():
                tf.write(chunk)
            temp_file_path = tf.name

        logger.info(f"Image saved to temp file: {temp_file_path}")

        with open(temp_file_path, "rb") as image_file:
            base64_image = base64.b64encode(image_file.read()).decode('utf-8')

        # Step 2: สร้าง Prompt และเรียก OpenRouter API
        logger.info("Calling OpenRouter API...")
        prompt = """
        Analyze this CYBOW 11M urine test strip.
        Return ONLY a raw JSON object with no markdown formatting and no backticks.
        Use this exact structure:
        {
            "urobilinogen": "normal",
            "glucose": "neg",
            "bilirubin": "neg",
            "ketones": "neg",
            "specific_gravity": 1.020,
            "blood": "neg",
            "ph": 6.5,
            "protein": "neg",
            "nitrite": "neg",
            "leukocytes": "neg",
            "ascorbic_acid": "neg"
        }
        """

        response = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}}
                    ]
                }
            ],
            response_format={"type": "json_object"}
        )

        result_text = response.choices[0].message.content.strip()
        logger.info(f"AI Response received: {result_text[:200]}...")

        # คลีนข้อมูล Markdown (ถ้า AI เผลอส่ง ```json มา)
        if result_text.startswith("```"):
            result_text = result_text.replace("```json", "").replace("```", "").strip()
            logger.warning("Cleaned markdown formatting from AI response")

        # Parse JSON with error handling
        try:
            data = json.loads(result_text)
        except json.JSONDecodeError as e:
            logger.error(f"JSON decode error: {e}, response: {result_text}")
            raise ValueError(f"Invalid JSON from AI: {e}")

        # Validate AI response
        is_valid, validation_msg = validate_ai_response(data)
        if not is_valid:
            logger.error(f"AI response validation failed: {validation_msg}")
            raise ValueError(f"Invalid AI response: {validation_msg}")
        
        # Step 3: ดึงข้อมูลให้ครบ 11 ค่า (ถ้า AI ส่งมาไม่ครบ จะใส่ 'N/A' หรือค่าว่างแทน)
        date_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        u_urobilinogen = data.get('urobilinogen', 'N/A')
        u_glucose = data.get('glucose', 'N/A')
        u_bilirubin = data.get('bilirubin', 'N/A')
        u_ketones = data.get('ketones', 'N/A')
        u_sg = data.get('specific_gravity', 0.0)
        u_blood = data.get('blood', 'N/A')
        u_ph = data.get('ph', 0.0)
        u_protein = data.get('protein', 'N/A')
        u_nitrite = data.get('nitrite', 'N/A')
        u_leukocytes = data.get('leukocytes', 'N/A')
        u_ascorbic_acid = data.get('ascorbic_acid', 'N/A')

        # บันทึกลง Database
        logger.info(f"Saving to database for patient: {patient_name}")
        try:
            success = database.insert_record(
                date=date_str,
                urobilinogen=u_urobilinogen,
                glucose=u_glucose,
                bilirubin=u_bilirubin,
                ketones=u_ketones,
                specific_gravity=u_sg,
                blood=u_blood,
                ph=u_ph,
                protein=u_protein,
                nitrite=u_nitrite,
                leukocytes=u_leukocytes,
                ascorbic_acid=u_ascorbic_acid,
                notes=patient_name
            )
            logger.info("Database insert successful")
        except Exception as db_error:
            logger.error(f"Database error: {db_error}")
            raise
        
        # Step 4: แจ้งผลลัพธ์ผ่าน LINE แบบครบ 11 ช่อง
        if success:
            reply_msg = (
                f"✅ บันทึกผลตรวจสำเร็จ!\n"
                f"👤 คนไข้: {patient_name}\n\n"
                f"🔬 ผลตรวจ CYBOW 11M:\n"
                f"1. Urobilinogen: {u_urobilinogen}\n"
                f"2. Glucose: {u_glucose}\n"
                f"3. Bilirubin: {u_bilirubin}\n"
                f"4. Ketones: {u_ketones}\n"
                f"5. Specific Gravity: {u_sg}\n"
                f"6. Blood: {u_blood}\n"
                f"7. pH: {u_ph}\n"
                f"8. Protein: {u_protein}\n"
                f"9. Nitrite: {u_nitrite}\n"
                f"10. Leukocytes: {u_leukocytes}\n"
                f"11. Ascorbic Acid: {u_ascorbic_acid}\n\n"
                f"📊 ข้อมูลเข้าสู่ Dashboard ครบถ้วนครับ!"
            )
            try:
                line_bot_api.push_message(user_id, TextSendMessage(text=reply_msg))
                logger.info(f"Success message sent to user: {user_id}")
            except LineBotApiError as e:
                logger.error(f"Failed to send success message: {e}")

    except LineBotApiError as e:
        logger.error(f"LINE Bot API error: {e}")
        try:
            line_bot_api.push_message(
                user_id,
                TextSendMessage(text="❌ ไม่สามารถดาวน์โหลดรูปภาพได้ กรุณาลองส่งใหม่อีกครั้ง")
            )
        except:
            pass
    except json.JSONDecodeError as e:
        logger.error(f"JSON parsing error: {e}")
        try:
            line_bot_api.push_message(
                user_id,
                TextSendMessage(text="❌ AI ไม่สามารถแปลงผลเป็น JSON ได้ กรุณาถ่ายรูปใหม่ให้ชัดขึ้น")
            )
        except:
            pass
    except ValueError as e:
        logger.error(f"Validation error: {e}")
        try:
            line_bot_api.push_message(
                user_id,
                TextSendMessage(text="❌ ข้อมูลจาก AI ไม่ถูกต้อง กรุณาถ่ายรูปแผ่นตรวจใหม่")
            )
        except:
            pass
    except Exception as e:
        logger.error(f"Unexpected error in processing: {e}", exc_info=True)
        try:
            line_bot_api.push_message(
                user_id,
                TextSendMessage(text="❌ เกิดข้อผิดพลาดในการวิเคราะห์หรือบันทึกข้อมูล กรุณาลองใหม่อีกครั้งครับ")
            )
        except:
            pass
    finally:
        if temp_file_path and os.path.exists(temp_file_path):
            try:
                os.remove(temp_file_path)
                logger.info(f"Temp file removed: {temp_file_path}")
            except Exception as e:
                logger.warning(f"Failed to remove temp file: {e}")

@app.get("/")
def keep_alive():
    return {"status": "CYBOW 11M Bot is awake and running!"}