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