import pandas as pd
import psycopg2
import os
import socket
import plotly.express as px
from urllib.parse import urlparse
from dotenv import load_dotenv

load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")

# บังคับให้ใช้ IPv4 เท่านั้น (แก้ปัญหา IPv6 network unreachable)
def force_ipv4_dns(hostname):
    """Force DNS resolution to IPv4 only"""
    try:
        result = socket.getaddrinfo(hostname, None, socket.AF_INET, socket.SOCK_STREAM)
        if result:
            return result[0][4][0]
    except Exception as e:
        print(f"[DNS] IPv4 resolution failed for {hostname}: {e}")
    return hostname

def load_data():
    """โหลดข้อมูลจาก PostgreSQL (Supabase) เป็น Pandas DataFrame"""
    if not DATABASE_URL or DATABASE_URL.strip() == "":
        print("[Error] DATABASE_URL not found for loading dashboard data")
        return pd.DataFrame()

    if DATABASE_URL.startswith('DATABASE_URL='):
        print("[Error] Invalid DATABASE_URL format")
        return pd.DataFrame()

    conn = None
    try:
        # ลองใช้ connection string โดยตรงก่อน (ทำงานได้ดีกับ Supabase)
        conn = psycopg2.connect(DATABASE_URL, connect_timeout=15)

        # ดึงข้อมูลจากฐานข้อมูลมาใส่ใน DataFrame ทันที
        df = pd.read_sql("SELECT * FROM records ORDER BY date DESC", conn)
        return df
    except Exception as e:
        print(f"[Error] Failed to load data: {e}")
        # Fallback: ลองใช้พารามิเตอร์แยก
        try:
            parsed = urlparse(DATABASE_URL)
            if not parsed.hostname:
                return pd.DataFrame()

            is_pooler = 'pooler' in parsed.hostname

            conn = psycopg2.connect(
                host=parsed.hostname,
                port=parsed.port or 5432,
                user=parsed.username,
                password=parsed.password,
                database=parsed.path.lstrip('/').split('?')[0],
                connect_timeout=15,
                sslmode='require' if is_pooler else 'prefer'
            )
            df = pd.read_sql("SELECT * FROM records ORDER BY date DESC", conn)
            return df
        except Exception as fallback_error:
            print(f"[Error] Fallback also failed: {fallback_error}")
            return pd.DataFrame()
    finally:
        if conn:
            conn.close()

def create_trend_chart(df, patient_name, param_col, title_name):
    """ฟังก์ชันสร้างกราฟแนวโน้ม (Trend Chart) ด้วย Plotly"""
    patient_df = df[df['notes'] == patient_name].copy()

    if patient_df.empty or param_col not in patient_df.columns:
        return None

    # แปลงคอลัมน์นั้นๆ ให้เป็นตัวเลข
    patient_df[param_col] = pd.to_numeric(patient_df[param_col], errors='coerce')

    fig = px.line(
        patient_df,
        x='date',
        y=param_col,
        markers=True,
        title=f"แนวโน้ม {title_name} ของคนไข้: {patient_name}",
        labels={'date': 'วันที่ตรวจ', param_col: title_name},
        template="plotly_white"
    )
    # เพิ่มลูกเล่นให้เส้นกราฟ
    fig.update_traces(line=dict(width=3), marker=dict(size=8))
    return fig