import pandas as pd
import psycopg2
import os
import plotly.express as px
from dotenv import load_dotenv

load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")

def load_data():
    """โหลดข้อมูลจาก PostgreSQL (Supabase) เป็น Pandas DataFrame"""
    if not DATABASE_URL:
        print("❌ ไม่พบ DATABASE_URL สำหรับดึงข้อมูลเข้า Dashboard")
        return pd.DataFrame()
        
    conn = None
    try:
        conn = psycopg2.connect(DATABASE_URL)
        # ดึงข้อมูลจากฐานข้อมูลมาใส่ใน DataFrame ทันที
        df = pd.read_sql("SELECT * FROM records ORDER BY date DESC", conn)
        return df
    except Exception as e:
        print(f"Error loading data: {e}")
        return pd.DataFrame()
    finally:
        if conn:
            conn.close()

# (ฟังก์ชัน create_trend_chart ด้านล่างยังคงใช้โค้ดเดิมได้เลยครับ ไม่ต้องแก้)