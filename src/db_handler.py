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
    """Preserve DSN escaping, TLS settings and other libpq connection options."""
    if not DATABASE_URL or DATABASE_URL.startswith("DATABASE_URL="):
        raise ValueError("DATABASE_URL is missing or malformed")
    if retries < 1:
        raise ValueError("retries must be positive")
    parsed = urlparse(DATABASE_URL)
    if parsed.scheme not in ("postgres", "postgresql") or not parsed.hostname:
        raise ValueError("DATABASE_URL must be a PostgreSQL URL")
    for attempt in range(retries):
        try:
            # libpq parses percent-encoded credentials and honors sslmode in the URL.
            return psycopg2.connect(DATABASE_URL, connect_timeout=15)
        except psycopg2.OperationalError as error:
            if attempt + 1 == retries:
                raise ConnectionError("Database connection failed") from error
            time.sleep(retry_delay)


def init_db():
    """สร้างตารางและอัปเดตโครงสร้างอัตโนมัติ (Auto Migration)"""
    conn = None
    cursor = None
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
        cursor.execute('''
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name='records' AND column_name='notes';
        ''')
        if not cursor.fetchone():
            print("[Auto Migration] Adding 'notes' column to PostgreSQL...")
            cursor.execute("ALTER TABLE records ADD COLUMN notes TEXT DEFAULT ''")

        # 3. ตรวจสอบและเพิ่มคอลัมน์ 'clinical_summary'
        cursor.execute('''
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name='records' AND column_name='clinical_summary';
        ''')
        if not cursor.fetchone():
            print("[Auto Migration] Adding 'clinical_summary' column...")
            cursor.execute("ALTER TABLE records ADD COLUMN clinical_summary TEXT DEFAULT ''")

        # 4. ตรวจสอบและเพิ่มคอลัมน์ 'clinical_bullets'
        cursor.execute('''
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name='records' AND column_name='clinical_bullets';
        ''')
        if not cursor.fetchone():
            print("[Auto Migration] Adding 'clinical_bullets' column...")
            cursor.execute("ALTER TABLE records ADD COLUMN clinical_bullets TEXT DEFAULT '[]'")

        cursor.execute("ALTER TABLE public.records ADD COLUMN IF NOT EXISTS diagnostics JSONB")
        cursor.execute("ALTER TABLE public.records ENABLE ROW LEVEL SECURITY")
        # Repair the legacy permissive policy even when RLS was already enabled.
        cursor.execute('DROP POLICY IF EXISTS "Service role full access" ON public.records')
        cursor.execute("""
            CREATE POLICY "Service role full access" ON public.records
            FOR ALL TO service_role USING (true) WITH CHECK (true)
        """)
        conn.commit()
        print("[Success] Database structure updated and secured!")

    except Exception as e:
        if conn:
            conn.rollback()
        raise RuntimeError("Database migration failed") from e
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

def insert_record(date, urobilinogen, glucose, bilirubin, ketones, specific_gravity, blood, ph, protein, nitrite, leukocytes, ascorbic_acid, notes="", clinical_summary="", clinical_bullets=None, diagnostics=None):
    """ฟังก์ชันบันทึกผลตรวจลง Database พร้อม clinical analysis"""
    conn = None
    cursor = None
    try:
        conn = get_connection()
        cursor = conn.cursor()

        # แปลง list ของ clinical_bullets เป็น JSON string
        import json
        if isinstance(clinical_bullets, str):
            clinical_bullets = json.loads(clinical_bullets)
        if clinical_bullets is None:
            clinical_bullets = []
        if not isinstance(clinical_bullets, list):
            raise ValueError("clinical_bullets must be a list")
        bullets_json = json.dumps(clinical_bullets, ensure_ascii=False)
        diagnostics_json = json.dumps(diagnostics or {}, ensure_ascii=False, allow_nan=False)

        # PostgreSQL ใช้ %s ในการส่งค่าตัวแปร
        query = '''
            INSERT INTO records (
                date, urobilinogen, glucose, bilirubin, ketones,
                specific_gravity, blood, ph, protein, nitrite, leukocytes, ascorbic_acid, notes,
                clinical_summary, clinical_bullets, diagnostics
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        '''

        values = (
            date, urobilinogen, glucose, bilirubin, ketones,
            specific_gravity, blood, ph, protein, nitrite, leukocytes, ascorbic_acid, notes,
            clinical_summary, bullets_json, diagnostics_json
        )

        cursor.execute(query, values)
        conn.commit()
        return True
    except Exception as e:
        print(f"[Insert Error] Failed to insert record: {e}")
        return False
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

# Run explicitly during deployment: python -m src.db_handler
if __name__ == "__main__":
    init_db()
