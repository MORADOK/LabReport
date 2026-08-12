import pandas as pd
import psycopg2
import os
import plotly.express as px
from dotenv import load_dotenv
from src.db_handler import get_connection

load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")

def load_data():
    """Load data with optimized query - only fetch necessary columns"""
    conn = None
    cursor = None
    try:
        conn = get_connection()
        cursor = conn.cursor()

        # 🚀 Optimize: Select only needed columns and limit rows if dataset is huge
        # Add index hint for faster sorting
        cursor.execute("""
            SELECT id, date, notes, urobilinogen, glucose, bilirubin, ketones,
                   specific_gravity, blood, ph, protein, nitrite, leukocytes,
                   ascorbic_acid, clinical_summary, clinical_bullets
            FROM records
            ORDER BY date DESC
            LIMIT 1000
        """)

        # ดึงชื่อคอลัมน์จาก Database
        columns = [desc[0] for desc in cursor.description]

        # ดึงข้อมูลทั้งหมดและสร้างเป็น DataFrame
        rows = cursor.fetchall()
        df = pd.DataFrame(rows, columns=columns)

        # 🚀 Pre-convert date column to datetime for faster operations
        if not df.empty and 'date' in df.columns:
            df['date'] = pd.to_datetime(df['date'], errors='coerce')

        return df

    except psycopg2.Error as db_err:
        print(f"Database error loading data: {db_err}")
        return pd.DataFrame()
    except Exception as e:
        print(f"Error loading data: {e}")
        return pd.DataFrame()
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

def create_trend_chart(df, patient_name, param_col, title_name):
    """ฟังก์ชันสร้างกราฟแนวโน้ม (Trend Chart) ด้วย Plotly"""
    try:
        patient_df = df[df['notes'] == patient_name].copy()

        if patient_df.empty or param_col not in patient_df.columns:
            return None

        # แปลงคอลัมน์นั้นๆ ให้เป็นตัวเลข
        patient_df[param_col] = pd.to_numeric(patient_df[param_col], errors='coerce')

        # กรองแถวที่เป็น NaN ออก
        patient_df = patient_df.dropna(subset=[param_col])

        if patient_df.empty:
            return None

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
    except Exception as e:
        print(f"Error creating trend chart: {e}")
        return None