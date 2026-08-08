import os
import psycopg2
from dotenv import load_dotenv

# โหลดตัวแปรจากไฟล์ .env (สำหรับการรัน Local)
load_dotenv()

# ดึง URL ฐานข้อมูลของ Supabase จาก Environment Variable
DATABASE_URL = os.getenv("DATABASE_URL")

def get_connection():
    """ฟังก์ชันจัดการ Connection ไปยัง PostgreSQL"""
    if not DATABASE_URL:
        raise ValueError("❌ ไม่พบ DATABASE_URL กรุณาใส่ URL ของ Supabase ในไฟล์ .env")
    return psycopg2.connect(DATABASE_URL)

def init_db():
    """สร้างตารางและอัปเดตโครงสร้างอัตโนมัติ (Auto Migration)"""
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        # 1. สร้างตารางหลัก (ใช้ SERIAL แทน AUTOINCREMENT)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS records (
                id SERIAL PRIMARY KEY,
                date TIMESTAMP,
                urobilinogen VARCHAR(50),
                glucose VARCHAR(50),
                bilirubin VARCHAR(50),
                ketones VARCHAR(50),
                specific_gravity REAL,
                blood VARCHAR(50),
                ph REAL,
                protein VARCHAR(50),
                nitrite VARCHAR(50),
                leukocytes VARCHAR(50),
                ascorbic_acid VARCHAR(50),
                notes TEXT DEFAULT ''
            )
        ''')
        
        # 2. ตรวจสอบว่ามีคอลัมน์ 'notes' หรือยัง 
        # (PostgreSQL ใช้ information_schema ในการเช็คคอลัมน์)
        cursor.execute('''
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name='records' AND column_name='notes';
        ''')
        
        if not cursor.fetchone():
            print("⚙️ [Auto Migration] กำลังเพิ่มคอลัมน์ 'notes' ลงใน PostgreSQL...")
            cursor.execute("ALTER TABLE records ADD COLUMN notes TEXT DEFAULT ''")
            print("✅ อัปเดตโครงสร้างฐานข้อมูลสำเร็จ!")
            
        conn.commit()
        print("🟢 [Setup] เชื่อมต่อฐานข้อมูล Supabase สำเร็จ พร้อมใช้งาน!")
        
    except Exception as e:
        print(f"❌ [DB Error] เกิดข้อผิดพลาดในการตั้งค่าฐานข้อมูล: {e}")
    finally:
        if conn:
            cursor.close()
            conn.close()

def insert_record(date, urobilinogen, glucose, bilirubin, ketones, specific_gravity, blood, ph, protein, nitrite, leukocytes, ascorbic_acid, notes=""):
    """ฟังก์ชันบันทึกผลตรวจลง Database"""
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        # PostgreSQL ใช้ %s ในการส่งค่าตัวแปร
        query = '''
            INSERT INTO records (
                date, urobilinogen, glucose, bilirubin, ketones, 
                specific_gravity, blood, ph, protein, nitrite, leukocytes, ascorbic_acid, notes
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        '''
        
        values = (
            date, urobilinogen, glucose, bilirubin, ketones, 
            specific_gravity, blood, ph, protein, nitrite, leukocytes, ascorbic_acid, notes
        )
        
        cursor.execute(query, values)
        conn.commit()
        return True
    except Exception as e:
        print(f"❌ [Insert Error] เกิดข้อผิดพลาดตอนบันทึกข้อมูล: {e}")
        return False
    finally:
        if conn:
            cursor.close()
            conn.close()

# ตรวจสอบและสร้างฐานข้อมูลทันทีเมื่อไฟล์ถูกเรียกใช้
init_db()