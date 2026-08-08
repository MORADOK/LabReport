# UAReport - CYBOW 11M Urine Analysis System

ระบบวิเคราะห์ผลตรวจปัสสาวะ CYBOW 11M อัตโนมัติด้วย AI Vision และ LINE Bot

## 🎯 ฟีเจอร์หลัก

- **LINE Bot Integration**: รับรูปแผ่นตรวจผ่าน LINE Official Account
- **AI Vision Analysis**: วิเคราะห์รูปแผ่นตรวจด้วย OpenRouter GPT-4o-mini
- **Auto Data Extraction**: ดึงข้อมูล 11 พารามิเตอร์อัตโนมัติ
- **Dashboard**: แสดงผลข้อมูลและกราฟแนวโน้มด้วย Streamlit
- **Database Storage**: บันทึกข้อมูลใน SQLite
- **Logging System**: ระบบ log แบบครบถ้วน
- **Error Handling**: จัดการข้อผิดพลาดแบบละเอียด

## 📋 พารามิเตอร์ที่วิเคราะห์ได้

1. Urobilinogen
2. Glucose
3. Bilirubin
4. Ketones
5. Specific Gravity
6. Blood
7. pH
8. Protein
9. Nitrite
10. Leukocytes
11. Ascorbic Acid

## 🛠️ เทคโนโลยี

**Backend:**
- Python 3.13
- FastAPI
- LINE Messaging API
- OpenRouter API (GPT-4o-mini)
- SQLite

**Frontend:**
- Streamlit
- Pandas
- Plotly

## 📦 การติดตั้ง

### 1. Clone โปรเจค

```bash
git clone <repository-url>
cd UAReport
```

### 2. สร้าง Virtual Environment

```bash
python -m venv venv

# Windows
venv\Scripts\activate

# macOS/Linux
source venv/bin/activate
```

### 3. ติดตั้ง Dependencies

```bash
pip install -r requirements.txt
```

### 4. ตั้งค่า Environment Variables

คัดลอกไฟล์ `.env.example` เป็น `.env`:

```bash
cp .env.example .env
```

แก้ไขไฟล์ `.env` และใส่ API keys:

```env
LINE_CHANNEL_SECRET=your_line_channel_secret_here
LINE_CHANNEL_ACCESS_TOKEN=your_line_channel_access_token_here
OPENROUTER_API_KEY=your_openrouter_api_key_here
```

**วิธีการหา API Keys:**

- **LINE API**: https://developers.line.biz/console/
  1. สร้าง Provider และ Channel (Messaging API)
  2. คัดลอก Channel Secret และ Channel Access Token

- **OpenRouter API**: https://openrouter.ai/keys
  1. สมัครสมาชิกและ Login
  2. สร้าง API Key ใหม่

## 🚀 การรันระบบ

### ทดสอบ Database

```bash
python test_database.py
```

### รัน LINE Bot (Backend)

```bash
# Development mode
uvicorn bot:app --reload --port 8000

# Production mode
uvicorn bot:app --host 0.0.0.0 --port 8000
```

เปิด Swagger UI: http://localhost:8000/docs

### รัน Dashboard (Frontend)

```bash
streamlit run app.py
```

เปิด Dashboard: http://localhost:8501

## 📱 การใช้งาน LINE Bot

1. เพิ่ม LINE Official Account เข้า Friend list
2. ส่งรูปแผ่นตรวจ CYBOW 11M เข้าแชท
3. Bot จะขอชื่อ-นามสกุลของคนไข้
4. พิมพ์ชื่อ-นามสกุล แล้วส่ง
5. รอ AI วิเคราะห์ผล (ประมาณ 5-10 วินาที)
6. รับผลตรวจครบ 11 พารามิเตอร์

## 📊 การใช้งาน Dashboard

1. เปิด Dashboard ที่ http://localhost:8501
2. คลิกที่แถบเมนูด้านซ้าย → "1 Dashboard"
3. เลือกชื่อคนไข้จาก Sidebar
4. ดูข้อมูลและกราฟแนวโน้ม
5. ดาวน์โหลดรายงาน CSV (ถ้าต้องการ)

## 🗂️ โครงสร้างโปรเจค

