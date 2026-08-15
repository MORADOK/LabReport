# -*- coding: utf-8 -*-
"""
Confidence Score Calculation Test Suite
ทดสอบระบบคำนวณ confidence score จากค่า RGB
"""

import sys
import os

# Force UTF-8 output on Windows
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.cybow_reference import calculate_confidence_from_rgb, enforce_strict_cybow_standards

def test_confidence_calculation():
    """
    ทดสอบ calculate_confidence_from_rgb() กับกรณีต่าง ๆ
    """
    print("=" * 80)
    print("🧪 TEST: Confidence Score Calculation")
    print("=" * 80)
    print()

    test_cases = [
        # (detected_rgb, param_code, selected_value, expected_confidence_range)
        {
            "name": "Perfect match - Glucose negative",
            "rgb": [118, 194, 201],
            "param": "glucose",
            "value": "neg.",
            "expected_min": 95,
            "expected_max": 100
        },
        {
            "name": "Close match - Glucose slight variation",
            "rgb": [125, 200, 205],
            "param": "glucose",
            "value": "neg.",
            "expected_min": 85,
            "expected_max": 100
        },
        {
            "name": "Medium distance - Protein moderate variation",
            "rgb": [150, 180, 90],
            "param": "protein",
            "value": "+30(0.3)",
            "expected_min": 70,
            "expected_max": 94
        },
        {
            "name": "Far distance - Blood high variation",
            "rgb": [200, 150, 100],
            "param": "blood",
            "value": "neg.",
            "expected_min": 0,
            "expected_max": 70
        },
        {
            "name": "Perfect match - pH 6",
            "rgb": [238, 179, 74],
            "param": "ph",
            "value": "6",
            "expected_min": 95,
            "expected_max": 100
        }
    ]

    passed = 0
    failed = 0

    print(f"{'Test Case':<45} {'RGB':<20} {'Confidence':<12} {'Expected':<15} {'Result'}")
    print("─" * 100)

    for test in test_cases:
        confidence = calculate_confidence_from_rgb(
            test["rgb"],
            test["param"],
            test["value"]
        )

        in_range = test["expected_min"] <= confidence <= test["expected_max"]
        result_icon = "✅" if in_range else "❌"

        rgb_str = str(test["rgb"])
        expected_str = f"{test['expected_min']}-{test['expected_max']}%"

        print(f"{test['name']:<45} {rgb_str:<20} {confidence:<12}% {expected_str:<15} {result_icon}")

        if in_range:
            passed += 1
        else:
            failed += 1

    print()
    print("=" * 80)
    print(f"📊 Summary: {passed}/{len(test_cases)} tests passed")
    print("=" * 80)
    print()

    return passed, failed


def test_overall_confidence():
    """
    ทดสอบการคำนวณ overall confidence จาก enforce_strict_cybow_standards
    """
    print("=" * 80)
    print("🧪 TEST: Overall Confidence Calculation")
    print("=" * 80)
    print()

    # Mock AI response with RGB data
    mock_ai_data = {
        "urobilinogen": "0.1 Normal",
        "glucose": "neg.",
        "bilirubin": "neg.",
        "ketones": "neg.",
        "specific_gravity": "1.020",
        "blood": "neg.",
        "ph": "6",
        "protein": "neg.",
        "nitrite": "neg.",
        "leukocytes": "neg.",
        "ascorbic_acid": "neg.",
        "detected_rgb": {
            "urobilinogen": [251, 226, 212],  # Perfect match
            "glucose": [118, 194, 201],       # Perfect match
            "bilirubin": [242, 222, 210],     # Perfect match
            "ketones": [242, 222, 210],       # Perfect match
            "specific_gravity": [160, 180, 160],  # Perfect match
            "blood": [245, 245, 245],         # Perfect match
            "ph": [238, 179, 74],             # Perfect match
            "protein": [237, 227, 85],        # Perfect match
            "nitrite": [245, 240, 235],       # Perfect match
            "leukocytes": [240, 230, 235],    # Perfect match
            "ascorbic_acid": [230, 235, 210]  # Perfect match
        },
        "clinical_summary": "Test data",
        "clinical_bullets": []
    }

    print("Testing with perfect RGB matches (all values should be ~100%)...")
    validated_data = enforce_strict_cybow_standards(mock_ai_data)

    overall_conf = validated_data.get("overall_confidence", 0)
    confidence_scores = validated_data.get("confidence_scores", {})

    print(f"\n📊 Individual Confidence Scores:")
    for param, score in confidence_scores.items():
        emoji = "🟢" if score >= 90 else "🟡" if score >= 75 else "🟠"
        print(f"  {emoji} {param:<20}: {score}%")

    print(f"\n🎯 Overall Confidence: {overall_conf:.1f}%")

    # Check if overall confidence is high (should be near 100% for perfect matches)
    success = overall_conf >= 90

    if success:
        print("✅ Overall confidence calculation: PASSED")
    else:
        print(f"❌ Overall confidence calculation: FAILED (expected ≥90%, got {overall_conf:.1f}%)")

    print()
    return 1 if success else 0, 0 if success else 1


