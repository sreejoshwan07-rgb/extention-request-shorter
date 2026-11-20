"""
CIT AI-Native Engineering Programme · Semester 1 · Assessment 5
Evaluation Harness: 5 Test Requests Benchmark

Evaluates extraction accuracy and recommendation alignment against ground truth.
"""

from typing import List, Dict, Any
from sorter import load_courses, classify, is_valid, recommend

EVAL_CASES = [
    {
        "id": "EVAL_01",
        "request": "Please give me 2 more days for CS101 lab record. I had fever since Monday.",
        "expected_course": "CS101",
        "expected_days": 2,
        "expected_reason": "medical",
        "expected_recommendation": "within_policy",
        "description": "Standard medical request within 3-day limit"
    },
    {
        "id": "EVAL_02",
        "request": "My grandmother passed away and I travelled home. Need 5 days extension for MA102 assignment.",
        "expected_course": "MA102",
        "expected_days": 5,
        "expected_reason": "family",
        "expected_recommendation": "needs_faculty_review",
        "description": "Legitimate family bereavement exceeding 3 days"
    },
    {
        "id": "EVAL_03",
        "request": "Laptop crashed and blue-screened yesterday. Need 3 days for EE104 problem set.",
        "expected_course": "EE104",
        "expected_days": 3,
        "expected_reason": "technical",
        "expected_recommendation": "within_policy",
        "description": "Technical hardware failure exactly at 3-day threshold"
    },
    {
        "id": "EVAL_04",
        "request": "Need extension",
        "expected_course": None,
        "expected_days": None,
        "expected_reason": "other",
        "expected_recommendation": "needs_more_info",
        "description": "Completely empty request missing all critical parameters"
    },
    {
        "id": "EVAL_05",
        "request": "I have three midterms this week and another assignment. Requesting 2 days for CS101 assignment 3 due to heavy workload.",
        "expected_course": "CS101",
        "expected_days": 2,
        "expected_reason": "workload",
        "expected_recommendation": "needs_faculty_review",
        "description": "Workload reason with <=3 days (workload not allowed for automatic triage)"
    }
]


def run_eval_harness():
    courses = load_courses("courses.csv")
    print("\n========================================================")
    print("CIT EXTENSION REQUEST SORTER - EVALUATION HARNESS")
    print("========================================================")
    
    total = len(EVAL_CASES)
    reason_matches = 0
    recommendation_matches = 0
    all_correct = 0

    print(f"Running {total} standardized evaluation cases...\n")

    for case in EVAL_CASES:
        raw_text = case["request"]
        extracted = classify(raw_text, courses)
        validated = is_valid(extracted, raw_text, courses)
        rec = recommend(validated)

        reason_ok = (validated["reason"] == case["expected_reason"])
        rec_ok = (rec == case["expected_recommendation"])

        if reason_ok:
            reason_matches += 1
        if rec_ok:
            recommendation_matches += 1
        if reason_ok and rec_ok:
            all_correct += 1

        status_sym = "[PASS]" if (reason_ok and rec_ok) else "[FAIL]"
        print(f"{status_sym} Case: {case['id']} ({case['description']})")
        print(f"   Input: \"{raw_text}\"")
        print(f"   Reason: Got '{validated['reason']}', Expected '{case['expected_reason']}' -> {'OK' if reason_ok else 'MISMATCH'}")
        print(f"   Recommendation: Got '{rec}', Expected '{case['expected_recommendation']}' -> {'OK' if rec_ok else 'MISMATCH'}")
        print(f"   Validated: Course={validated['course']}, Days={validated['days']}, Summary=\"{validated['summary']}\"")
        print("-" * 56)

    print("\n--- EVALUATION BENCHMARK SUMMARY ---")
    print(f"Total Cases Tested          : {total}")
    print(f"Reason Accuracy             : {reason_matches}/{total} ({reason_matches/total*100:.1f}%)")
    print(f"Recommendation Accuracy     : {recommendation_matches}/{total} ({recommendation_matches/total*100:.1f}%)")
    print(f"Overall Full-Match Accuracy : {all_correct}/{total} ({all_correct/total*100:.1f}%)")
    print("========================================================\n")
    return all_correct == total


if __name__ == "__main__":
    success = run_eval_harness()
    if not success:
        exit(1)
