# -*- coding: utf-8 -*-
"""
Test advanced Thai text sanitization with A-Z support and backslash wrapper detection
"""
import sys
import io
import os

# Set UTF-8 encoding for Windows console
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.analysis import sanitize_thai_text, parse_clinical_bullets

print("=" * 70)
print("Testing Advanced Thai Text Sanitization (A-Z + Backslash Support)")
print("=" * 70)

# Test sanitize_thai_text with A-Z support
test_cases_sanitize = [
    ("น้ำgcตาล", "น้ำตาล"),
    ("ทำNงาน", "ทำงาน"),
    ("คำnแนะนำn:", "คำแนะนำ:"),
    ("สำnหรับ", "สำหรับ"),
    ("ปัสbสาวะfb", "ปัสสาวะ"),
    ("Glucose (GLU)", "Glucose (GLU)"),  # Should be preserved
    ("pH 7.0", "pH 7.0"),  # Should be preserved
]

print("\n📝 Test sanitize_thai_text (รองรับ A-Z):")
for input_text, expected in test_cases_sanitize:
    result = sanitize_thai_text(input_text)
    status = "✅" if result == expected else "❌"
    print(f"  {status} Input: {input_text:30} → Output: {result:25} (Expected: {expected})")

# Test parse_clinical_bullets with backslash wrapper
test_cases_bullets = [
    ('["ข้อ 1", "ข้อ 2"]', ["ข้อ 1", "ข้อ 2"]),
    ('\\\\พบเลือดในปัสสาวะ\\\\, \\\\ควรพบแพทย์\\\\', ["พบเลือดในปัสสาวะ", "ควรพบแพทย์"]),  # Backslash wrapper
    ('["ทำbงาน", "น้ำgc"]', ["ทำงาน", "น้ำ"]),  # With corruption + sanitization
    ('["ข้อที่ 1 มีขึ้นบรรทัดใหม่", "ข้อ 2"]', ["ข้อที่ 1 มีขึ้นบรรทัดใหม่", "ข้อ 2"]),  # Standard format
]

print("\n📋 Test parse_clinical_bullets (รองรับ backslash wrapper):")
for input_text, expected in test_cases_bullets:
    result = parse_clinical_bullets(input_text, sanitize=True)
    # Compare lists
    match = result == expected
    status = "✅" if match else "❌"
    print(f"  {status} Input: {repr(input_text)[:40]:40}")
    print(f"      Output: {result}")
    print(f"      Expected: {expected}")

print("\n" + "=" * 70)
print("✅ All advanced sanitization tests completed!")
print("=" * 70)
