# 🏥 LHome Urine Tracker - ระบบวิเคราะห์ปัสสาวะอัตโนมัติด้วย AI

ระบบวิเคราะห์และจัดการผลตรวจปัสสาวะ CYBOW 11M อัตโนมัติ พร้อม LINE Bot และ Dashboard สำหรับติดตามผลผู้ป่วย

## 🎯 ฟีเจอร์หลัก

### 📸 AI Vision Analysis (Medical-Grade)
- วิเคราะห์แผ่นตรวจปัสสาวะ CYBOW 11M ด้วย AI (Claude Sonnet 4.5)
- อ่านค่า 11 พารามิเตอร์ได้แม่นยำด้วยการเทียบสี RGB แบบละเอียด
- ใช้ Euclidean Distance สำหรับ color matching precision
- ระบบ deterministic (ภาพเดียวกันได้ผลเดียวกันเสมอ)
- สรุปผลทางคลินิกอัตโนมัติพร้อมข้อบ่งชี้แบบละเอียด

### 💬 LINE Bot Integration
- รับรูปแผ่นตรวจผ่าน LINE Official Account
- ระบุชื่อผู้ป่วยและบันทึกอัตโนมัติ
- รับผลสรุปทันทีผ่าน LINE

### 📊 Dashboard & Reporting
- Dashboard แสดงสถิติภาพรวมระบบ
- ดูประวัติผู้ป่วยแต่ละรายละเอียด
- กราฟแนวโน้มสุขภาพ (Trend Charts)
- ดาวน์โหลดรายงาน PDF มาตรฐานทางการแพทย์
- Export ข้อมูล CSV

### 🗄️ Database (Supabase PostgreSQL)
- เก็บข้อมูลปลอดภัยบน Cloud
- Row Level Security (RLS)
- Auto-migration โครงสร้างตาราง
- Connection pooling และ retry logic

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

- **Backend:** FastAPI, Python 3.10+
- **Frontend:** Streamlit
- **Database:** PostgreSQL (Supabase)
- **AI Model:** Claude Sonnet 4.5 (via OpenRouter) - Medical-grade vision analysis
- **Color Analysis:** Euclidean Distance with 50+ RGB reference points
- **LINE Bot SDK:** line-bot-sdk
- **Data Processing:** pandas, plotly
- **PDF Generation:** fpdf2 with THSarabun fonts

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
# Database (Supabase PostgreSQL)
DATABASE_URL=postgresql://user:password@host:port/database

# LINE Bot
LINE_CHANNEL_ACCESS_TOKEN=your_line_channel_access_token
LINE_CHANNEL_SECRET=your_line_channel_secret

# OpenRouter API (สำหรับ Claude Sonnet 4.5 Vision)
OPENROUTER_API_KEY=your_openrouter_api_key
```

**วิธีการหา API Keys:**

- **Supabase Database**: https://supabase.com
  1. สร้างโปรเจคใหม่
  2. ไปที่ Project Settings → Database
  3. คัดลอก Connection String (URI mode)

- **LINE API**: https://developers.line.biz/console/
  1. สร้าง Provider และ Channel (Messaging API)
  2. คัดลอก Channel Secret และ Channel Access Token

- **OpenRouter API**: https://openrouter.ai/keys
  1. สมัครสมาชิกและ Login
  2. สร้าง API Key ใหม่

## 🚀 การรันระบบ

### ทดสอบการเชื่อมต่อ Database

```bash
python -c "from src.analysis import load_data; print(load_data())"
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
├── .streamlit/
│   └── config.toml         # Streamlit configuration
├── assets/
│   └── fonts/              # THSarabun fonts สำหรับ PDF
├── pages/
│   └── dashboard.py        # Streamlit dashboard หลัก
├── src/
│   ├── analysis.py         # โหลดข้อมูลและสร้างกราฟ
│   ├── db_handler.py       # จัดการ Database (Supabase)
│   └── pdf_generator.py    # สร้างรายงาน PDF
├── .env                    # Environment variables (ห้าม commit!)
├── .env.example            # ตัวอย่าง configuration
├── .gitignore              # Git ignore rules
├── app.py                  # Streamlit homepage
├── bot.py                  # FastAPI LINE Bot Server
├── requirements.txt        # Python dependencies
├── README.md               # คู่มือนี้
└── venv/                   # Virtual environment (ห้าม commit!)
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

