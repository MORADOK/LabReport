import sqlite3
import os

# กำหนด Path ให้ไฟล์ .db อยู่ในโฟลเดอร์เดียวกับไฟล์นี้เสมอ
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, "data", "urine_records.db")

def init_db():
    """สร้างตารางและอัปเดตโครงสร้างอัตโนมัติ (Auto Migration)"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # 1. สร้างตารางหลัก (ถ้ายังไม่มี)
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
    
    # 2. ตรวจสอบว่ามีคอลัมน์ 'notes' หรือยัง (ถ้ายังไม่มีให้เพิ่มเข้าไป)
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