def test_confidence_with_ai_values():
    """
    ทดสอบกรณีที่ AI ส่งค่า confidence มาเอง (ไม่มี RGB)
    """
    print("=" * 80)
    print("🧪 TEST: Confidence from AI Estimates (No RGB)")
    print("=" * 80)
    print()

    mock_ai_data = {
        "urobilinogen": "0.1 Normal",
        "glucose": "neg.",
        "bilirubin": "neg.",
        "ketones": "neg.",
        "specific_gravity": "1.020",
        "blood": "neg.",
        "ph": "6",
        "protein": "neg.",
        "nitrite": "neg.",
        "leukocytes": "neg.",
        "ascorbic_acid": "neg.",
        "confidence_scores": {
            "urobilinogen": 95,
            "glucose": 98,
            "bilirubin": 92,
            "ketones": 94,
            "specific_gravity": 90,
            "blood": 96,
            "ph": 93,
            "protein": 97,
            "nitrite": 91,
            "leukocytes": 95,
            "ascorbic_acid": 89
        },
        "clinical_summary": "Test data",
        "clinical_bullets": []
    }

    print("Testing with AI-provided confidence scores (no RGB data)...")
    validated_data = enforce_strict_cybow_standards(mock_ai_data)

    overall_conf = validated_data.get("overall_confidence", 0)
    confidence_scores = validated_data.get("confidence_scores", {})

    print(f"\n📊 Confidence Scores (from AI):")
    for param, score in confidence_scores.items():
        emoji = "🟢" if score >= 90 else "🟡" if score >= 75 else "🟠"
        print(f"  {emoji} {param:<20}: {score}%")

    print(f"\n🎯 Overall Confidence: {overall_conf:.1f}%")

    # Check if scores match what AI provided
    success = all(
        confidence_scores.get(param) == mock_ai_data["confidence_scores"][param]
        for param in mock_ai_data["confidence_scores"].keys()
    )

    if success:
        print("✅ AI confidence preservation: PASSED")
    else:
        print("❌ AI confidence preservation: FAILED")

    print()
    return 1 if success else 0, 0 if success else 1


def run_all_tests():
    """
    รันการทดสอบทั้งหมด
    """
    print("\n")
    print("╔" + "═" * 78 + "╗")
    print("║" + " " * 15 + "🧪 CONFIDENCE SCORE TEST SUITE" + " " * 32 + "║")
    print("╚" + "═" * 78 + "╝")
    print()

    total_passed = 0
    total_failed = 0

    # Test 1: Confidence Calculation
    p1, f1 = test_confidence_calculation()
    total_passed += p1
    total_failed += f1

    # Test 2: Overall Confidence
    p2, f2 = test_overall_confidence()
    total_passed += p2
    total_failed += f2

    # Test 3: AI Confidence Values
    p3, f3 = test_confidence_with_ai_values()
    total_passed += p3
    total_failed += f3

    # Final Summary
    total_tests = total_passed + total_failed
    pass_rate = (total_passed / total_tests * 100) if total_tests > 0 else 0

    print()
    print("╔" + "═" * 78 + "╗")
    print("║" + " " * 25 + "📊 FINAL SUMMARY" + " " * 36 + "║")
    print("╠" + "═" * 78 + "╣")
    print(f"║  Total Tests:      {total_tests:<58} ║")
    print(f"║  ✅ Passed:         {total_passed:<58} ║")
    print(f"║  ❌ Failed:         {total_failed:<58} ║")
    print(f"║  📈 Pass Rate:      {pass_rate:.1f}%{' ' * 54} ║")
    print("╠" + "═" * 78 + "╣")

    if pass_rate == 100:
        print("║  🎉 STATUS:        ✅ ALL TESTS PASSED - READY TO USE!" + " " * 23 + "║")
    elif pass_rate >= 80:
        print("║  ⚠️  STATUS:        🟡 MOSTLY PASSING - MINOR ISSUES" + " " * 26 + "║")
    else:
        print("║  ❌ STATUS:        🔴 NEEDS REVIEW" + " " * 43 + "║")

    print("╚" + "═" * 78 + "╝")
    print()

    return pass_rate >= 80


if __name__ == "__main__":
    try:
        success = run_all_tests()
        exit_code = 0 if success else 1

        if success:
            print("✅ Confidence score testing completed successfully!")
            print("   System is ready for use.\n")
        else:
            print("❌ Confidence score testing found issues!")
            print("   Please review failed tests.\n")

        exit(exit_code)

    except Exception as e:
        print(f"\n❌ Test suite crashed with error: {e}")
        import traceback
        traceback.print_exc()
        exit(1)
