# -*- coding: utf-8 -*-
"""
Bot Accuracy Test Suite - CYBOW 11M Urinalysis System
ทดสอบความแม่นยำของระบบบอทอย่างละเอียดก่อนใช้งาน

Test Categories:
1. Strict Validator Function Testing
2. Value Normalization Testing
3. Edge Cases & Error Handling
4. CYBOW Reference Integration
5. Visual Anchoring Compliance
"""

import sys
import os
from datetime import datetime

# Force UTF-8 output on Windows
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.cybow_reference import (
    CYBOW_11M_EXACT_REFERENCE,
    get_severity_level,
    enforce_strict_cybow_standards
)

# =================================================================
# 🎯 Test 1: Strict Validator Function Testing
# =================================================================

def test_strict_validator():
    """
    ทดสอบ enforce_strict_cybow_standards() กับกรณีต่าง ๆ
    """
    print("=" * 70)
    print("🎯 TEST 1: Strict Validator Function Testing")
    print("=" * 70)

    test_cases = [
        {
            "name": "Test Case 1: AI ตอบค่าถูกต้องแล้ว (Perfect Match)",
            "input": {
                "urobilinogen": "0.1 Normal",
                "glucose": "neg.",
                "protein": "++100(1.0)",
                "blood": "Hemolysis +++250"
            },
            "expected": {
                "urobilinogen": "0.1 Normal",
                "glucose": "neg.",
                "protein": "++100(1.0)",
                "blood": "Hemolysis +++250"
            }
        },
        {
            "name": "Test Case 2: AI ตอบแบบตัดทอน (Truncated Values)",
            "input": {
                "glucose": "neg",
                "protein": "++100",
                "blood": "+++250",
                "ketones": "±5"
            },
            "expected": {
                "glucose": "neg.",
                "protein": "++100(1.0)",
                "blood": "Hemolysis +++250",  # Should match first occurrence with +++250
                "ketones": "±5(0.5)"
            }
        },
        {
            "name": "Test Case 3: AI ตอบแบบ Negative Variations",
            "input": {
                "glucose": "negative",
                "bilirubin": "0",
                "nitrite": "neg",
                "ascorbic_acid": "neg."
            },
            "expected": {
                "glucose": "neg.",
                "bilirubin": "neg.",
                "nitrite": "neg.",
                "ascorbic_acid": "neg."
            }
        },
        {
            "name": "Test Case 4: AI ตอบแบบมีหน่วย (With Units - Should Normalize)",
            "input": {
                "protein": "100 mg/dL",
                "glucose": "100",
                "specific_gravity": "1.020",
                "ph": "6"
            },
            "expected": {
                "protein": "++100(1.0)",
                "glucose": "±100(5.5)",
                "specific_gravity": "1.020",
                "ph": "6"
            }
        },
        {
            "name": "Test Case 5: Edge Cases - Malformed Input",
            "input": {
                "glucose": "+++",
                "protein": "trace value",
                "blood": "positive",
                "leukocytes": "500"
            },
            "expected": {
                "glucose": "neg.",  # Fallback to first value
                "protein": "trace",  # Should match 'trace'
                "blood": "neg.",  # No number match, fallback
                "leukocytes": "+++500"  # Should match number 500
            }
        }
    ]

    passed = 0
    failed = 0

    for idx, test in enumerate(test_cases, 1):
        print(f"\n{'─' * 70}")
        print(f"📝 {test['name']}")
        print(f"{'─' * 70}")

        # Run validator
        result = enforce_strict_cybow_standards(test['input'])

        # Check each parameter
        test_passed = True
        for param, expected_val in test['expected'].items():
            actual_val = result.get(param)
            match = actual_val == expected_val

            status = "✅" if match else "❌"
            print(f"  {status} {param:20s}: '{actual_val:20s}' (expected: '{expected_val}')")

            if not match:
                test_passed = False

        if test_passed:
            print(f"  ✅ Test Case {idx}: PASSED")
            passed += 1
        else:
            print(f"  ❌ Test Case {idx}: FAILED")
            failed += 1

    print(f"\n{'=' * 70}")
    print(f"📊 Strict Validator Test Summary: {passed}/{len(test_cases)} passed")
    print(f"{'=' * 70}\n")

    return passed, failed


