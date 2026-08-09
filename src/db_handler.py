import os
import psycopg2
import time
import socket
from urllib.parse import urlparse
from dotenv import load_dotenv

# โหลดตัวแปรจากไฟล์ .env (สำหรับการรัน Local)
load_dotenv()

# ดึง URL ฐานข้อมูลของ Supabase จาก Environment Variable
DATABASE_URL = os.getenv("DATABASE_URL")

# บังคับให้ใช้ IPv4 เท่านั้น (แก้ปัญหา IPv6 network unreachable)
def force_ipv4_dns(hostname):
    """Force DNS resolution to IPv4 only"""
    try:
        # ใช้ AF_INET (IPv4 only) แทน AF_UNSPEC (IPv4/IPv6)
        result = socket.getaddrinfo(hostname, None, socket.AF_INET, socket.SOCK_STREAM)
        if result:
            return result[0][4][0]  # Return first IPv4 address
    except Exception as e:
        print(f"[DNS] IPv4 resolution failed for {hostname}: {e}")
    return hostname  # Fallback to original hostname

def get_connection(retries=3, retry_delay=2):
    """ฟังก์ชันจัดการ Connection ไปยัง PostgreSQL (แก้ปัญหา IPv6 + Retry Logic)"""
    if not DATABASE_URL:
        raise ValueError("[Error] DATABASE_URL not found in .env file")

    last_error = None
    for attempt in range(retries):
        try:
            # Parse URL
            parsed = urlparse(DATABASE_URL)

            # บังคับให้ใช้ IPv4 address
            ipv4_host = force_ipv4_dns(parsed.hostname)
            print(f"[DNS] Resolved {parsed.hostname} to {ipv4_host}")

            # สร้าง connection แบบใช้พารามิเตอร์แยกเพื่อควบคุม connection ได้ดีกว่า
            conn = psycopg2.connect(
                host=ipv4_host,  # ใช้ IPv4 address แทน hostname
                port=parsed.port or 5432,
                user=parsed.username,
                password=parsed.password,
                database=parsed.path.lstrip('/'),
                connect_timeout=15,
                keepalives=1,
                keepalives_idle=30,
                keepalives_interval=10,
                keepalives_count=5
            )
            return conn
        except (psycopg2.OperationalError, Exception) as e:
            last_error = e
            if attempt < retries - 1:
                print(f"[Retry {attempt + 1}/{retries}] Connection failed, retrying in {retry_delay}s...")
                time.sleep(retry_delay)
            else:
                # Fallback: ลองใช้ connection string ปกติ
                try:
                    print(f"[Fallback] Trying direct connection string...")
                    return psycopg2.connect(DATABASE_URL, connect_timeout=15)
                except Exception as fallback_error:
                    raise ConnectionError(f"[Connection Failed] All connection attempts failed. Last error: {last_error}")

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
            print("[Auto Migration] Adding 'notes' column to PostgreSQL...")
            cursor.execute("ALTER TABLE records ADD COLUMN notes TEXT DEFAULT ''")
            print("[Success] Database structure updated!")

        conn.commit()
        print("[Setup] Connected to Supabase database successfully!")

    except Exception as e:
        print(f"[DB Error] Database setup failed: {e}")
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
        print(f"[Insert Error] Failed to insert record: {e}")
        return False
    finally:
        if conn:
            cursor.close()
            conn.close()

# ตรวจสอบและสร้างฐานข้อมูลทันทีเมื่อไฟล์ถูกเรียกใช้
init_db()
