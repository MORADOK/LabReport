# 🚀 UAReport - Quick Start Guide

ระบบวิเคราะห์ผลตรวจปัสสาวะ CYBOW 11M อัตโนมัติ

---

## ✅ สถานะระบบปัจจุบัน

**🟢 ระบบพร้อมใช้งาน!**

| Service | Status | URL | Port |
|---------|--------|-----|------|
| LINE Bot API | 🟢 RUNNING | http://127.0.0.1:8000 | 8000 |
| Swagger UI | 🟢 RUNNING | http://127.0.0.1:8000/docs | 8000 |
| Dashboard | 🟢 RUNNING | http://localhost:8501 | 8501 |
| Database | 🟢 ACTIVE | D:\UAReport\data\urine_records.db | - |

---

## 📱 การใช้งาน Dashboard

### เข้าใช้งาน
เปิดเบราว์เซอร์แล้วไปที่:
```
http://localhost:8501
```

หรือ
```
http://192.168.10.70:8501  (network access)
```

### หน้าจอ Homepage
- ดูสถานะระบบ
- อ่านคู่มือการใช้งาน
- คลิกเมนู "1 Dashboard" ที่ sidebar ซ้ายมือ

### หน้าจอ Dashboard
1. **กรองข้อมูล**
   - เลือก "แสดงทั้งหมด" หรือ
   - เลือกชื่อคนไข้จาก dropdown

2. **ดูข้อมูล**
   - ตารางแสดงผลตรวจทั้งหมด 11 พารามิเตอร์
   - จัดเรียงตามวันที่ (ล่าสุดก่อน)

3. **ดูกราฟแนวโน้ม**
   - กราฟ pH
   - กราฟ Specific Gravity

4. **ดาวน์โหลดรายงาน**
   - คลิกปุ่ม "ดาวน์โหลดรายงาน (CSV)"
   - ไฟล์จะบันทึกเป็น `Urine_Report_[ชื่อ].csv`

---

## 🤖 การใช้งาน LINE Bot

### ขั้นตอนการส่งผลตรวจ

**1. เตรียมรูปภาพ**
- ถ่ายรูปแผ่นตรวจ CYBOW 11M
- ต้องชัด มองเห็นสีของแผ่นตรวจ
- แสงสว่างเพียงพอ

**2. ส่งรูปเข้า LINE Bot**
- เปิดแชท LINE Official Account
- กดไอคอนรูปภาพ
- เลือกรูปที่ถ่ายไว้
- ส่ง

**3. Bot จะตอบกลับ**
```
📸 ได้รับรูปแผ่นตรวจเรียบร้อยครับ

พิมพ์ 'ชื่อ-นามสกุล' ของคนไข้เพื่อบันทึกข้อมูลได้เลยครับ
```

**4. พิมพ์ชื่อคนไข้**
```
สมชาย ใจดี
```

**5. รอผลการวิเคราะห์**
```
⏳ กำลังใช้ AI วิเคราะห์ผลตรวจของคุณ สมชาย ใจดี...
กรุณารอสักครู่ครับ
```

**6. รับผลตรวจ (5-10 วินาที)**
```
✅ บันทึกผลตรวจสำเร็จ!
👤 คนไข้: สมชาย ใจดี

🔬 ผลตรวจ CYBOW 11M:
1. Urobilinogen: normal
2. Glucose: neg
3. Bilirubin: neg
4. Ketones: neg
5. Specific Gravity: 1.020
6. Blood: neg
7. pH: 6.5
8. Protein: neg
9. Nitrite: neg
10. Leukocytes: neg
11. Ascorbic Acid: neg

📊 ข้อมูลเข้าสู่ Dashboard ครบถ้วนครับ!
```

**7. ดูข้อมูลใน Dashboard**
- เปิด http://localhost:8501
- เลือกชื่อ "สมชาย ใจดี"
- ดูผลตรวจและกราฟ

---

## 🔧 การตรวจสอบสถานะระบบ

### ตรวจสอบว่า Bot Server รันอยู่
```bash
curl http://127.0.0.1:8000/docs
```
ถ้าเห็น Swagger UI = ✅ ทำงานปกติ

### ตรวจสอบว่า Dashboard รันอยู่
```bash
curl http://localhost:8501
```
ถ้าเห็น HTML = ✅ ทำงานปกติ

### ตรวจสอบ Database
```bash
python test_database.py
```

---

## 🛠️ การรันระบบใหม่ (ถ้าปิดไป)

### Terminal 1: เปิด Bot Server
```bash
# Activate virtual environment
venv\Scripts\activate

# Run bot
uvicorn bot:app --reload --port 8000
```

### Terminal 2: เปิด Dashboard
```bash
# Activate virtual environment (ถ้ายังไม่ได้เปิด)
venv\Scripts\activate

# Run dashboard
streamlit run app.py
```

