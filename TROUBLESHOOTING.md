# 🔧 Troubleshooting Guide - LHome Medical Dashboard

## ⚠️ Dashboard ไม่แสดงข้อมูลคนไข้

### สาเหตุและวิธีแก้ไข

---

## 1️⃣ ยังไม่มีข้อมูลในระบบ (ส่วนใหญ่)

### วิธีแก้:

**Option A: ส่งข้อมูลผ่าน LINE Bot (แนะนำ)**
```
1. เปิด LINE Bot ที่คุณสร้างไว้
2. ส่งรูปภาพแผ่นตรวจปัสสาวะ CYBOW 11M
3. ตอบกลับด้วยชื่อ-นามสกุลผู้ป่วย
4. รอระบบวิเคราะห์ (ใช้เวลา 10-30 วินาที)
5. Refresh Dashboard
```

**Option B: เพิ่มข้อมูล Demo (สำหรับทดสอบ)**
```bash
# ⚠️ ใช้ได้เฉพาะบน Streamlit Cloud หรือ server ที่เชื่อมต่อได้
# ไม่ได้ผลใน local ถ้ามีปัญหา network

# แก้ไข: รันคำสั่งนี้บน Streamlit Cloud terminal
python test_insert_demo_data.py
```

---

## 2️⃣ Local Environment - Network/DNS Issue

### อาการ:
- Dashboard แสดง "⚠️ ไม่สามารถโหลดข้อมูลจาก Database"
- รันโปรแกรมใน local ไม่สามารถเชื่อมต่อ Supabase

### สาเหตุ:
```
Error: could not translate host name "db.fjlarwlqqneneimrprvv.supabase.co"
```

เป็นปัญหา DNS resolution ใน Windows ที่ไม่สามารถแปลง hostname เป็น IP ได้

### วิธีแก้:

#### วิธีที่ 1: ใช้ Streamlit Cloud (แนะนำที่สุด) ⭐
```
✅ Dashboard บน Cloud ทำงานได้ปกติ
✅ ไม่มีปัญหา DNS
✅ เหมาะสำหรับ production

URL: https://labreport-haolauca6om7gqtufcm6ft.streamlit.app
```

#### วิธีที่ 2: แก้ DNS ใน Windows
```bash
# 1. เปิด Command Prompt (Admin)
# 2. ล้าง DNS cache
ipconfig /flushdns

# 3. เปลี่ยน DNS เป็น Google DNS
# Network Settings → Properties → IPv4 → DNS
# Preferred: 8.8.8.8
# Alternate: 8.8.4.4

# 4. ลองใหม่อีกครั้ง
```

#### วิธีที่ 3: ตรวจสอบ Firewall/Antivirus
```
1. ปิด Firewall ชั่วคราว
2. ปิด Antivirus ชั่วคราว
3. ลองเชื่อมต่อใหม่
4. ถ้าได้ → เพิ่ม exception ให้ Python
```

#### วิธีที่ 4: ใช้ VPN
```
1. เปิด VPN (เช่น ProtonVPN, Cloudflare WARP)
2. เชื่อมต่อ server ต่างประเทศ
3. ลองรันโปรแกรมใหม่
```

---

## 3️⃣ RLS (Row Level Security) บล็อกการเข้าถึง

### ตรวจสอบ:
```bash
# ใน Supabase Dashboard → SQL Editor
SELECT relrowsecurity
FROM pg_class
WHERE relname = 'records';

# ควรได้: true

# ตรวจสอบ policies
SELECT * FROM pg_policies WHERE tablename = 'records';

# ควรมี: "Service role full access"
```

### วิธีแก้ (ถ้า RLS บล็อก):
```sql
-- ใน Supabase SQL Editor
-- 1. ตรวจสอบว่ามี policy
SELECT * FROM pg_policies WHERE tablename = 'records';

-- 2. ถ้าไม่มี ให้สร้าง
CREATE POLICY "Service role full access"
ON public.records
FOR ALL
USING (true)
WITH CHECK (true);

-- 3. หรือปิด RLS ชั่วคราว (ไม่แนะนำใน production)
-- ALTER TABLE public.records DISABLE ROW LEVEL SECURITY;
```

---

## 4️⃣ ปัญหา DATABASE_URL

### ตรวจสอบ:
```bash
# ตรวจสอบว่ามี DATABASE_URL
python -c "import os; from dotenv import load_dotenv; load_dotenv(); print('DB URL exists:', bool(os.getenv('DATABASE_URL')))"
```

### วิธีแก้:
```bash
# 1. เช็คไฟล์ .env
cat .env

# 2. ควรมีรูปแบบนี้:
DATABASE_URL=postgresql://postgres:YOUR_PASSWORD@db.xxxxx.supabase.co:5432/postgres

# 3. ไม่ควรมี prefix "DATABASE_URL="
# ✅ ถูก: DATABASE_URL=postgresql://...
# ❌ ผิด: DATABASE_URL=DATABASE_URL=postgresql://...
```

---

## 5️⃣ Streamlit Cloud Configuration

### ตรวจสอบ Secrets:
```
1. ไปที่ Streamlit Cloud Dashboard
2. เลือก app → Settings → Secrets
3. เช็คว่ามี DATABASE_URL
4. Format:
   DATABASE_URL = "postgresql://postgres:password@host:5432/postgres"
```

---

## 📊 Quick Diagnostic

รันคำสั่งนี้เพื่อตรวจสอบระบบ:

```bash
# Test 1: ตรวจสอบ environment
python -c "import os; from dotenv import load_dotenv; load_dotenv(); print('DATABASE_URL:', 'OK' if os.getenv('DATABASE_URL') else 'MISSING')"

# Test 2: ตรวจสอบการ import modules
python -c "from src.analysis import load_data; print('Import: OK')"

# Test 3: ลองโหลดข้อมูล
python -c "from src.analysis import load_data; df = load_data(); print(f'Records: {len(df)}')"
```

---

## ✅ สรุป: แนวทางที่ดีที่สุด

### สำหรับ Development (Local):
```
✅ ใช้สำหรับแก้ไข code เท่านั้น
❌ อย่าคาดหวังว่า Dashboard จะทำงาน (ถ้ามีปัญหา network)
✅ ทดสอบ logic ด้วย unit tests
```

### สำหรับ Testing & Production:
```
✅ ใช้ Streamlit Cloud เป็นหลัก
✅ ส่งข้อมูลผ่าน LINE Bot
✅ ดู Dashboard บน Cloud
✅ Network stable และเชื่อถือได้
```

---

## 🆘 ยังแก้ไม่ได้?

1. **ตรวจสอบ Streamlit Cloud Dashboard**
   - ถ้าทำงานบน Cloud = ปัญหาอยู่ที่ local network
   - ถ้าไม่ทำงานบน Cloud = ปัญหาอยู่ที่ config/data

2. **ตรวจสอบ LINE Bot**
   - ลองส่งข้อมูลผ่าน LINE Bot
   - ดูว่ามี response กลับมาไหม
   - เช็ค log ใน Render/Railway

3. **ตรวจสอบ Supabase**
   - เข้า Supabase Dashboard
   - ไปที่ Table Editor → records
   - ดูว่ามีข้อมูลไหม

4. **GitHub Issues**
   - ถ้ายังไม่ได้ ให้เปิด issue บน GitHub repo
   - แนบ error messages และ screenshots

---

## 📞 Contact & Support

- **Documentation**: [README.md](./README.md)
- **Database Setup**: [database/README.md](./database/README.md)
- **GitHub Issues**: Report bugs and request features

---

**สร้างโดย**: LHome Medical System
**อัพเดทล่าสุด**: 2024
