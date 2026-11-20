"""
Unit tests for CIT Extension Request Sorter.
Tests all six core functions and policy invariants.
"""

import os
import pytest
from sorter import (
    load_courses,
    load_requests,
    classify,
    is_valid,
    recommend,
    write_reports,
    MAX_DAYS_WITHIN_POLICY,
    RECOMMENDATION_WITHIN_POLICY,
    RECOMMENDATION_NEEDS_FACULTY_REVIEW,
    RECOMMENDATION_NEEDS_MORE_INFO
)


@pytest.fixture
def sample_courses():
    return {
        "CS101": "Programming in Python",
        "MA102": "Engineering Mathematics",
        "PH103": "Engineering Physics",
        "EE104": "Basic Electrical Engineering"
    }


def test_load_courses():
    courses = load_courses("courses.csv")
    assert isinstance(courses, dict)
    assert "CS101" in courses
    assert len(courses) >= 3


def test_load_requests():
    reqs = load_requests("requests.csv")
    assert isinstance(reqs, list)
    assert len(reqs) >= 20
    assert "id" in reqs[0]
    assert "request" in reqs[0]


def test_is_valid_course_catalog_check(sample_courses):
    # Valid course present in catalog & request
    raw_text = "Need 2 days for CS101 assignment."
    extracted = {"course": "CS101", "days": 2, "reason": "medical", "summary": "Requests 2 days"}
    validated = is_valid(extracted, raw_text, sample_courses)
    assert validated["course"] == "CS101"

    # Course NOT in catalog
    raw_text_invalid = "Need 2 days for BIO999 assignment."
    extracted_invalid = {"course": "BIO999", "days": 2, "reason": "medical", "summary": "Requests 2 days"}
    validated_invalid = is_valid(extracted_invalid, raw_text_invalid, sample_courses)
    assert validated_invalid["course"] is None

    # Course in catalog but NOT in student request text (LLM hallucination)
    raw_text_hallucinated = "Need 2 days for my lab report."
    extracted_hallucinated = {"course": "CS101", "days": 2, "reason": "medical", "summary": "Requests 2 days"}
    validated_hallucinated = is_valid(extracted_hallucinated, raw_text_hallucinated, sample_courses)
    assert validated_hallucinated["course"] is None


def test_is_valid_days_fact_check(sample_courses):
    # Days present as digits
    raw_text_digit = "Give me 3 days for MA102."
    extracted = {"course": "MA102", "days": 3, "reason": "medical", "summary": "Requests 3 days"}
    validated = is_valid(extracted, raw_text_digit, sample_courses)
    assert validated["days"] == 3

    # Days present as words
    raw_text_word = "Give me three days for MA102."
    extracted_word = {"course": "MA102", "days": 3, "reason": "medical", "summary": "Requests 3 days"}
    validated_word = is_valid(extracted_word, raw_text_word, sample_courses)
    assert validated_word["days"] == 3

    # Days not written (student said "on Monday")
    raw_text_date = "Can I submit MA102 on Monday?"
    extracted_date = {"course": "MA102", "days": 2, "reason": "medical", "summary": "Requests 2 days"}
    validated_date = is_valid(extracted_date, raw_text_date, sample_courses)
    assert validated_date["days"] is None


def test_is_valid_privacy_scrubbing(sample_courses):
    raw_text = "I have acute fever and severe migraine for CS101."
    extracted = {
        "course": "CS101",
        "days": 2,
        "reason": "medical",
        "summary": "Requests 2 days for CS101, had acute fever and severe migraine"
    }
    validated = is_valid(extracted, raw_text, sample_courses)
    # Summary must be scrubbed of illness terms
    assert "fever" not in validated["summary"].lower()
    assert "migraine" not in validated["summary"].lower()
    assert len(validated["summary"].split()) <= 15


def test_recommend_policy_rules():
    # Rule 1: Missing course or days -> needs_more_info
    assert recommend({"course": None, "days": 2, "reason": "medical"}) == RECOMMENDATION_NEEDS_MORE_INFO
    assert recommend({"course": "CS101", "days": None, "reason": "medical"}) == RECOMMENDATION_NEEDS_MORE_INFO

    # Rule 2: <= 3 days and allowed reason (medical, family, technical) -> within_policy
    assert recommend({"course": "CS101", "days": 2, "reason": "medical"}) == RECOMMENDATION_WITHIN_POLICY
    assert recommend({"course": "CS101", "days": 3, "reason": "family"}) == RECOMMENDATION_WITHIN_POLICY
    assert recommend({"course": "CS101", "days": 1, "reason": "technical"}) == RECOMMENDATION_WITHIN_POLICY

    # Rule 3: > 3 days or other reasons -> needs_faculty_review
    assert recommend({"course": "CS101", "days": 4, "reason": "medical"}) == RECOMMENDATION_NEEDS_FACULTY_REVIEW
    assert recommend({"course": "CS101", "days": 2, "reason": "workload"}) == RECOMMENDATION_NEEDS_FACULTY_REVIEW
    assert recommend({"course": "CS101", "days": 2, "reason": "event"}) == RECOMMENDATION_NEEDS_FACULTY_REVIEW
    assert recommend({"course": "CS101", "days": 2, "reason": "other"}) == RECOMMENDATION_NEEDS_FACULTY_REVIEW


def test_write_reports(tmp_path):
    processed = [
        {"id": "T01", "course": "CS101", "days": 2, "reason": "medical", "recommendation": RECOMMENDATION_WITHIN_POLICY, "summary": "Req 2 days"},
        {"id": "T02", "course": "MA102", "days": 5, "reason": "family", "recommendation": RECOMMENDATION_NEEDS_FACULTY_REVIEW, "summary": "Req 5 days"},
        {"id": "T03", "course": None, "days": None, "reason": "other", "recommendation": RECOMMENDATION_NEEDS_MORE_INFO, "summary": "Req more info"}
    ]
    originals = [
        {"id": "T01", "request": "Text 1"},
        {"id": "T02", "request": "Text 2"},
        {"id": "T03", "request": "Text 3"}
    ]
    out_dir = str(tmp_path)
    reports = write_reports(processed, originals, output_dir=out_dir)

    assert os.path.exists(reports["results"])
    assert os.path.exists(reports["review_queue"])
    assert os.path.exists(reports["summary"])

    # Check results has no original text
    with open(reports["results"], "r", encoding="utf-8") as f:
        content = f.read()
        assert "Text 1" not in content

    # Check review_queue contains only T02 and T03 (not within_policy)
    with open(reports["review_queue"], "r", encoding="utf-8") as f:
        content = f.read()
        assert "T01" not in content
        assert "T02" in content
        assert "T03" in content
