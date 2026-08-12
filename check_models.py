import requests
import pandas as pd
import sys
import io

# Fix encoding for Windows console
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

def fetch_openrouter_models():
    url = "https://openrouter.ai/api/v1/models"

    print("🔄 กำลังดึงข้อมูลโมเดลจาก OpenRouter...")
    response = requests.get(url)
    
    if response.status_code == 200:
        data = response.json()
        models_list = []
        
        # วนลูปดึงข้อมูลที่สำคัญของแต่ละโมเดล
        for model in data.get('data', []):
            prompt_price = float(model['pricing']['prompt'])
            completion_price = float(model['pricing']['completion'])
            
            models_list.append({
                "Model ID": model['id'],
                "Name": model['name'],
                "Context Length": model['context_length'],
                "Prompt Price ($/token)": prompt_price,
                "Completion Price ($/token)": completion_price,
                "Is Free": prompt_price == 0.0 and completion_price == 0.0
            })
            
        return pd.DataFrame(models_list)
    else:
        print(f"❌ Error: {response.status_code}")
        return None

# ==========================================
# 📊 การวิเคราะห์และแสดงผลข้อมูล
# ==========================================
if __name__ == "__main__":
    df_models = fetch_openrouter_models()
    
    if df_models is not None:
        total_models = len(df_models)
        free_models = df_models[df_models["Is Free"] == True]
        paid_models = df_models[df_models["Is Free"] == False]
        
        print("\n" + "="*50)
        print(f"📊 สรุปข้อมูลโมเดลบน OpenRouter")
        print("="*50)
        print(f"🤖 จำนวนโมเดลทั้งหมด: {total_models} รุ่น")
        print(f"🆓 โมเดลที่ใช้งานได้ฟรี 100%: {len(free_models)} รุ่น")
        print(f"💰 โมเดลที่ต้องใช้เครดิต: {len(paid_models)} รุ่น")
        
        print("\n" + "="*50)
        print("🆓 ตัวอย่างโมเดลฟรี (Free Models):")
        print("="*50)
        # แสดง 5 อันดับแรกของโมเดลฟรี
        print(free_models[["Model ID", "Name", "Context Length"]].head(5).to_string(index=False))
        
        print("\n" + "="*50)
        print("🏆 ตัวอย่างโมเดลพรีเมียม (Paid Models):")
        print("="*50)
        # แสดง 5 อันดับแรกของโมเดลเสียเงิน เรียงตาม Context Length
        print(paid_models.sort_values(by="Context Length", ascending=False)[["Model ID", "Name", "Context Length"]].head(5).to_string(index=False))