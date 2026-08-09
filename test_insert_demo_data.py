"""
Test script to insert demo data into the database
This helps verify that the dashboard can display data correctly
"""
import os
from datetime import datetime, timedelta
from dotenv import load_dotenv
from src import db_handler

load_dotenv()

def insert_demo_data():
    """Insert sample patient data for testing"""
    print("🔄 Inserting demo data...")

    # Demo data for 3 patients with different test results
    demo_patients = [
        {
            "name": "ทดสอบ ระบบ",
            "tests": [
                {
                    "urobilinogen": "0.1 Normal",
                    "glucose": "neg.",
                    "bilirubin": "neg.",
                    "ketones": "neg.",
                    "specific_gravity": 1.020,
                    "blood": "neg.",
                    "ph": 6.5,
                    "protein": "neg.",
                    "nitrite": "neg.",
                    "leukocytes": "neg.",
                    "ascorbic_acid": "neg.",
                    "clinical_summary": "ผลตรวจปัสสาวะอยู่ในเกณฑ์ปกติทุกพารามิเตอร์",
                    "clinical_bullets": ["ไม่พบความผิดปกติ", "แนะนำตรวจติดตามเป็นประจำ"]
                }
            ]
        },
        {
            "name": "สมชาย ใจดี",
            "tests": [
                {
                    "urobilinogen": "0.1 Normal",
                    "glucose": "+250(14)",
                    "bilirubin": "neg.",
                    "ketones": "+15(1.5)",
                    "specific_gravity": 1.025,
                    "blood": "neg.",
                    "ph": 5.5,
                    "protein": "trace",
                    "nitrite": "neg.",
                    "leukocytes": "neg.",
                    "ascorbic_acid": "neg.",
                    "clinical_summary": "พบระดับน้ำตาลและคีโตนในปัสสาวะสูง อาจบ่งชี้ภาวะเบาหวาน",
                    "clinical_bullets": [
                        "พบ Glucose +250 mg/dL บ่งชี้ระดับน้ำตาลในเลือดสูง",
                        "พบ Ketones +15 mg/dL อาจเกิดจากการเผาผลาญไขมัน",
                        "แนะนำตรวจระดับน้ำตาลในเลือด (FBS) และพบแพทย์"
                    ]
                }
            ]
        },
        {
            "name": "สมหญิง สุขสันต์",
            "tests": [
                {
                    "urobilinogen": "0.1 Normal",
                    "glucose": "neg.",
                    "bilirubin": "neg.",
                    "ketones": "neg.",
                    "specific_gravity": 1.015,
                    "blood": "Hemolysis +10",
                    "ph": 7.0,
                    "protein": "++100(1.0)",
                    "nitrite": "pos.",
                    "leukocytes": "++75",
                    "ascorbic_acid": "neg.",
                    "clinical_summary": "พบเลือด โปรตีน และเม็ดเลือดขาวในปัสสาวะ บ่งชี้การติดเชื้อทางเดินปัสสาวะ",
                    "clinical_bullets": [
                        "พบ Blood (Hemolysis +10) และ Protein (++100) บ่งชี้การอักเสบหรือติดเชื้อ",
                        "พบ Nitrite positive และ Leukocytes ++75 สนับสนุนการติดเชื้อแบคทีเรีย",
                        "แนะนำส่งตรวจ Urine Culture และให้ยาปฏิชีวนะตามแพทย์สั่ง"
                    ]
                }
            ]
        }
    ]

    success_count = 0
    total_count = 0

    for patient in demo_patients:
        for i, test in enumerate(patient["tests"]):
            # Create timestamp (spread over last 7 days)
            date = datetime.now() - timedelta(days=i*2)
            date_str = date.strftime("%Y-%m-%d %H:%M:%S")

            total_count += 1
            result = db_handler.insert_record(
                date=date_str,
                urobilinogen=test["urobilinogen"],
                glucose=test["glucose"],
                bilirubin=test["bilirubin"],
                ketones=test["ketones"],
                specific_gravity=test["specific_gravity"],
                blood=test["blood"],
                ph=test["ph"],
                protein=test["protein"],
                nitrite=test["nitrite"],
                leukocytes=test["leukocytes"],
                ascorbic_acid=test["ascorbic_acid"],
                notes=patient["name"],
                clinical_summary=test["clinical_summary"],
                clinical_bullets=test["clinical_bullets"]
            )

            if result:
                success_count += 1
                print(f"✅ Inserted: {patient['name']} - {date_str}")
            else:
                print(f"❌ Failed: {patient['name']}")

    print(f"\n{'='*50}")
    print(f"✅ Successfully inserted {success_count}/{total_count} records")
    print(f"{'='*50}")

    if success_count > 0:
        print("\n🎉 Demo data inserted successfully!")
        print("📊 You can now view the data in the dashboard")
        print("\nNext steps:")
        print("1. Run: streamlit run Home.py")
        print("2. Navigate to Dashboard page")
        print("3. Select a patient to view their test results")
    else:
        print("\n⚠️ Failed to insert demo data")
        print("Please check your database connection and try again")

if __name__ == "__main__":
    print("=" * 50)
    print("  LHome Medical - Demo Data Insertion")
    print("=" * 50)
    print()

    # Check if DATABASE_URL is configured
    if not os.getenv("DATABASE_URL"):
        print("❌ ERROR: DATABASE_URL not found in .env file")
        print("Please configure your database connection first")
        exit(1)

    print("This script will insert demo patient data for testing.")
    print()

    try:
        insert_demo_data()
    except Exception as e:
        print(f"\n❌ Error: {e}")
        print("\nTroubleshooting:")
        print("1. Check DATABASE_URL in .env file")
        print("2. Verify database connection")
        print("3. Check network connectivity")
        print("4. Ensure RLS policies are configured correctly")
