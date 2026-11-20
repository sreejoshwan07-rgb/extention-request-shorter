# CIT Capstone Specification: Extension Request Sorter
**CIT AI-Native Engineering Programme · Semester 1 · Assessment 5**  
**Author:** Individual Engineering Submission | **Status:** Checkpoint 1 Sign-Off Ready

---

### 1. System Overview & Problem Statement
Every assignment deadline creates a high-volume influx of student extension requests. Faculty spend critical hours manually reading unstructured emails, parsing course codes and duration requests, verifying prerequisites against syllabus policies, and checking for missing information. 

The **Extension Request Sorter** is a console-based, AI-native decision-support pipeline. It delegates low-level entity extraction to an LLM, rigorously fact-checks and privacy-sanitizes the extracted data in deterministic Python, applies academic extension policies, and triages requests into three explicit operational queues. 

> **Core Principle:** The system is strictly a recommendation and triage aid. The tool **never** approves or rejects requests; academic faculty retain 100% final decision authority.

---

### 2. Input Specifications
The system processes two CSV inputs with explicit header schemas:
1. **`courses.csv`**: Approved department course directory for the active semester.
   - Schema: `code,name` (e.g., `CS101,Programming in Python`).
2. **`requests.csv`**: Unstructured student submissions containing varied levels of completeness and informal phrasing.
   - Schema: `id,date,request` (e.g., `R01,2026-10-01,"Please give me 2 more days for CS101..."`).

---

### 3. LLM Extraction Contract & JSON Schema
The LLM acts solely as an extraction parser, guided by the **5-Role Prompt Framework** (Authority, Exemplar, Constraint, Rubric, Metadata). It must return a single, valid JSON object with four exact keys:

```json
{
  "course": "CS101",
  "days": 2,
  "reason": "medical",
  "summary": "Requests 2 days for CS101 lab record, medical reason"
}
```

| Field | Allowed Values | Extraction & Normalization Rule |
| :--- | :--- | :--- |
| `course` | Course code string or `null` | Must match student text verbatim. Set to `null` if omitted or ambiguous. |
| `days` | Integer `1–30` or `null` | Only capture explicit quantitative numbers written by student (digits or words like "two"). **Strict Rule:** Set to `null` for relative dates (e.g., "by Monday", "next week"). Never calculate dates. |
| `reason` | `medical`, `family`, `technical`, `event`, `workload`, `other` | Categorized based strictly on stated cause. Defaults to `"other"` if unstated. No hallucinations. |
| `summary` | Text string ($\le 15$ words) | Concise neutral description. **Strict Rule:** Must NOT contain specific illness names, medical treatments, or individual names. |

---

### 4. Deterministic Fact-Checking & Privacy Sanitization in Python
LLM responses are not inherently trusted. Python validates facts deterministically prior to policy evaluation:
1. **Course Code Catalog Verification:** Keep `course` only if it exists in `courses.csv` AND appears verbatim in `request`. If invalid or unlisted, it is reset to `null`.
2. **Explicit Days Verification:** Keep `days` only if the exact integer or corresponding word (e.g., `2` or `"two"`) appears directly in the raw request text.
3. **Medical Privacy & Redaction Engine:** If the LLM summary contains specific medical conditions or treatments (e.g., "fever", "migraine", "bronchitis", "surgery", "depression"), Python intercepts and enforces neutral phrasing: `"Requests <days> days for <course>, medical reason"`.

---

### 5. Extension Policy Logic
The policy engine runs in pure Python with configurable constants:
- **Constants:** `MAX_DAYS_WITHIN_POLICY = 3`, `ALLOWED_POLICY_REASONS = {"medical", "family", "technical"}`.
- **Triage Classification Rules:**
  1. **`needs_more_info`**: If either `course` is `null` OR `days` is `null`.
  2. **`within_policy`**: If `days <= MAX_DAYS_WITHIN_POLICY` AND `reason` in `ALLOWED_POLICY_REASONS`.
  3. **`needs_faculty_review`**: All other valid requests (e.g., $>3$ days, workload, university events, compassionate grounds).

---

### 6. Output Specifications
The system produces three segregated files ensuring confidentiality and operational clarity:
1. **`results.csv`**: (`id,course,days,reason,recommendation,summary`) — Complete audited dataset for registrar records. Excludes raw student text.
2. **`review_queue.csv`**: (`id,course,days,reason,recommendation,summary,request`) — Filtered queue of all requests where recommendation $\ne$ `within_policy`, including raw student text for faculty discretion.
3. **`summary.txt`**: Aggregated management metrics for the Head of Department (HOD) displaying counts broken down by recommendation, reason, and course. Zero student text.
