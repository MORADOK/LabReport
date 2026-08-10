import pandas as pd
import psycopg2
import os
import socket
import plotly.express as px
from urllib.parse import urlparse
from dotenv import load_dotenv
from src.database import get_connection

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
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        # 🌟 ใช้ท่า Execute สดๆ แทน เพื่อลด Dependency ของ SQLAlchemy
        cursor.execute("SELECT * FROM records ORDER BY date DESC")
        
        # ดึงชื่อคอลัมน์จาก Database
        columns = [desc[0] for desc in cursor.description]
        
        # ดึงข้อมูลทั้งหมดและสร้างเป็น DataFrame
        df = pd.DataFrame(cursor.fetchall(), columns=columns)
        return df
        
    except Exception as e:
        print(f"Error loading data: {e}")
        return pd.DataFrame()
    finally:
        if conn:
            cursor.close()
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