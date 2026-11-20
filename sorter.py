"""
CIT AI-Native Engineering Programme · Semester 1 · Assessment 5
Extension Request Sorter

This module provides the core pipeline for reading student extension requests,
extracting attributes via LLM, validating facts and privacy in Python,
applying department policy, and generating departmental reports.
"""

import os
import re
import csv
import json
import logging
from typing import Dict, List, Optional, Any, Tuple

# Set up logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("ExtensionSorter")

# ==============================================================================
# Department Extension Policy Constants
# ==============================================================================
MAX_DAYS_WITHIN_POLICY: int = 3
ALLOWED_POLICY_REASONS: set = {"medical", "family", "technical"}

RECOMMENDATION_WITHIN_POLICY: str = "within_policy"
RECOMMENDATION_NEEDS_FACULTY_REVIEW: str = "needs_faculty_review"
RECOMMENDATION_NEEDS_MORE_INFO: str = "needs_more_info"

VALID_REASONS: set = {"medical", "family", "technical", "event", "workload", "other"}

# Number words mapping for fact-checking days
WORD_TO_NUMBER: Dict[str, int] = {
    "one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
    "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10,
    "eleven": 11, "twelve": 12, "thirteen": 13, "fourteen": 14,
    "fifteen": 15, "twenty": 20, "thirty": 30
}

# Illness and medical treatment keywords for privacy enforcement
ILLNESS_TREATMENT_KEYWORDS: set = {
    "fever", "migraine", "flu", "cough", "bronchitis", "covid", "dengue",
    "infection", "vomiting", "diarrhea", "dehydration", "surgery", "operation",
    "fracture", "depression", "anxiety", "chemotherapy", "asthma", "pneumonia",
    "hospital", "hospitalized", "clinic", "doctor", "prescribed", "medication",
    "food poisoning", "bed rest", "illness", "diagnosed", "diagnosis", "headache"
}


# ==============================================================================
# Function 1: load_courses
# ==============================================================================
def load_courses(filepath: str = "courses.csv") -> Dict[str, str]:
    """
    Loads approved course catalog from CSV into a dictionary of code -> name.
    Uses try/except to handle missing or malformed files gracefully.
    """
    courses: Dict[str, str] = {}
    try:
        with open(filepath, mode="r", encoding="utf-8") as file:
            reader = csv.DictReader(file)
            for row in reader:
                code = row.get("code", "").strip().upper()
                name = row.get("name", "").strip()
                if code:
                    courses[code] = name
        logger.info(f"Loaded {len(courses)} courses from {filepath}")
    except FileNotFoundError:
        logger.error(f"Courses file not found at {filepath}")
        raise
    except Exception as e:
        logger.error(f"Error reading courses file {filepath}: {e}")
        raise
    return courses


# ==============================================================================
# Function 2: load_requests
# ==============================================================================
def load_requests(filepath: str = "requests.csv") -> List[Dict[str, str]]:
    """
    Loads raw student requests from CSV into a list of dictionaries.
    Schema: id, date, request.
    """
    requests_list: List[Dict[str, str]] = []
    try:
        with open(filepath, mode="r", encoding="utf-8") as file:
            reader = csv.DictReader(file)
            for row in reader:
                record = {
                    "id": row.get("id", "").strip(),
                    "date": row.get("date", "").strip(),
                    "request": row.get("request", "").strip()
                }
                if record["id"]:
                    requests_list.append(record)
        logger.info(f"Loaded {len(requests_list)} student requests from {filepath}")
    except FileNotFoundError:
        logger.error(f"Requests file not found at {filepath}")
        raise
    except Exception as e:
        logger.error(f"Error reading requests file {filepath}: {e}")
        raise
    return requests_list


