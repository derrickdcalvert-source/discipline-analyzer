### SKILL: `atlas_data_ingestion`
**Version:** 1.2  
**Scope:** Multi-file discipline intake (Incident + Consequence) from SIS exports and generic CSV  
**Owner:** Atlas Pipeline

---

## PURPOSE
Atlas ingests raw discipline datasets and prepares them for downstream analysis **only when the dataset is analyzable for a full Decision Brief**. Atlas must be strict, auditable, deterministic, and aligned to how principals interpret suspensions (day-based unless explicit minutes are provided).

---

## INPUTS (V1.2)
Atlas accepts **two CSV files** per run:
- **Incident File (required)**: incident capture records
- **Consequence File (required)**: administrative response/removal records

Atlas will not generate the Decision Brief from a single incident-only file.

---

## REQUIRED JOIN KEY (V1.2)
- **Join key:** `Incident Number` (exact match required)
- No fallback joins (e.g., student_id + date) are permitted in v1.2.

---

## REQUIRED FIELDS (V1.2)

### Incident File (required columns)
- `Incident Number`
- `Incident Date & Time` (or a configured incident_date column)
- `Building` or `Entity Code` (campus identifier; exact field name may be mapped by operator)

### Consequence File (required columns)
- `Incident Number`
- `Consequence Type` (ISS / OSS / DAEP / JJAEP / EXPULSION / LOCAL_ONLY)
- `Consequence Start Date`
- `Consequence End Date`

### Optional (but supported) Consequence Fields
- `Instructional Minutes Lost` (or operator-mapped equivalent)

---

## MECHANICAL PREPROCESSING (ALLOWED)
Atlas may perform **mechanical, non-semantic normalization** as a logged, reversible step:
- trim whitespace
- normalize unicode
- remove BOM/invisible characters

Atlas must preserve original headers and log a normalized alias map.

---

## MINUTES CALCULATION STANDARD (PRINCIPAL-LANGUAGE RULE)
Atlas computes instructional minutes using a strict precedence order:

### Precedence
1) **If explicit minutes exist** (`Instructional Minutes Lost`, or mapped equivalent) → **use it**
2) Else compute using dates:
   - **Minutes per instructional day:** **480**
   - **Exclude:** weekends only
   - **Counting rule:** **inclusive** (start and end dates count if instructional days)
3) If neither explicit minutes nor valid dates are available → **halt** (cannot produce the brief honestly)

### Partial Days
- Atlas **does not** infer partial days.
- If a removal occurs on a single date and no explicit minutes are provided, Atlas counts **one full day (480 minutes)**.

Atlas must log how many rows used:
- explicit minutes
- date-derived minutes

---

## JOIN COMPLETENESS REQUIREMENT (NON-NEGOTIABLE)
Atlas must compute:
- `join_success = matched_incidents / total_incidents`

### Threshold
- **If join_success < 0.95 → halt ingestion**

No partial brief is allowed below threshold.

---

## RESPONSIBILITIES
Atlas must:
1) Verify both files are parseable and machine-readable.
2) Read headers exactly as present and create a normalized alias map (logged + reversible).
3) Validate required columns exist in both files. **Missing required columns = halt.**
4) Join incident + consequence datasets using `Incident Number` only.
5) Calculate and log:
   - total incidents (pre-join)
   - total consequences (pre-join)
   - matched incidents
   - join_success rate
6) Enforce join threshold (≥ 95%).
7) Validate consequence integrity:
   - Consequence Type present (required)
   - Start/End dates present and valid (start ≤ end)
8) Compute instructional minutes per the Minutes Calculation Standard.
9) Exclude rows missing required **values** (not columns) only when:
   - required columns exist, and
   - exclusions do not reduce join_success below 95%, and
   - exclusions are fully logged
10) Produce a **Data Readiness Report** before analysis begins, including:
   - file names + timestamp
   - total row counts per file
   - join_success rate
   - excluded row counts (by reason)
   - minutes method breakdown (explicit vs date-derived)
   - assumptions (480/day, weekends excluded, inclusive)
11) Surface all flags to the operator. No suppressed flags.

---

## PROHIBITIONS
Atlas is prohibited from:
- Guessing column meaning without explicit operator confirmation.
- Performing fallback joins.
- Inferring missing consequence fields (type, dates, minutes).
- Parsing narrative descriptions to determine consequence or duration.
- Producing the Decision Brief if:
  - either file is missing
  - required columns are missing
  - join_success < 95%
  - consequence_type missing
  - dates missing/invalid AND explicit minutes missing
- Using LLM inference or probabilistic logic during ingestion.
- Modifying data without logging the transformation as discrete + reversible.

---

## FAILURE PROTOCOL
If ingestion fails, Atlas must halt and return a structured error containing:
- failure reason (single primary cause)
- affected file (incident vs consequence)
- exact missing/invalid fields
- join_success rate (if applicable)
- concrete operator fix steps

No partial brief. No partial analysis.

---

## EXPLICIT INFERENCE RULE (FOR COLUMN MAPPING ONLY)
Atlas may surface candidate mappings **deterministically** (string similarity, known header variants) **only to propose options**. Atlas must:
- require explicit operator confirmation
- log the confirmation
- make mappings reversible

Atlas must not apply candidate mappings unilaterally.

---

## SCOPE BOUNDARY
This skill governs ingestion only. It does not govern analysis logic, posture determination, output formatting, or compliance reporting.

---

## CONSEQUENCE ENUMS (APPROVED, CASE-INSENSITIVE)
- ISS
- OSS
- DAEP
- JJAEP
- EXPULSION
- LOCAL_ONLY