## 🔄 การปรับปรุงที่ทำไปแล้ว (Latest Updates)

### 🌟 Major Update: Medical-Grade AI Analysis
✅ **อัพเกรด AI Model เป็น Claude Sonnet 4.5** (ความแม่นยำสูงสุดสำหรับการวิเคราะห์ภาพทางการแพทย์)
✅ **RGB Color Standards** - เพิ่มค่ามาตรฐานสี RGB แบบละเอียด 50+ จุดอ้างอิง
✅ **Euclidean Distance Algorithm** - ใช้สูตรทางคณิตศาสตร์ในการเทียบสี
✅ **Deterministic Analysis** - ตั้งค่า temperature=0 เพื่อให้ได้ผลลัพธ์สม่ำเสมอ
✅ **Enhanced System Prompt** - คำสั่ง AI แบบละเอียด พร้อมตัวอย่างและมาตรฐาน

### 🏥 System Improvements
✅ เพิ่มระบบสรุปผลทางคลินิกอัตโนมัติแบบละเอียด (clinical_bullets)
✅ ปรับปรุง PDF Generator ให้สวยงามและมาตรฐาน (ใช้ฟอนต์ THSarabun)
✅ เพิ่ม Error Handling แบบละเอียด พร้อม retry logic
✅ ปรับ Requirements.txt ให้มี Version Pinning เพื่อความเสถียร
✅ Migration จาก SQLite → PostgreSQL (Supabase) พร้อม RLS
✅ ปรับปรุง Dashboard UI ให้ทันสมัย (Modern Medical Theme)
✅ เพิ่ม Quick Download PDF จากตาราง (Single-click download)

## 📈 แผนพัฒนาในอนาคต

- [ ] เพิ่ม User Authentication & Role-based Access
- [ ] เพิ่ม Unit Tests และ Integration Tests
- [ ] สร้าง Docker Container สำหรับ Deployment
- [ ] เพิ่ม Notification Alert สำหรับค่าผิดปกติ
- [ ] รองรับแผ่นตรวจหลายรุ่น

## 📊 ตารางสรุปพารามิเตอร์ CYBOW 11M

| Parameter | ชื่อไทย | ค่ามาตรฐาน | ความหมายเมื่อผิดปกติ |
|-----------|---------|------------|---------------------|
| URO | ยูโรบิลิโนเจน | 0.1 - 1.0 mg/dL | ปัญหาตับ/ถุงน้ำดี |
| GLU | กลูโคส | Negative | เบาหวาน |
| BIL | บิลิรูบิน | Negative | ตับอักเสบ/ดีซ่าน |
| KET | คีโตน | Negative | เบาหวานไม่ควบคุม/อดอาหาร |
| SG | ความถ่วงจำเพาะ | 1.005 - 1.030 | ขาดน้ำ/ไตทำงานผิดปกติ |
| BLO | เลือด | Negative | UTI/นิ่วในไต/ภาวะไตอักเสบ |
| pH | ความเป็นกรด-ด่าง | 5.0 - 8.0 | กรด-ด่างผิดปกติ |
| PRO | โปรตีน | Negative | โรคไต/ความดันโลหิตสูง |
| NIT | ไนไตรต์ | Negative | ติดเชื้อแบคทีเรีย (UTI) |
| LEU | เม็ดเลือดขาว | Negative | การอักเสบ/ติดเชื้อ |
| ASC | วิตามินซี | Negative | รับประทานวิตามินซีมาก |

## 👨‍💻 ผู้พัฒนา

พัฒนาโดย LHome Medical Team
ระบบนี้ใช้ Python และ AI เพื่ออำนวยความสะดวกในการวิเคราะห์ผลตรวจปัสสาวะ

## 📄 License

สงวนลิขสิทธิ์ © 2024-2026 LHome Medical System
ระบบนี้สร้างขึ้นเพื่อการศึกษาและใช้ในสถานพยาบาล

---

**⚠️ หมายเหตุสำคัญ:**
- ระบบนี้เป็นเครื่องมือช่วยคัดกรองเบื้องต้น ไม่ใช่การวินิจฉัยทางการแพทย์
- ควรปรึกษาแพทย์เพื่อการวินิจฉัยที่ถูกต้อง
- กรุณาอ่านคู่มือให้ละเอียดก่อนใช้งาน
- อย่าลืม rotate API keys หากเคยโพสต์ขึ้น Git โดยไม่ตั้งใจ