# ==============================================================================
# Function 3: classify (LLM Call, Retry, and Fallback)
# ==============================================================================
def _call_llm_api(prompt: str, system_instruction: str) -> Optional[str]:
    """
    Internal helper to call configured LLM API (Gemini or OpenAI).
    Reads API key from environment, never hardcoded.
    """
    gemini_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    openai_key = os.getenv("OPENAI_API_KEY")

    if gemini_key:
        try:
            # Try Google GenAI SDK
            import google.generativeai as genai
            genai.configure(api_key=gemini_key)
            model = genai.GenerativeModel(
                model_name="gemini-1.5-flash",
                system_instruction=system_instruction
            )
            response = model.generate_content(prompt)
            if response and response.text:
                return response.text.strip()
        except Exception as e:
            logger.warning(f"Gemini API invocation attempt failed: {e}")

    if openai_key:
        try:
            import openai
            client = openai.OpenAI(api_key=openai_key)
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": system_instruction},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.0
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            logger.warning(f"OpenAI API invocation attempt failed: {e}")

    return None


def _fallback_extractor(request_text: str, course_catalog: Dict[str, str]) -> Dict[str, Any]:
    """
    Deterministic rule-based fallback extractor used when LLM call or retry fails.
    Ensures zero downtime and full offline resilience.
    """
    text_lower = request_text.lower()
    
    # 1. Course extraction
    extracted_course = None
    for code in course_catalog:
        if re.search(r'\b' + re.escape(code.lower()) + r'\b', text_lower):
            extracted_course = code
            break
    
    # 2. Days extraction (Strict: only if number is written, null for dates)
    extracted_days = None
    # Check if student explicitly specified a day of week / relative date without count
    relative_date_match = re.search(r'\b(on monday|on tuesday|on wednesday|on thursday|on friday|on saturday|on sunday|tomorrow|next week)\b', text_lower)
    
    # Check digits strictly associated with days (e.g., "2 days", "2 more days", "2-day")
    digit_match = re.search(r'\b(\d+)\s*(?:-| )?(?:more\s+)?days?\b', text_lower)
    if digit_match:
        val = int(digit_match.group(1))
        if 1 <= val <= 30:
            extracted_days = val
    else:
        # Check word numbers
        for word, num in WORD_TO_NUMBER.items():
            if re.search(r'\b' + word + r'\s+(?:more\s+)?days?\b', text_lower):
                extracted_days = num
                break
                
    if relative_date_match and not digit_match and not extracted_days:
        extracted_days = None

    # 3. Reason categorization
    if any(k in text_lower for k in ["fever", "unwell", "sick", "infection", "bronchitis", "hospital", "poisoning", "doctor"]):
        extracted_reason = "medical"
    elif any(k in text_lower for k in ["grandmother", "family", "sister", "brother", "wedding", "passed away", "emergency"]):
        extracted_reason = "family"
    elif any(k in text_lower for k in ["laptop", "wi-fi", "wifi", "hard drive", "crashed", "power cut", "corrupted", "technical"]):
        extracted_reason = "technical"
    elif any(k in text_lower for k in ["hackathon", "meet", "athletic", "competition", "conference"]):
        extracted_reason = "event"
    elif any(k in text_lower for k in ["workload", "midterm", "midterms", "exams", "deadlines"]):
        extracted_reason = "workload"
    else:
        extracted_reason = "other"

    # 4. Summary generation
    c_str = extracted_course if extracted_course else "course"
    d_str = f"{extracted_days} days" if extracted_days else "extension"
    summary = f"Requests {d_str} for {c_str}, {extracted_reason} reason"
    
    return {
        "course": extracted_course,
        "days": extracted_days,
        "reason": extracted_reason,
        "summary": summary
    }


def _validate_raw_llm_json(raw_text: str) -> Optional[Dict[str, Any]]:
    """
    Helper to sanitize and parse raw LLM JSON output.
    Returns parsed dictionary if schema is valid, else None.
    """
    if not raw_text:
        return None
    cleaned = raw_text.strip()
    # Strip markdown backticks if present
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
        cleaned = re.sub(r"\s*```$", "", cleaned)
    try:
        data = json.loads(cleaned)
        if isinstance(data, dict):
            required_keys = {"course", "days", "reason", "summary"}
            if required_keys.issubset(data.keys()):
                # Normalize types
                course = str(data["course"]).strip().upper() if data["course"] is not None else None
                days = int(data["days"]) if (data["days"] is not None and str(data["days"]).isdigit()) else None
                reason = str(data["reason"]).strip().lower() if data["reason"] else "other"
                if reason not in VALID_REASONS:
                    reason = "other"
                summary = str(data["summary"]).strip()
                return {
                    "course": course,
                    "days": days,
                    "reason": reason,
                    "summary": summary
                }
    except Exception:
        pass
    return None


