import pandas as pd
import psycopg2
import os
import json
import ast
import plotly.express as px
from dotenv import load_dotenv
from src.db_handler import get_connection

load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")

def sanitize_thai_text(text):
    """
    🧹 Remove corrupted characters from Thai text

    Fixes common issues where characters like 'b', 'f', 'fb' are incorrectly
    inserted into Thai words (e.g., "ทำbงาน" -> "ทำงาน").

    Args:
        text: Text string that may contain corrupted characters

    Returns:
        str: Cleaned text with corrupted characters removed
    """
    if not isinstance(text, str):
        text = str(text)

    # Common corrupted patterns found in Thai text
    corrupted_patterns = {
        "ทำbงาน": "ทำงาน",
        "น้ำfb": "น้ำ",
        "จำbเพาะ": "จำเพาะ",
        "ความbถ่วง": "ความถ่วง",
        "ปัสbสาวะ": "ปัสสาวะ",
        "เม็ดbเลือด": "เม็ดเลือด",
        "โปรbตีน": "โปรตีน",
        "กลูbโคส": "กลูโคส",
        "คีbโตน": "คีโตน",
        "บิfลิรูบิน": "บิลิรูบิน",
        "ไนfไตรต์": "ไนไตรต์",
        "วิfตามิน": "วิตามิน",
    }

    # Apply all pattern replacements
    for corrupted, clean in corrupted_patterns.items():
        text = text.replace(corrupted, clean)

    return text

def parse_clinical_bullets(raw_bullets, sanitize=True):
    """
    🌟 Robust JSON/List parsing with Unicode escape handling

    Safely converts clinical_bullets from database (which might be JSON string,
    Unicode-escaped string, or already a list) into a proper Python list.

    Args:
        raw_bullets: Raw data from database (str, list, or any type)
        sanitize: If True, apply text sanitization to remove corrupted characters

    Returns:
        list: Parsed clinical bullets, or error message list if parsing fails
    """
    try:
        # 1. Handle if already a list
        if isinstance(raw_bullets, list):
            return raw_bullets

        # 2. Handle string inputs
        if isinstance(raw_bullets, str):
            # 2.1 Clean up Unicode escape sequences (e.g., \u0e34 -> Thai characters)
            if r'\u0e' in raw_bullets or '\\u0e' in raw_bullets:
                try:
                    # Decode Unicode escapes back to actual Thai text
                    raw_bullets = raw_bullets.encode('utf-8').decode('unicode_escape')
                except Exception:
                    pass  # If decoding fails, continue with original string

            # 2.2 Try JSON parsing first (safer for most cases)
            try:
                db_bullets = json.loads(raw_bullets)
            except json.JSONDecodeError:
                # 2.3 Fallback to ast.literal_eval for Python-style strings
                try:
                    db_bullets = ast.literal_eval(raw_bullets)
                except (ValueError, SyntaxError):
                    # If both fail, treat the entire string as a single bullet point
                    db_bullets = [raw_bullets]
        else:
            # 3. For any other type, convert to string and wrap in list
            db_bullets = [str(raw_bullets)]

        # 4. Ensure result is always a list
        if not isinstance(db_bullets, list):
            db_bullets = [str(db_bullets)]

        # 5. Sanitize Thai text if requested
        if sanitize:
            db_bullets = [sanitize_thai_text(bullet) for bullet in db_bullets]

        return db_bullets

    except Exception as e:
        # Final fallback: return error message
        return ["ไม่สามารถโหลดข้อบ่งชี้ทางคลินิกได้ (Data Format Error)"]

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