### แบบย่อ (รันทั้งคู่พร้อมกัน)
```bash
# Terminal 1
uvicorn bot:app --reload --port 8000

# Terminal 2
streamlit run app.py
```

---

## 📊 ข้อมูลในระบบปัจจุบัน

**Database:** `D:\UAReport\data\urine_records.db`
- **จำนวนข้อมูล:** 3 records
- **ขนาดไฟล์:** 12 KB

**ตัวอย่างข้อมูลที่มี:**
1. Test Patient - ทดสอบระบบ (2 records)
2. ทรงดี มาแน่ (1 record)

---

## 🔍 API Endpoints

### LINE Webhook
```
POST http://127.0.0.1:8000/webhook
```
Endpoint นี้สำหรับ LINE ส่งข้อมูลมา (ไม่ต้องเรียกเอง)

### API Documentation
```
GET http://127.0.0.1:8000/docs
```
Swagger UI - ดู API spec ทั้งหมด

### OpenAPI Schema
```
GET http://127.0.0.1:8000/openapi.json
```
JSON schema สำหรับ developers

---

## 📝 Log Files

### Bot Log
**Location:** `D:\UAReport\bot.log`

**ดู log แบบ real-time:**
```bash
Get-Content bot.log -Wait -Tail 20
```

**ตัวอย่าง log:**
```
2026-08-07 18:05:14 - bot - INFO - Environment variables loaded successfully
2026-08-07 18:05:20 - bot - INFO - Received image from user: U123456...
2026-08-07 18:05:25 - bot - INFO - AI Response received: {"urobilinogen"...
2026-08-07 18:05:30 - bot - INFO - Database insert successful
```

---

## ⚡ Tips การใช้งาน

### 1. ถ่ายรูปแผ่นตรวจให้ดี
- ✅ ใช้แสงสว่างเพียงพอ
- ✅ ถ่ายตรงๆ ไม่เอียง
- ✅ มองเห็นสีบนแผ่นตรวจชัดเจน
- ❌ อย่าถ่ายในที่มืด
- ❌ อย่าเบลอ

### 2. ตั้งชื่อคนไข้ให้ชัดเจน
- ✅ "สมชาย ใจดี"
- ✅ "Somchai Jaidee"
- ✅ "คนไข้ A001"
- ❌ "A" (สั้นเกินไป)
- ❌ "" (ว่างเปล่า)

### 3. ตรวจสอบผลตรวจ
- เปิด Dashboard ดูผลทันที
- ดาวน์โหลด CSV เก็บไว้
- เปรียบเทียบกราฟแนวโน้ม

---

## 🚨 แก้ปัญหาเบื้องต้น

### Bot ไม่ตอบกลับ
```bash
# 1. ตรวจสอบ server ยังรันอยู่ไหม
curl http://127.0.0.1:8000/docs

# 2. ดู log
Get-Content bot.log -Tail 50

# 3. Restart server
# กด Ctrl+C แล้วรันใหม่
uvicorn bot:app --reload --port 8000
```

### Dashboard ไม่โหลด
```bash
# 1. ตรวจสอบ port 8501
curl http://localhost:8501

# 2. Restart dashboard
# กด Ctrl+C แล้วรันใหม่
streamlit run app.py
```

### AI วิเคราะห์ผิดพลาด
- ลองถ่ายรูปใหม่ให้ชัดขึ้น
- ตรวจสอบแสง
- ส่งรูปใหม่อีกครั้ง

---

## 📞 Support

**ดูคู่มือเต็ม:** `README.md`
**ดูรายงานการทดสอบ:** `TESTING_REPORT.md`

**หากมีปัญหา:**
1. ดู log file: `bot.log`
2. ทดสอบ database: `python test_database.py`
3. ตรวจสอบ .env file มี API keys ครบ

---

## 🎯 สิ่งที่ต้องจำ

1. **ระบบต้องรันทั้ง 2 ส่วน:**
   - Bot Server (port 8000)
   - Dashboard (port 8501)

2. **URL สำคัญ:**
   - Dashboard: http://localhost:8501
   - API Docs: http://localhost:8000/docs

3. **ข้อมูลจะซิงค์อัตโนมัติ:**
   - ส่งรูปทาง LINE → บันทึกลง Database
   - Dashboard จะแสดงข้อมูลทันที

4. **API Keys ต้องถูกต้อง:**
   - ตรวจสอบ `.env` file
   - LINE_CHANNEL_SECRET
   - LINE_CHANNEL_ACCESS_TOKEN
   - OPENROUTER_API_KEY

---

**สร้างเมื่อ:** 2026-08-07
**Version:** 1.0
**Status:** 🟢 Production Ready