def classify(
    request_text: str,
    course_catalog: Dict[str, str],
    system_prompt_path: str = "system_prompt.txt"
) -> Dict[str, Any]:
    """
    Extracts course, days, reason, and summary from student request.
    Follows required pattern:
    1. Reads system prompt from file.
    2. Sends request to LLM.
    3. Validates reply. If invalid, retries ONCE with clarification.
    4. If retry fails or API unavailable, falls back to deterministic rule-based extractor.
    """
    system_instruction = ""
    try:
        with open(system_prompt_path, mode="r", encoding="utf-8") as f:
            system_instruction = f.read()
    except Exception as e:
        logger.warning(f"Could not load system prompt from {system_prompt_path}: {e}")

    user_prompt = f"Extract extension request metadata from this student request:\n\n\"{request_text}\""
    
    # Attempt 1: Initial LLM call
    raw_response = _call_llm_api(user_prompt, system_instruction)
    parsed = _validate_raw_llm_json(raw_response) if raw_response else None

    # Attempt 2: Retry once if response was invalid
    if parsed is None and raw_response is not None:
        logger.info("LLM returned non-compliant output. Retrying once with strict JSON reinforcement...")
        retry_prompt = (
            f"{user_prompt}\n\nCRITICAL RETRY: Output MUST be strictly raw JSON with keys: "
            f"\"course\", \"days\", \"reason\", \"summary\". No codeblocks."
        )
        retry_response = _call_llm_api(retry_prompt, system_instruction)
        parsed = _validate_raw_llm_json(retry_response) if retry_response else None

    # Fallback if both attempts failed or API keys not present
    if parsed is None:
        logger.info("Using deterministic fallback extractor.")
        parsed = _fallback_extractor(request_text, course_catalog)

    return parsed


# ==============================================================================
# Function 4: is_valid (Deterministic Fact & Privacy Checks)
# ==============================================================================
def is_valid(
    extracted_data: Dict[str, Any],
    request_text: str,
    valid_courses: Dict[str, str]
) -> Dict[str, Any]:
    """
    Applies deterministic Python fact checks and privacy sanitization:
    1. Keep course only if in courses.csv AND written in student's request text.
    2. Keep days only if student wrote that number as digits or word in request.
    3. Privacy check: If summary names an illness or treatment, sanitize to neutral phrasing.
    4. Truncate summary to 15 words or fewer.
    """
    text_lower = request_text.lower()
    validated = dict(extracted_data)

    # 1. Fact-check course
    course = validated.get("course")
    if course:
        course_clean = str(course).strip().upper()
        # Must be in valid course catalog AND present in raw request text
        if (course_clean in valid_courses) and (course_clean.lower() in text_lower):
            validated["course"] = course_clean
        else:
            validated["course"] = None
    else:
        validated["course"] = None

    # 2. Fact-check days
    days = validated.get("days")
    if days is not None:
        try:
            days_int = int(days)
            if 1 <= days_int <= 30:
                # Student must have written this number as a digit or word
                digit_str = str(days_int)
                has_digit = re.search(r'\b' + re.escape(digit_str) + r'\b', text_lower) is not None
                
                # Check for word representation
                has_word = False
                for word, val in WORD_TO_NUMBER.items():
                    if val == days_int and re.search(r'\b' + re.escape(word) + r'\b', text_lower):
                        has_word = True
                        break

                if has_digit or has_word:
                    validated["days"] = days_int
                else:
                    validated["days"] = None
            else:
                validated["days"] = None
        except (ValueError, TypeError):
            validated["days"] = None
    else:
        validated["days"] = None

    # 3. Privacy Rule: check summary for illness/treatment keywords or names
    summary = validated.get("summary", "")
    summary_words = summary.split()
    summary_lower = summary.lower()

    # Check for illness terms or length violation
    has_illness_term = any(k in summary_lower for k in ILLNESS_TREATMENT_KEYWORDS)
    exceeds_word_limit = len(summary_words) > 15

    if has_illness_term or exceeds_word_limit or not summary:
        # Construct neutral compliant summary
        c_desc = validated["course"] if validated["course"] else "course"
        d_desc = f"{validated['days']} days" if validated["days"] is not None else "extension"
        validated["summary"] = f"Requests {d_desc} for {c_desc}, {validated.get('reason', 'other')} reason"
    else:
        # Keep original summary if clean
        validated["summary"] = " ".join(summary_words[:15])

    return validated