# =================================================================
# 🎯 Test 2: Get Severity Level Testing
# =================================================================

def test_severity_levels():
    """
    ทดสอบ get_severity_level() กับค่าต่าง ๆ
    """
    print("=" * 70)
    print("🎯 TEST 2: Get Severity Level Testing")
    print("=" * 70)

    test_cases = [
        # (param_code, value, expected_severity, expected_status)
        ("GLU", "neg.", "normal", "Normal"),
        ("GLU", "±100(5.5)", "warning", "Positive"),
        ("GLU", "+++1000(55)", "critical", "Positive (High)"),

        ("PRO", "neg.", "normal", "Normal"),
        ("PRO", "trace", "warning", "Positive"),
        ("PRO", "++100(1.0)", "critical", "Positive (High)"),

        ("BLO", "neg.", "normal", "Normal"),
        ("BLO", "Hemolysis +10", "warning", "Positive"),
        ("BLO", "Hemolysis +++250", "critical", "Positive (High)"),

        ("NIT", "neg.", "normal", "Normal"),
        ("NIT", "pos.", "high", "Positive"),

        ("LEU", "neg.", "normal", "Normal"),
        ("LEU", "+25", "warning", "Positive"),
        ("LEU", "+++500", "critical", "Positive (High)"),

        ("ASC", "neg.", "normal", "Normal"),
        ("ASC", "+20(1.2)", "high", "Positive"),

        ("pH", "6", "normal", "Normal"),
        ("pH", "10", "warning", "Abnormal"),

        ("SG", "1.020", "normal", "Normal"),
        ("SG", "1.040", "warning", "Abnormal"),
    ]

    passed = 0
    failed = 0

    print(f"\n{'Param':<6} {'Value':<20} {'Severity':<10} {'Status':<20} {'Result':<6}")
    print("─" * 70)

    for param_code, value, expected_severity, expected_status in test_cases:
        severity, color, status = get_severity_level(param_code, value)

        severity_match = severity == expected_severity
        status_match = status == expected_status
        test_passed = severity_match and status_match

        result_icon = "✅" if test_passed else "❌"

        print(f"{param_code:<6} {value:<20} {severity:<10} {status:<20} {result_icon}")

        if test_passed:
            passed += 1
        else:
            failed += 1
            print(f"  ❌ Expected: severity={expected_severity}, status={expected_status}")

    print(f"\n{'=' * 70}")
    print(f"📊 Severity Level Test Summary: {passed}/{len(test_cases)} passed")
    print(f"{'=' * 70}\n")

    return passed, failed


# =================================================================
# 🎯 Test 3: CYBOW Reference Completeness
# =================================================================

def test_reference_completeness():
    """
    ทดสอบความครบถ้วนของ CYBOW_11M_EXACT_REFERENCE
    """
    print("=" * 70)
    print("🎯 TEST 3: CYBOW Reference Completeness Testing")
    print("=" * 70)

    required_params = [
        "URO", "GLU", "BIL", "KET", "SG", "BLO",
        "pH", "PRO", "NIT", "LEU", "ASC"
    ]

    passed = 0
    failed = 0

    print(f"\n{'Parameter':<6} {'Has Normal':<12} {'Has High/Warning':<18} {'Has Color Info':<16} {'Result'}")
    print("─" * 70)

    for param in required_params:
        if param not in CYBOW_11M_EXACT_REFERENCE:
            print(f"{param:<6} {'❌':<12} {'❌':<18} {'❌':<16} ❌ MISSING")
            failed += 1
            continue

        ref = CYBOW_11M_EXACT_REFERENCE[param]

        # Check for required fields
        has_normal = "normal" in ref or "min_normal" in ref
        has_abnormal = "high" in ref or "warning" in ref or "critical" in ref
        has_color = "color_normal" in ref or "color" in ref

        all_present = has_normal and (has_abnormal or param in ["SG", "pH"]) and has_color

        normal_icon = "✅" if has_normal else "❌"
        abnormal_icon = "✅" if (has_abnormal or param in ["SG", "pH"]) else "❌"
        color_icon = "✅" if has_color else "❌"
        result_icon = "✅" if all_present else "❌"

        print(f"{param:<6} {normal_icon:<12} {abnormal_icon:<18} {color_icon:<16} {result_icon}")

        if all_present:
            passed += 1
        else:
            failed += 1

    print(f"\n{'=' * 70}")
    print(f"📊 Reference Completeness Summary: {passed}/{len(required_params)} complete")
    print(f"{'=' * 70}\n")

    return passed, failed


