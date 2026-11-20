# CIT Capstone: AI Judgment Framework
**Project:** Extension Request Sorter  
**Programme:** CIT AI-Native Engineering Programme · Semester 1 · Assessment 5

The **Judgment Framework** establishes the governance, accountability boundaries, and safety envelope for deploying AI in high-stakes academic administration. In accordance with the CIT AI-Native engineering philosophy, automation is never granted unmonitored decision authority.

---

### 1. Component Governance Matrix

| Pipeline Component | AI Responsibility | Cost of Being Wrong | Can it be verified without AI? | Who is Accountable? | Primary Defense & Safeguard Mechanism |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Course Code Identification** | Identifies course code from unstructured student text. | **Medium:** Wrong faculty receives request or valid request is rejected. | **Yes:** Direct exact-match verification against `courses.csv` catalog and string search in raw text. | **Python Validation Engine:** Code resets any unlisted/hallucinated course to `null`. | Deterministic catalog verification (`is_valid()`) strips unapproved course codes. |
| **Duration (Days) Extraction** | Identifies duration count ($1–30$). Must reject relative dates. | **High:** Student granted insufficient or excessive extension time. | **Yes:** Regular expression matching digits or English number words in raw input. | **Python Validation Engine:** Enforces `null` if student specified temporal dates without numbers. | Dual-layer check: LLM prompt constraint + Python regex fact-check (`is_valid()`). |
| **Reason Categorization** | Maps stated context into one of 6 categories. | **Low–Medium:** Misclassifies discretionary category, affecting review queue routing. | **Partially:** Rule-based keyword matching can detect obvious cases, but nuanced human prose requires faculty discretion. | **Course Faculty:** Final extension decisions are human-reviewed. | Requests categorized as non-routine are routed to `needs_faculty_review`. |
| **Summary & Medical Privacy** | Generates $\le 15$ word factual summary. | **Severe (Legal / Privacy Breach):** Disclosing student health diagnoses (e.g. psychiatric/medical). | **Yes:** Python dictionary search across protected illness/treatment terms and word counts. | **Python Sanitization Engine:** Replaces summary with neutral standardized phrasing. | Privacy scrubber intercepts and rewrites summary if any illness/treatment term appears. |
| **Extension Recommendation** | **None** (Delegated strictly to Python). | **Severe:** Inconsistent academic policy enforcement or unauthorized approval. | **Yes:** Pure deterministic Boolean logic in Python (`recommend()`). | **System Developer & Course Faculty:** Logic matches departmental policy constants. | LLM is structurally prohibited from recommending; policy runs entirely in Python. |
| **Final Extension Decision** | **None** (Zero automation). | **Critical:** Violates institutional regulations, equity standards, or student rights. | **Yes:** Academic faculty judgment. | **Course Faculty & Department HOD:** Humans retain 100% decision authority. | The tool only recommends queues; it never outputs "approved" or "rejected". |

---

### 2. What Python Cannot Check & The Faculty Human-in-the-Loop Safeguard

#### The Verification Gap
While deterministic Python fact-checking provides bulletproof validation against structural discrepancies (e.g., verifying if a course exists in `courses.csv` or whether a number was written), **Python and LLMs fundamentally cannot verify the truthfulness, authenticity, or gravity of real-world human circumstances.**

Specifically, the automated pipeline cannot check:
1. **Medical Authenticity:** Whether a student's claim of illness or emergency is genuine or supported by legitimate clinical documentation.
2. **Extenuating Circumstances:** Nuanced emotional, familial, or personal hardship that falls outside rigid categorizations.
3. **Academic Integrity History:** Whether the student has repeatedly requested extensions or has active integrity infractions.
4. **Pedagogical Deadlines:** Whether an upcoming assignment solution will be released to the cohort, making an extension pedagogically impossible.

#### How Faculty Cover the Gap
To ensure academic integrity and equitable student welfare:
- **`review_queue.csv` Interface:** The pipeline segregates every request requiring human discretion or missing data into `review_queue.csv`, preserving the raw, unredacted student submission solely for authorized course faculty.
- **Human Discretionary Checkpoint:** Faculty inspect supporting certificates, consult student welfare coordinators, and apply compassionate flexibility.
- **Zero-Auto-Approval Guarantee:** No student is ever granted an extension without explicit faculty sign-off.