# ==============================================================================
# Function 5: recommend (Department Policy Application)
# ==============================================================================
def recommend(validated_data: Dict[str, Any]) -> str:
    """
    Applies the department extension policy in Python:
    1. If course or days is missing: needs_more_info
    2. If days is 3 or fewer and reason is medical, family or technical: within_policy
    3. Everything else: needs_faculty_review
    """
    course = validated_data.get("course")
    days = validated_data.get("days")
    reason = str(validated_data.get("reason", "")).lower()

    # Rule 1: Missing information
    if course is None or days is None:
        return RECOMMENDATION_NEEDS_MORE_INFO

    # Rule 2: Within standard department policy threshold
    if days <= MAX_DAYS_WITHIN_POLICY and reason in ALLOWED_POLICY_REASONS:
        return RECOMMENDATION_WITHIN_POLICY

    # Rule 3: Requires human faculty discretionary review
    return RECOMMENDATION_NEEDS_FACULTY_REVIEW


# ==============================================================================
# Function 6: write_reports
# ==============================================================================
def write_reports(
    processed_records: List[Dict[str, Any]],
    original_requests: List[Dict[str, str]],
    output_dir: str = "."
) -> Dict[str, str]:
    """
    Writes three segregated output files:
    1. results.csv: every request with id, course, days, reason, recommendation, summary. (No original text)
    2. review_queue.csv: every request not within_policy, with original request, for faculty only.
    3. summary.txt: aggregate metrics by recommendation, reason, and course for HOD. (No original text)
    """
    os.makedirs(output_dir, exist_ok=True)
    
    # Map original text by ID for review_queue lookup
    text_lookup = {r["id"]: r.get("request", "") for r in original_requests}

    results_file = os.path.join(output_dir, "results.csv")
    review_queue_file = os.path.join(output_dir, "review_queue.csv")
    summary_file = os.path.join(output_dir, "summary.txt")

    # 1. Write results.csv
    with open(results_file, mode="w", newline="", encoding="utf-8") as f:
        fieldnames = ["id", "course", "days", "reason", "recommendation", "summary"]
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for r in processed_records:
            writer.writerow({
                "id": r["id"],
                "course": r["course"] if r["course"] is not None else "",
                "days": r["days"] if r["days"] is not None else "",
                "reason": r["reason"],
                "recommendation": r["recommendation"],
                "summary": r["summary"]
            })

    # 2. Write review_queue.csv (all requests where recommendation != within_policy)
    with open(review_queue_file, mode="w", newline="", encoding="utf-8") as f:
        fieldnames = ["id", "course", "days", "reason", "recommendation", "summary", "request"]
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for r in processed_records:
            if r["recommendation"] != RECOMMENDATION_WITHIN_POLICY:
                writer.writerow({
                    "id": r["id"],
                    "course": r["course"] if r["course"] is not None else "",
                    "days": r["days"] if r["days"] is not None else "",
                    "reason": r["reason"],
                    "recommendation": r["recommendation"],
                    "summary": r["summary"],
                    "request": text_lookup.get(r["id"], "")
                })

    # 3. Generate and write summary.txt
    recommendation_counts: Dict[str, int] = {}
    reason_counts: Dict[str, int] = {}
    course_counts: Dict[str, int] = {}

    for r in processed_records:
        rec = r["recommendation"]
        recommendation_counts[rec] = recommendation_counts.get(rec, 0) + 1

        rsn = r["reason"]
        reason_counts[rsn] = reason_counts.get(rsn, 0) + 1

        crs = r["course"] if r["course"] else "Unspecified/Invalid"
        course_counts[crs] = course_counts.get(crs, 0) + 1

    total_requests = len(processed_records)

    with open(summary_file, mode="w", encoding="utf-8") as f:
        f.write("======================================================================\n")
        f.write("CIT ACADEMIC OPERATIONS: EXTENSION REQUEST TRIAGE SUMMARY (HOD REPORT)\n")
        f.write("======================================================================\n\n")
        f.write(f"Total Requests Processed: {total_requests}\n\n")

        f.write("--- BREAKDOWN BY RECOMMENDATION ---\n")
        for rec, count in sorted(recommendation_counts.items()):
            pct = (count / total_requests * 100) if total_requests else 0
            f.write(f"  * {rec:<25}: {count:>3} ({pct:5.1f}%)\n")
        f.write("\n")

        f.write("--- BREAKDOWN BY REASON ---\n")
        for rsn, count in sorted(reason_counts.items()):
            pct = (count / total_requests * 100) if total_requests else 0
            f.write(f"  * {rsn:<25}: {count:>3} ({pct:5.1f}%)\n")
        f.write("\n")

        f.write("--- BREAKDOWN BY COURSE ---\n")
        for crs, count in sorted(course_counts.items()):
            pct = (count / total_requests * 100) if total_requests else 0
            f.write(f"  * {crs:<25}: {count:>3} ({pct:5.1f}%)\n")
        f.write("\n")
        f.write("Policy Constants Applied:\n")
        f.write(f"  * MAX_DAYS_WITHIN_POLICY: {MAX_DAYS_WITHIN_POLICY}\n")
        f.write(f"  * ALLOWED_POLICY_REASONS: {sorted(list(ALLOWED_POLICY_REASONS))}\n")
        f.write("======================================================================\n")

    logger.info(f"Wrote outputs: {results_file}, {review_queue_file}, {summary_file}")
    return {
        "results": results_file,
        "review_queue": review_queue_file,
        "summary": summary_file
    }