# =================================================================
# 🎯 Test 4: Visual Anchoring Compliance
# =================================================================

def test_visual_anchoring_compliance():
    """
    ทดสอบว่า ASC (strip 11) มีสีพื้นฐานถูกต้องตามที่กำหนด
    """
    print("=" * 70)
    print("🎯 TEST 4: Visual Anchoring Compliance Testing")
    print("=" * 70)

    critical_checks = [
        {
            "param": "ASC",
            "field": "color_normal",
            "expected_keywords": ["น้ำเงิน", "ฟ้า", "blue", "teal"],
            "description": "ASC strip 11 baseline color (Dark Blue/Teal)"
        },
        {
            "param": "BLO",
            "field": "color_normal",
            "expected_keywords": ["เหลือง", "yellow"],
            "description": "BLO strip 6 baseline color (Yellow)"
        },
        {
            "param": "ASC",
            "field": "color_high",
            "expected_keywords": ["ส้ม", "orange"],
            "description": "ASC abnormal color (Orange)"
        }
    ]

    passed = 0
    failed = 0

    print(f"\n{'Parameter':<10} {'Field':<15} {'Check':<50} {'Result'}")
    print("─" * 90)

    for check in critical_checks:
        param = check["param"]
        field = check["field"]
        expected_keywords = check["expected_keywords"]
        description = check["description"]

        if param not in CYBOW_11M_EXACT_REFERENCE:
            print(f"{param:<10} {field:<15} {description:<50} ❌")
            failed += 1
            continue

        ref = CYBOW_11M_EXACT_REFERENCE[param]

        if field not in ref:
            print(f"{param:<10} {field:<15} {description:<50} ❌")
            failed += 1
            continue

        color_value = ref[field].lower()
        has_keyword = any(keyword.lower() in color_value for keyword in expected_keywords)

        result_icon = "✅" if has_keyword else "❌"
        print(f"{param:<10} {field:<15} {description:<50} {result_icon}")

        if not has_keyword:
            print(f"  ❌ Found: '{ref[field]}' (expected one of: {expected_keywords})")
            failed += 1
        else:
            passed += 1

    print(f"\n{'=' * 70}")
    print(f"📊 Visual Anchoring Compliance: {passed}/{len(critical_checks)} checks passed")
    print(f"{'=' * 70}\n")

    return passed, failed


# =================================================================
# 🎯 Test 5: Fuzzy Matching Logic
# =================================================================

def test_fuzzy_matching():
    """
    ทดสอบความสามารถในการจับคู่ค่าแบบ fuzzy
    """
    print("=" * 70)
    print("🎯 TEST 5: Fuzzy Matching Logic Testing")
    print("=" * 70)

    test_cases = [
        # (input_value, param, should_normalize_to)
        ("negative", "glucose", "neg."),
        ("0", "bilirubin", "neg."),
        ("NORMAL", "nitrite", "neg."),
        ("pos", "nitrite", "pos."),
        ("positive", "nitrite", "pos."),
        ("Trace", "protein", "trace"),
        ("TRACE", "protein", "trace"),
        ("25", "leukocytes", "+25"),
        ("75", "leukocytes", "++75"),
        ("500", "leukocytes", "+++500"),
        ("100", "glucose", "±100(5.5)"),
        ("250", "glucose", "+250(14)"),
        ("1000", "glucose", "+++1000(55)"),
        ("10", "blood", "Hemolysis +10"),
        ("50", "blood", "Hemolysis ++50"),
        ("250", "blood", "Hemolysis +++250"),
    ]

    passed = 0
    failed = 0

    print(f"\n{'Input Value':<15} {'Parameter':<15} {'Expected Output':<25} {'Actual Output':<25} {'Result'}")
    print("─" * 100)

    for input_val, param, expected_output in test_cases:
        # Create mock AI data
        mock_data = {param: input_val}
        validated = enforce_strict_cybow_standards(mock_data)
        actual_output = validated.get(param, "N/A")

        match = actual_output == expected_output
        result_icon = "✅" if match else "❌"

        print(f"{input_val:<15} {param:<15} {expected_output:<25} {actual_output:<25} {result_icon}")

        if match:
            passed += 1
        else:
            failed += 1

    print(f"\n{'=' * 70}")
    print(f"📊 Fuzzy Matching Summary: {passed}/{len(test_cases)} matched correctly")
    print(f"{'=' * 70}\n")

    return passed, failed


