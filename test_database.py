"""
Test script for database operations
"""
import sys
import os
from datetime import datetime

# Set UTF-8 encoding for Windows console
if sys.platform == 'win32':
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

sys.path.append(os.path.dirname(__file__))
from src import database, analysis

def test_database():
    print("=" * 50)
    print("Testing Database Operations")
    print("=" * 50)

    # Test 1: Insert a test record
    print("\n[Test 1] Inserting test record...")
    try:
        test_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        success = database.insert_record(
            date=test_date,
            urobilinogen="normal",
            glucose="neg",
            bilirubin="neg",
            ketones="neg",
            specific_gravity=1.020,
            blood="neg",
            ph=6.5,
            protein="neg",
            nitrite="neg",
            leukocytes="neg",
            ascorbic_acid="neg",
            notes="Test Patient - ทดสอบระบบ"
        )
        if success:
            print("✅ Insert successful")
        else:
            print("❌ Insert failed")
    except Exception as e:
        print(f"❌ Error during insert: {e}")
        return False

    # Test 2: Load data
    print("\n[Test 2] Loading data from database...")
    try:
        df = analysis.load_data()
        if df.empty:
            print("⚠️  Database is empty")
        else:
            print(f"✅ Loaded {len(df)} records")
            print("\nLatest 5 records:")
            print(df.head()[['date', 'notes', 'ph', 'protein', 'blood']])
    except Exception as e:
        print(f"❌ Error loading data: {e}")
        return False

    # Test 3: Check database schema
    print("\n[Test 3] Checking database schema...")
    try:
        import sqlite3
        BASE_DIR = os.path.dirname(os.path.abspath(__file__))
        DB_PATH = os.path.join(BASE_DIR, "data", "urine_records.db")

        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("PRAGMA table_info(records)")
        columns = cursor.fetchall()

        print("Database columns:")
        for col in columns:
            print(f"  - {col[1]} ({col[2]})")

        conn.close()
        print("✅ Schema check complete")
    except Exception as e:
        print(f"❌ Error checking schema: {e}")
        return False

    print("\n" + "=" * 50)
    print("All database tests completed successfully!")
    print("=" * 50)
    return True

if __name__ == "__main__":
    test_database()