# ==============================================================================
# Main Orchestration Loop
# ==============================================================================
def process_all_requests(
    courses_file: str = "courses.csv",
    requests_file: str = "requests.csv",
    output_dir: str = "."
) -> List[Dict[str, Any]]:
    """
    Runs the full end-to-end sorting pipeline.
    """
    print("\n========================================================")
    print("CIT Extension Request Sorter - Pipeline Execution")
    print("========================================================")
    
    courses = load_courses(courses_file)
    requests_data = load_requests(requests_file)

    processed_results: List[Dict[str, Any]] = []

    print(f"Processing {len(requests_data)} requests against {len(courses)} valid courses...")

    for item in requests_data:
        req_id = item["id"]
        req_text = item["request"]

        # Step 1: LLM Extraction (with retry & fallback)
        extracted = classify(req_text, courses)

        # Step 2: Python Fact & Privacy Checks
        validated = is_valid(extracted, req_text, courses)

        # Step 3: Python Policy Recommendation
        rec = recommend(validated)

        # Step 4: Aggregate record
        record = {
            "id": req_id,
            "course": validated["course"],
            "days": validated["days"],
            "reason": validated["reason"],
            "recommendation": rec,
            "summary": validated["summary"]
        }
        processed_results.append(record)

    # Step 5: Write all reports
    write_reports(processed_results, requests_data, output_dir=output_dir)
    print(f"Completed! Generated reports in '{output_dir}'.\n")
    return processed_results


if __name__ == "__main__":
    process_all_requests()
