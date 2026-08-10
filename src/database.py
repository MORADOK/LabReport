import os
import json
import psycopg2
from dotenv import load_dotenv

load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")

def get_connection():
    db_url = os.getenv("DATABASE_URL")
    if not db_url or db_url.strip() == "":
        raise ValueError("❌ ไม่พบ DATABASE_URL")
    return psycopg2.connect(db_url)

def init_db():
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        # 1. สร้างตารางหลัก
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
        
        # 2. ระบบ Auto Migration: เพิ่มคอลัมน์ใหม่สำหรับเก็บคำวิเคราะห์ทางคลินิก
        cursor.execute("SELECT column_name FROM information_schema.columns WHERE table_name='records' AND column_name='clinical_summary';")
        if not cursor.fetchone():
            cursor.execute("ALTER TABLE records ADD COLUMN clinical_summary TEXT DEFAULT ''")
            
        cursor.execute("SELECT column_name FROM information_schema.columns WHERE table_name='records' AND column_name='clinical_bullets';")
        if not cursor.fetchone():
            cursor.execute("ALTER TABLE records ADD COLUMN clinical_bullets TEXT DEFAULT '[]'")
            
        conn.commit()
        print("✅ อัปเดตโครงสร้างฐานข้อมูลรองรับระบบ PDF สำเร็จ!")
    except Exception as e:
        print(f"❌ DB Error: {e}")
    finally:
        if conn: cursor.close(); conn.close()

def insert_record(date, urobilinogen, glucose, bilirubin, ketones, specific_gravity, blood, ph, protein, nitrite, leukocytes, ascorbic_acid, notes="", clinical_summary="", clinical_bullets=[]):
    """เพิ่มพารามิเตอร์ clinical_summary และ clinical_bullets"""
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        # แปลง List ของ Bullet points ให้เป็น JSON String ก่อนบันทึกลง Database
        bullets_json = json.dumps(clinical_bullets, ensure_ascii=False)
        
        query = '''
            INSERT INTO records (
                date, urobilinogen, glucose, bilirubin, ketones, 
                specific_gravity, blood, ph, protein, nitrite, leukocytes, ascorbic_acid, notes, clinical_summary, clinical_bullets
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        '''
        
        values = (
            date, urobilinogen, glucose, bilirubin, ketones, 
            specific_gravity, blood, ph, protein, nitrite, leukocytes, ascorbic_acid, notes, clinical_summary, bullets_json
        )
        
        cursor.execute(query, values)
        conn.commit()
        return True
    except Exception as e:
        print(f"❌ Insert Error: {e}")
        return False
    finally:
        if conn: cursor.close(); conn.close()