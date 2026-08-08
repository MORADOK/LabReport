import os
from google import genai
from dotenv import load_dotenv

# โหลด .env
load_dotenv()

# เชื่อมต่อด้วย SDK ใหม่
client = genai.Client(api_key=os.getenv('GEMINI_API_KEY'))

print("🔍 กำลังค้นหา Model ที่คุณสามารถใช้งานได้...")
try:
    models = client.models.list()
    for m in models:
        # กรองเฉพาะโมเดลที่มีคำว่า gemini และรองรับการ Gen Content
        if 'gemini' in m.name:
            print(f"✅ รองรับ: {m.name}")
except Exception as e:
    print(f"❌ Error: {e}")