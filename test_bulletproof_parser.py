# -*- coding: utf-8 -*-
"""
Test bullet-proof parser with 4-tier fallback system
"""
import sys
import os
import io

# Set UTF-8 encoding for Windows console
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.analysis import parse_clinical_bullets
import json

# Test cases covering all scenarios
test_cases = [
    ("Valid JSON", '["ข้อ 1", "ข้อ 2", "ข้อ 3"]'),
    ("Python list repr", "['Item 1', 'Item 2']"),
    ("Malformed JSON with newlines", '["ข้อที่ 1\nมีขึ้นบรรทัดใหม่", "ข้อ 2"]'),
    ("Corrupted Thai + newlines", '["ทำbงานของไต\nปกติ", "ความbถ่วงสูง"]'),
    ("Malformed but has quotes", '["ข้อ 1", "ข้อ 2", broken json'),
    ("Just quoted text", '"ข้อความเดียว ไม่มี brackets"'),
    ("Multiple quotes no brackets", '"ข้อ 1" "ข้อ 2" "ข้อ 3"'),
    ("Broken structure", '[ข้อ 1 ข้อ 2]'),
    ("Already a list", ["Already", "a", "list"]),
    ("Empty string", ""),
    ("Empty list", "[]"),
]

print("=" * 70)
print("Testing Bullet-Proof Parser (4-Tier Fallback System)")
print("=" * 70)

for i, (desc, test_input) in enumerate(test_cases, 1):
    print(f"\n{i}. {desc}")
    print(f"   Input: {repr(test_input)[:60]}...")
    try:
        result = parse_clinical_bullets(test_input, sanitize=True)
        print(f"   ✅ Result ({len(result)} items):")
        for j, item in enumerate(result, 1):
            print(f"      {j}. {item[:50]}..." if len(item) > 50 else f"      {j}. {item}")
    except Exception as e:
        print(f"   ❌ Error: {e}")

# Test with real database-like scenarios
print("\n" + "=" * 70)
print("Real-world scenarios:")
print("=" * 70)

real_scenarios = [
    ("Newline in middle of text", '["พบเม็ดเลือดขาว\nและไนไตรต์", "ควรพบแพทย์"]'),
    ("Unicode escape + corruption", r'["\u0e17\u0e33bงาน", "\u0e19\u0e49\u0e33fb"]'),
    ("Mixed valid and broken", '["ข้อ 1", null, "ข้อ 2", undefined]'),
]

for i, (desc, test_input) in enumerate(real_scenarios, 1):
    print(f"\n{i}. {desc}")
    result = parse_clinical_bullets(test_input, sanitize=True)
    print(f"   Result: {result}")

print("\n" + "=" * 70)
print("✅ All tests completed!")
print("=" * 70)
