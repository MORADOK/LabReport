import pandas as pd
import sqlite3
import os
import plotly.express as px

# ชี้ไปที่โฟลเดอร์ data/
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, "data", "urine_records.db")

def load_data():
    """โหลดข้อมูลจาก SQLite เป็น Pandas DataFrame"""
    if not os.path.exists(DB_PATH):
        return pd.DataFrame()
        
    try:
        conn = sqlite3.connect(DB_PATH)
        df = pd.read_sql("SELECT * FROM records ORDER BY date DESC", conn)
        conn.close()
        return df
    except Exception as e:
        print(f"Error loading data: {e}")
        return pd.DataFrame()

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