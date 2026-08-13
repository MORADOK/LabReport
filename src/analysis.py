import pandas as pd
import psycopg2
import os
import json
import ast
import re
import plotly.express as px
from dotenv import load_dotenv
from src.db_handler import get_connection

load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")

def sanitize_thai_text(text):
    """
    🧹 Advanced Thai text sanitization with comprehensive corruption removal

    Removes English letters (a-z, A-Z) that are incorrectly inserted between or after
    Thai characters, while preserving valid medical terms like "Glucose (GLU)".

    Examples:
        "น้ำgcตาล" -> "น้ำตาล"
        "ทำNงาน" -> "ทำงาน"
        "ปัสbสาวะ" -> "ปัสสาวะ"
        "คำnแนะนำn:" -> "คำแนะนำ:"
        "Glucose (GLU)" -> "Glucose (GLU)" (preserved)

    Args:
        text: Text string that may contain corrupted characters

    Returns:
        str: Cleaned text with corrupted characters removed
    """
    if not isinstance(text, str):
        text = str(text)

    # Pattern 1: Remove [a-zA-Z]+ if preceded AND followed by Thai characters
    # Handles: "น้ำgcตาล" -> "น้ำตาล", "ทำNงาน" -> "ทำงาน"
    cleaned = re.sub(r'(?<=[\u0E00-\u0E7F])[a-zA-Z]+(?=[\u0E00-\u0E7F])', '', text)

    # Pattern 2: Remove [a-zA-Z]+ after Thai characters before whitespace/punctuation
    # Handles: "คำnแนะนำn:" -> "คำแนะนำ:", "สำnหรับ" -> "สำหรับ"
    cleaned = re.sub(r'(?<=[\u0E00-\u0E7F])[a-zA-Z]+(?=[\s:;,.\)]|$)', '', cleaned)

    return cleaned

def parse_clinical_bullets(raw_bullets, sanitize=True):
    """
    🌟 Bullet-proof JSON/List parser with 5-tier fallback system

    Safely converts clinical_bullets from database (which might be JSON string,
    Unicode-escaped string, backslash-wrapped text, or already a list) into a proper Python list.

    Fallback tiers:
    - Plan 0: Backslash wrapper detection - Extract text between \\ ... \\
    - Plan A: json.loads() - Standard JSON parsing
    - Plan B: ast.literal_eval() - Python literal parsing
    - Plan C: Regex extraction - Extract quoted strings
    - Plan D: Ultimate fallback - Return cleaned raw text

    Args:
        raw_bullets: Raw data from database (str, list, or any type)
        sanitize: If True, apply text sanitization to remove corrupted characters

    Returns:
        list: Parsed clinical bullets, always returns a list (never fails)
    """
    try:
        # 0. Handle if already a list
        if isinstance(raw_bullets, list):
            if sanitize:
                return [sanitize_thai_text(str(b)) for b in raw_bullets]
            return raw_bullets

        # 1. Convert to string and clean artifacts + newlines
        if not isinstance(raw_bullets, str):
            raw_bullets = str(raw_bullets)

        # PLAN 0: Detect backslash wrapper (e.g., \\text1\\, \\text2\\)
        # This handles AI outputs that wrap each bullet in backslashes
        if '\\\\' in raw_bullets:
            extracted = re.findall(r'\\\\(.*?)\\\\', raw_bullets)
            if extracted:
                # Remove trailing commas and filter out very short strings
                cleaned_list = [sanitize_thai_text(b.strip(',').strip()) if sanitize else b.strip(',').strip()
                               for b in extracted if len(b.strip()) > 5]
                if cleaned_list:
                    return cleaned_list

        # Clean up artifacts and problematic newlines that break JSON
        cleaned_data = raw_bullets.replace('\n', ' ').strip()

        # 2. Decode Unicode escape sequences if present
        if r'\u0e' in cleaned_data or '\\u0e' in cleaned_data:
            try:
                cleaned_data = cleaned_data.encode('utf-8').decode('unicode_escape')
            except Exception:
                pass  # Continue with original if decoding fails

        # PLAN A: Try JSON parsing first (most reliable for standard JSON)
        try:
            db_bullets = json.loads(cleaned_data)
            if isinstance(db_bullets, list):
                # Success! Sanitize if requested
                if sanitize:
                    return [sanitize_thai_text(str(b)) for b in db_bullets]
                return [str(b) for b in db_bullets]
        except (json.JSONDecodeError, ValueError):
            pass  # Move to Plan B

        # PLAN B: Try ast.literal_eval (handles Python list repr)
        try:
            db_bullets = ast.literal_eval(cleaned_data)
            if isinstance(db_bullets, list):
                if sanitize:
                    return [sanitize_thai_text(str(b)) for b in db_bullets]
                return [str(b) for b in db_bullets]
        except (ValueError, SyntaxError):
            pass  # Move to Plan C

        # PLAN C: Regex extraction - Extract all quoted strings "..."
        # This works even if JSON structure is malformed
        extracted = re.findall(r'"([^"]*)"', cleaned_data)
        if extracted:
            # Filter out very short strings (likely not real content)
            valid_bullets = [str(b) for b in extracted if len(str(b)) > 5]
            if valid_bullets:
                if sanitize:
                    return [sanitize_thai_text(b) for b in valid_bullets]
                return valid_bullets

        # PLAN D: Ultimate fallback - Clean and return as single-item list
        # Remove brackets and quotes, sanitize if requested
        fallback_text = cleaned_data.replace('[', '').replace(']', '').replace('"', '').strip()
        if fallback_text:
            if sanitize:
                return [sanitize_thai_text(fallback_text)]
            return [fallback_text]

        # If everything is empty, return empty list
        return []

    except Exception as e:
        # Absolute final fallback: return error message
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