# =================================================================
# 🚀 Main Test Runner
# =================================================================

def run_all_tests():
    """
    รันการทดสอบทั้งหมดและสรุปผล
    """
    print("\n")
    print("╔" + "═" * 68 + "╗")
    print("║" + " " * 10 + "🧪 BOT ACCURACY TEST SUITE - CYBOW 11M SYSTEM" + " " * 11 + "║")
    print("║" + " " * 20 + f"Test Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}" + " " * 18 + "║")
    print("╚" + "═" * 68 + "╝")
    print()

    total_passed = 0
    total_failed = 0

    # Test 1: Strict Validator
    p1, f1 = test_strict_validator()
    total_passed += p1
    total_failed += f1

    # Test 2: Severity Levels
    p2, f2 = test_severity_levels()
    total_passed += p2
    total_failed += f2

    # Test 3: Reference Completeness
    p3, f3 = test_reference_completeness()
    total_passed += p3
    total_failed += f3

    # Test 4: Visual Anchoring
    p4, f4 = test_visual_anchoring_compliance()
    total_passed += p4
    total_failed += f4

    # Test 5: Fuzzy Matching
    p5, f5 = test_fuzzy_matching()
    total_passed += p5
    total_failed += f5

    # Final Summary
    total_tests = total_passed + total_failed
    pass_rate = (total_passed / total_tests * 100) if total_tests > 0 else 0

    print("\n")
    print("╔" + "═" * 68 + "╗")
    print("║" + " " * 20 + "📊 FINAL TEST SUMMARY" + " " * 26 + "║")
    print("╠" + "═" * 68 + "╣")
    print(f"║  Total Tests Run:     {total_tests:<47} ║")
    print(f"║  ✅ Passed:            {total_passed:<47} ║")
    print(f"║  ❌ Failed:            {total_failed:<47} ║")
    print(f"║  📈 Pass Rate:         {pass_rate:.1f}%{' ' * 43} ║")
    print("╠" + "═" * 68 + "╣")

    if pass_rate == 100:
        print("║  🎉 STATUS:           ✅ ALL TESTS PASSED - SYSTEM READY!        ║")
    elif pass_rate >= 90:
        print("║  ⚠️  STATUS:           🟡 MOSTLY PASSING - MINOR FIXES NEEDED    ║")
    elif pass_rate >= 70:
        print("║  ⚠️  STATUS:           🟠 SOME ISSUES - REVIEW REQUIRED          ║")
    else:
        print("║  ❌ STATUS:           🔴 CRITICAL ISSUES - NOT READY FOR USE    ║")

    print("╚" + "═" * 68 + "╝")
    print()

    # Test Category Breakdown
    print("📋 Test Category Breakdown:")
    print(f"  1. Strict Validator:        {p1}/{p1+f1} passed")
    print(f"  2. Severity Levels:         {p2}/{p2+f2} passed")
    print(f"  3. Reference Completeness:  {p3}/{p3+f3} passed")
    print(f"  4. Visual Anchoring:        {p4}/{p4+f4} passed")
    print(f"  5. Fuzzy Matching:          {p5}/{p5+f5} passed")
    print()

    return pass_rate >= 90  # Return True if ready for production


if __name__ == "__main__":
    try:
        success = run_all_tests()
        exit_code = 0 if success else 1

        if success:
            print("✅ Bot accuracy testing completed successfully!")
            print("   System is ready for production use.\n")
        else:
            print("❌ Bot accuracy testing found issues!")
            print("   Please review failed tests before deployment.\n")

        exit(exit_code)

    except Exception as e:
        print(f"\n❌ Test suite crashed with error: {e}")
        import traceback
        traceback.print_exc()
        exit(1)
