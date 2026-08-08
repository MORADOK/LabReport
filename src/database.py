import sqlite3
import os

# 1. กำหนด Path ให้อ้างอิงจากโฟลเดอร์หลักเสมอ
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_DIR = os.path.join(BASE_DIR, "data")
DB_PATH = os.path.join(DB_DIR, "urine_records.db")

def init_db():
    """สร้างโฟลเดอร์ ตาราง และอัปเดตโครงสร้างอัตโนมัติ (Auto Migration)"""
    
    # 2. 🌟 เช็คและสร้างโฟลเดอร์ data/ อัตโนมัติ (หัวใจสำคัญที่แก้ Error บน Render)
    if not os.path.exists(DB_DIR):
        os.makedirs(DB_DIR)
        print("⚙️ [Setup] สร้างโฟลเดอร์ data/ สำหรับเก็บ Database อัตโนมัติเรียบร้อย")

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # 3. สร้างตารางหลัก (ถ้ายังไม่มี)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT,
            urobilinogen TEXT,
            glucose TEXT,
            bilirubin TEXT,
            ketones TEXT,
            specific_gravity REAL,
            blood TEXT,
            ph REAL,
            protein TEXT,
            nitrite TEXT,
            leukocytes TEXT,
            ascorbic_acid TEXT
        )
    ''')
    
    # 4. ตรวจสอบว่ามีคอลัมน์ 'notes' หรือยัง (Auto Migration)
    cursor.execute("PRAGMA table_info(records)")
    columns = [col[1] for col in cursor.fetchall()]
    
    if 'notes' not in columns:
        print("⚙️ [Auto Migration] กำลังเพิ่มคอลัมน์ 'notes' ลงในฐานข้อมูล...")
        cursor.execute("ALTER TABLE records ADD COLUMN notes TEXT DEFAULT ''")
        print("✅ อัปเดตโครงสร้างฐานข้อมูลสำเร็จ!")
        
    conn.commit()
    conn.close()

def insert_record(date, urobilinogen, glucose, bilirubin, ketones, specific_gravity, blood, ph, protein, nitrite, leukocytes, ascorbic_acid, notes=""):
    """ฟังก์ชันบันทึกผลตรวจลง Database"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    query = '''
        INSERT INTO records (
            date, urobilinogen, glucose, bilirubin, ketones, 
            specific_gravity, blood, ph, protein, nitrite, leukocytes, ascorbic_acid, notes
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    '''
    
    values = (
        date, urobilinogen, glucose, bilirubin, ketones, 
        specific_gravity, blood, ph, protein, nitrite, leukocytes, ascorbic_acid, notes
    )
    
    cursor.execute(query, values)
    conn.commit()
    conn.close()
    return True

# เรียกใช้งานตอนโหลดไฟล์ เพื่อตรวจสอบและอัปเดต DB ทันที
init_db()