```
UAReport/
├── .env                    # Environment variables (ห้ามโพสต์ Git!)
├── .env.example            # ตัวอย่าง env config
├── .gitignore              # Git ignore rules
├── README.md               # คู่มือนี้
├── requirements.txt        # Python dependencies
├── bot.py                  # LINE Bot (Main - ปรับปรุงแล้ว)
├── main.py                 # LINE Bot (Old version)
├── app.py                  # Streamlit homepage
├── test_database.py        # Database test script
├── check_models.py         # Gemini model checker
├── data/
│   └── urine_records.db    # SQLite database
├── src/
│   ├── database.py         # Database operations
│   └── analysis.py         # Data analysis & charts
├── page/
│   └── dashboard.py        # Streamlit dashboard
└── venv/                   # Virtual environment
```

## 🔐 ความปลอดภัย

### ⚠️ สำคัญมาก!

1. **ห้ามโพสต์ไฟล์ `.env` ขึ้น Git**
2. **Rotate API Keys ทันที** ถ้าคุณเคยโพสต์โดยไม่ตั้งใจ
3. ใช้ `.gitignore` ครอบคลุม:
   - `.env`
   - `*.db`
   - `__pycache__/`
   - `venv/`
   - `*.log`

## 🧪 การทดสอบ

### ทดสอบ Database

```bash
python test_database.py
```

Expected output:
```
✅ Insert successful
✅ Loaded X records
✅ Schema check complete
```

### ทดสอบ Bot Server

```bash
# Start server
uvicorn bot:app --reload --port 8000

# ใน terminal อื่น
curl http://localhost:8000/docs
```

Expected: Swagger UI HTML

### ทดสอบ Dashboard

```bash
streamlit run app.py
```

Expected: เปิดเบราว์เซอร์ที่ http://localhost:8501

## 📝 Logging

ระบบจะบันทึก log ไว้ที่:
- **Console**: Standard output
- **File**: `bot.log`

ระดับ Log:
- INFO: การทำงานปกติ
- WARNING: เตือนปัญหาที่ไม่ร้ายแรง
- ERROR: ข้อผิดพลาดที่จัดการได้
- CRITICAL: ข้อผิดพลาดร้ายแรง

## 🐛 การแก้ไขปัญหา

### Bot ไม่ตอบกลับ

1. ตรวจสอบ `.env` มี API Keys ครบ
2. ตรวจสอบ LINE Webhook URL ตั้งค่าถูกต้อง
3. ดู log ที่ `bot.log`

### Database Error

```bash
# ตรวจสอบ schema
python test_database.py

# ถ้าต้องการรีเซ็ต (ระวัง: ข้อมูลจะหายหมด!)
rm data/urine_records.db
python -c "from src import database; database.init_db()"
```

### AI ไม่สามารถวิเคราะห์รูปได้

1. ตรวจสอบรูปชัดพอ
2. แผ่นตรวจต้องเป็น CYBOW 11M
3. ถ่ายรูปในที่แสงสว่างเพียงพอ
4. ตรวจสอบ OpenRouter API key และ credits

## 🔄 การปรับปรุงที่ทำไปแล้ว

✅ เพิ่ม logging system
✅ ปรับปรุง error handling (specific exceptions)
✅ เพิ่ม input validation
✅ สร้าง `.env.example` และ `.gitignore`
✅ ทดสอบระบบทั้งหมด
✅ เพิ่ม daemon threads เพื่อป้องกัน hanging
✅ ตรวจสอบ AI response validation

## 📈 แผนพัฒนาในอนาคต

- [ ] เพิ่ม Connection Pooling สำหรับ Database
- [ ] เพิ่ม Unit Tests
- [ ] เพิ่ม Type Hints ทุกฟังก์ชัน
- [ ] สร้าง Docker Container
- [ ] เพิ่ม User Authentication
- [ ] Export รายงานเป็น PDF

## 👨‍💻 ผู้พัฒนา

ระบบนี้พัฒนาด้วย Python และ AI สำหรับอำนวยความสะดวกในการวิเคราะห์ผลตรวจปัสสาวะ

## 📄 License

ระบบนี้สร้างขึ้นเพื่อการศึกษาและใช้ในสถานพยาบาล

---

**หมายเหตุ:** กรุณาอ่านคู่มือให้ละเอียดก่อนใช้งาน และอย่าลืม rotate API keys หากเคยโพสต์ขึ้น Git โดยไม่ตั้งใจ
