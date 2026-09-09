"""AI-assisted summary for staff-entered CYBOW 11M results.

The staff-selected 11 values are authoritative. AI may summarize them but must
never alter, infer, or replace any selected result.
"""
import json
import os
import re

from openai import OpenAI

DISPLAY_NAMES = {
    "urobilinogen": "Urobilinogen",
    "glucose": "Glucose",
    "bilirubin": "Bilirubin",
    "ketones": "Ketones",
    "specific_gravity": "Specific Gravity",
    "blood": "Blood",
    "ph": "pH",
    "protein": "Protein",
    "nitrite": "Nitrite",
    "leukocytes": "Leukocytes",
    "ascorbic_acid": "Ascorbic acid",
}


def deterministic_summary(results):
    """Safe fallback that preserves exactly what staff selected."""
    parts = [f"{DISPLAY_NAMES.get(k, k)}: {v}" for k, v in results.items()]
    return {
        "summary": "; ".join(parts),
        "bullets": [
            "ผลทั้ง 11 ค่าเป็นค่าที่พนักงานอ่านและเลือกจากแถบ CYBOW 11M",
            "ควรพิจารณาร่วมกับอาการ ประวัติ และการตรวจยืนยันตามดุลยพินิจของบุคลากรทางการแพทย์",
        ],
        "ai_used": False,
        "model": None,
    }


def _extract_json(text):
    match = re.search(r"\{.*\}", text or "", re.DOTALL)
    if not match:
        raise ValueError("AI summary did not return JSON")
    value = json.loads(match.group())
    if not isinstance(value, dict):
        raise ValueError("AI summary payload must be an object")
    return value


def summarize_manual_results(results, client=None, model=None):
    """Create a concise Thai clinical-oriented summary without changing results.

    Returns a fallback summary when the AI service is unavailable or malformed.
    """
    fallback = deterministic_summary(results)
    api_key = os.getenv("OPENROUTER_API_KEY")
    if client is None:
        if not api_key:
            fallback["error"] = "OPENROUTER_API_KEY unavailable"
            return fallback
        client = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=api_key)
    model = model or os.getenv("TEXT_MODEL") or os.getenv("VISION_MODEL", "anthropic/claude-4.5-sonnet")

    prompt = (
        "คุณเป็นผู้ช่วยสรุปผล urinalysis CYBOW 11M สำหรับบุคลากรทางการแพทย์ "
        "ข้อมูลต่อไปนี้ถูกอ่านและเลือกโดยพนักงานแล้ว จึงเป็นค่าต้นทางที่ห้ามแก้ไข ห้ามเดาค่าใหม่ "
        "และห้ามวินิจฉัยโรคจากผลนี้เพียงอย่างเดียว สรุปเป็นภาษาไทยแบบกระชับ โดยชี้ว่าค่าใดควรได้รับความสนใจ "
        "และแนะนำให้พิจารณาร่วมกับอาการ/ประวัติ/การตรวจยืนยันเมื่อเหมาะสม "
        "ตอบ JSON เท่านั้นรูปแบบ {\"summary\":\"...\",\"bullets\":[\"...\"]}.\n\n"
        "ผลที่พนักงานเลือก:\n" + json.dumps(results, ensure_ascii=False)
    )
    try:
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": "Do not modify the supplied laboratory values. Do not diagnose. Return valid JSON only."},
                {"role": "user", "content": prompt},
            ],
            temperature=0,
            max_tokens=700,
        )
        payload = _extract_json(response.choices[0].message.content)
        summary = str(payload.get("summary", "")).strip()
        bullets = payload.get("bullets", [])
        if not summary or not isinstance(bullets, list):
            raise ValueError("AI summary JSON missing fields")
        bullets = [str(x).strip() for x in bullets if str(x).strip()][:6]
        if not bullets:
            raise ValueError("AI summary bullets empty")
        return {"summary": summary, "bullets": bullets, "ai_used": True, "model": model}
    except Exception as exc:
        fallback["error"] = str(exc)
        return fallback
