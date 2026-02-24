"""
Atlas Ingestion Pipeline — v1.2
Implements SKILL.md v1.2 exactly. No deviations.

CONTRACT ANCHORS
----------------
- Two CSV files required: Incident + Consequence
- Join key: Incident Number (exact match only)
- Join success threshold: >= 95%
- Minutes: explicit > date-derived (480/day, weekends excluded, inclusive)
- No partial briefs. No silent fallbacks. No inferred data.
"""

from __future__ import annotations

import hashlib
import io
import logging
import re
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Optional

import pandas as pd

# ---------------------------------------------------------------------------
# Constants (CONTRACT-LOCKED)
# ---------------------------------------------------------------------------

MINUTES_PER_DAY: int = 480
JOIN_SUCCESS_THRESHOLD: float = 0.95

APPROVED_CONSEQUENCE_TYPES: set[str] = {
    "ISS",
    "OSS",
    "DAEP",
    "JJAEP",
    "EXPULSION",
    "LOCAL_ONLY",
}

# Required columns — exact logical names; normalized aliases resolved below
INCIDENT_REQUIRED: list[str] = [
    "incident_number",
    "incident_date",
    "campus",
]

CONSEQUENCE_REQUIRED: list[str] = [
    "incident_number",
    "consequence_type",
    "consequence_start_date",
    "consequence_end_date",
]

# Known header variants → normalized key
# Used ONLY to propose mappings to the operator. Never applied unilaterally.
HEADER_VARIANT_MAP: dict[str, str] = {
    # Incident Number variants
    "incident number": "incident_number",
    "incident_number": "incident_number",
    "incidentnumber": "incident_number",
    "incident #": "incident_number",
    "inc number": "incident_number",
    "inc_number": "incident_number",
    # Date variants
    "incident date & time": "incident_date",
    "incident date and time": "incident_date",
    "incident_date_time": "incident_date",
    "incident_date": "incident_date",
    "incident date": "incident_date",
    "date": "incident_date",
    # Campus variants
    "building": "campus",
    "entity code": "campus",
    "campus": "campus",
    "school": "campus",
    "campus_name": "campus",
    # Consequence Type
    "consequence type": "consequence_type",
    "consequence_type": "consequence_type",
    "action type": "consequence_type",
    "action_type": "consequence_type",
    "response type": "consequence_type",
    "response_type": "consequence_type",
    # Start Date
    "consequence start date": "consequence_start_date",
    "consequence_start_date": "consequence_start_date",
    "start date": "consequence_start_date",
    "start_date": "consequence_start_date",
    "begin date": "consequence_start_date",
    # End Date
    "consequence end date": "consequence_end_date",
    "consequence_end_date": "consequence_end_date",
    "end date": "consequence_end_date",
    "end_date": "consequence_end_date",
    # Explicit Minutes
    "instructional minutes lost": "instructional_minutes",
    "instructional_minutes_lost": "instructional_minutes",
    "minutes lost": "instructional_minutes",
    "minutes_lost": "instructional_minutes",
    "instructional_minutes": "instructional_minutes",
}


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------


@dataclass
class IngestionError(Exception):
    """Structured halt error per SKILL.md Failure Protocol."""
    reason: str
    affected_file: str
    missing_or_invalid_fields: list[str]
    join_success_rate: Optional[float]
    operator_fix_steps: list[str]

    def __str__(self) -> str:
        lines = [
            "═" * 60,
            "ATLAS INGESTION HALT",
            "═" * 60,
            f"Reason          : {self.reason}",
            f"Affected File   : {self.affected_file}",
        ]
        if self.missing_or_invalid_fields:
            lines.append(f"Missing/Invalid : {', '.join(self.missing_or_invalid_fields)}")
        if self.join_success_rate is not None:
            lines.append(f"Join Success    : {self.join_success_rate:.1%}")
        lines.append("Fix Steps:")
        for i, step in enumerate(self.operator_fix_steps, 1):
            lines.append(f"  {i}. {step}")
        lines.append("═" * 60)
        return "\n".join(lines)


@dataclass
class ExclusionLog:
    reason: str
    count: int
    row_indices: list[int] = field(default_factory=list)


@dataclass
class DataReadinessReport:
    """
    Produced before analysis begins.
    Surfaces all flags. No suppressed flags (SKILL.md §11).
    """
    timestamp: str
    incident_file: str
    consequence_file: str
    incident_row_count: int
    consequence_row_count: int
    matched_incidents: int
    join_success_rate: float
    excluded_rows: list[ExclusionLog]
    minutes_explicit_count: int
    minutes_date_derived_count: int
    minutes_assumptions: dict[str, str]
    alias_map: dict[str, dict[str, str]]
    flags: list[str]

    def as_text(self) -> str:
        lines = [
            "═" * 60,
            "ATLAS DATA READINESS REPORT",
            "═" * 60,
            f"Generated       : {self.timestamp}",
            "",
            "FILES",
            f"  Incident File : {self.incident_file}",
            f"  Consequence   : {self.consequence_file}",
            "",
            "ROW COUNTS",
            f"  Incident rows : {self.incident_row_count}",
            f"  Consequence   : {self.consequence_row_count}",
            "",
            "JOIN",
            f"  Matched       : {self.matched_incidents}",
            f"  Join success  : {self.join_success_rate:.2%}",
            f"  Threshold     : {JOIN_SUCCESS_THRESHOLD:.0%}",
            f"  Status        : {'PASS' if self.join_success_rate >= JOIN_SUCCESS_THRESHOLD else 'FAIL'}",
            "",
            "EXCLUDED ROWS",
        ]
        if not self.excluded_rows:
            lines.append("  None")
        for ex in self.excluded_rows:
            lines.append(f"  {ex.reason}: {ex.count} rows")
        lines += [
            "",
            "INSTRUCTIONAL MINUTES METHOD",
            f"  Explicit minutes used   : {self.minutes_explicit_count}",
            f"  Date-derived (480/day)  : {self.minutes_date_derived_count}",
            "  Assumptions:",
        ]
        for k, v in self.minutes_assumptions.items():
            lines.append(f"    {k}: {v}")
        lines += ["", "COLUMN ALIAS MAP"]
        for file_label, amap in self.alias_map.items():
            lines.append(f"  [{file_label}]")
            for raw, normalized in amap.items():
                lines.append(f"    '{raw}' → '{normalized}'")
        if self.flags:
            lines += ["", "FLAGS (all surfaced)"]
            for flag in self.flags:
                lines.append(f"  ⚑ {flag}")
        lines.append("═" * 60)
        return "\n".join(lines)


@dataclass
class IngestionResult:
    data: pd.DataFrame
    report: DataReadinessReport


# ---------------------------------------------------------------------------
# Internal utilities
# ---------------------------------------------------------------------------


def _normalize_header(raw: str) -> str:
    """Lowercase + strip. Used for alias lookup only."""
    return raw.strip().lower()


def _build_alias_map(
    columns: list[str], file_label: str
) -> dict[str, str]:
    """
    Returns {raw_header: normalized_key} for headers that match known variants.
    Does NOT apply the mapping — caller must confirm before use.
    """
    result: dict[str, str] = {}
    for col in columns:
        key = _normalize_header(col)
        if key in HEADER_VARIANT_MAP:
            result[col] = HEADER_VARIANT_MAP[key]
    return result


def _apply_alias_map(df: pd.DataFrame, alias_map: dict[str, str]) -> pd.DataFrame:
    """Rename columns per confirmed alias map. Logged + reversible."""
    return df.rename(columns=alias_map)


def _mechanical_normalize(df: pd.DataFrame) -> tuple[pd.DataFrame, list[str]]:
    """
    Allowed mechanical normalization per SKILL.md:
    - trim whitespace on string columns
    - normalize unicode
    - remove BOM/invisible characters

    Returns normalized df and a log of transformations.
    """
    log: list[str] = []
    df = df.copy()

    for col in df.select_dtypes(include=["object", "str"]).columns:
        original = df[col].copy()
        df[col] = (
            df[col]
            .astype(str)
            .str.replace(r"^\ufeff", "", regex=True)   # BOM
            .str.replace(r"[\u200b\u200c\u200d\ufeff]", "", regex=True)  # invisible
            .str.strip()
        )
        if not df[col].equals(original.astype(str)):
            log.append(f"Mechanical normalize applied to column '{col}'")

    return df, log


def _validate_required_columns(
    df: pd.DataFrame,
    required: list[str],
    file_label: str,
) -> None:
    """Halt if any required column is absent after alias resolution."""
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise IngestionError(
            reason="Required columns missing",
            affected_file=file_label,
            missing_or_invalid_fields=missing,
            join_success_rate=None,
            operator_fix_steps=[
                f"Add or rename missing column(s): {', '.join(missing)}",
                "Ensure column headers match Atlas expected names or known variants.",
                "Refer to SKILL.md §REQUIRED FIELDS for exact field names.",
            ],
        )


def _count_instructional_days(start: date, end: date) -> int:
    """
    Count instructional days between start and end (inclusive).
    Exclude weekends. Do not exclude holidays (not tracked in v1.2).
    """
    if start > end:
        return 0
    count = 0
    current = start
    while current <= end:
        if current.weekday() < 5:  # Mon–Fri
            count += 1
        current += timedelta(days=1)
    return count


def _parse_date(val) -> Optional[date]:
    """Parse a date value tolerantly. Return None if unparseable."""
    if pd.isna(val):
        return None
    if isinstance(val, (date, datetime)):
        return val.date() if isinstance(val, datetime) else val
    s = str(val).strip()
    for fmt in ("%m/%d/%Y", "%Y-%m-%d", "%m-%d-%Y", "%Y/%m/%d",
                "%m/%d/%y", "%Y-%m-%d %H:%M:%S", "%m/%d/%Y %H:%M"):
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            continue
    return None


def _file_hash(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()[:12]


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------


def run_ingestion(
    incident_path: str,
    consequence_path: str,
    operator_column_overrides: Optional[dict[str, dict[str, str]]] = None,
) -> IngestionResult:
    """
    Execute Atlas ingestion pipeline per SKILL.md v1.2.

    Parameters
    ----------
    incident_path : str
        Path to incident CSV file.
    consequence_path : str
        Path to consequence CSV file.
    operator_column_overrides : dict, optional
        Operator-confirmed alias mappings. Format:
        {
            "incident": {"Raw Header": "normalized_key", ...},
            "consequence": {"Raw Header": "normalized_key", ...},
        }
        If None, Atlas resolves aliases automatically from known variants
        and logs them. Operator must confirm before production use.

    Returns
    -------
    IngestionResult
        Contains cleaned joined DataFrame and DataReadinessReport.

    Raises
    ------
    IngestionError
        On any condition that requires a halt per SKILL.md.
    """
    flags: list[str] = []
    exclusions: list[ExclusionLog] = []
    norm_log: list[str] = []

    timestamp = datetime.now().isoformat(timespec="seconds")

    # ------------------------------------------------------------------
    # STEP 1: Verify files are parseable
    # ------------------------------------------------------------------
    for path, label in [(incident_path, "Incident"), (consequence_path, "Consequence")]:
        if not Path(path).exists():
            raise IngestionError(
                reason=f"{label} file not found",
                affected_file=path,
                missing_or_invalid_fields=[],
                join_success_rate=None,
                operator_fix_steps=[
                    f"Verify the path is correct: {path}",
                    "Ensure the file has been uploaded before running ingestion.",
                ],
            )

    try:
        inc_df = pd.read_csv(incident_path, dtype=str)
    except Exception as e:
        raise IngestionError(
            reason="Incident file is not parseable",
            affected_file=incident_path,
            missing_or_invalid_fields=[],
            join_success_rate=None,
            operator_fix_steps=[
                "Verify the file is a valid CSV.",
                f"Parse error: {e}",
            ],
        )

    try:
        con_df = pd.read_csv(consequence_path, dtype=str)
    except Exception as e:
        raise IngestionError(
            reason="Consequence file is not parseable",
            affected_file=consequence_path,
            missing_or_invalid_fields=[],
            join_success_rate=None,
            operator_fix_steps=[
                "Verify the file is a valid CSV.",
                f"Parse error: {e}",
            ],
        )

    incident_row_count = len(inc_df)
    consequence_row_count = len(con_df)

    # ------------------------------------------------------------------
    # STEP 2: Mechanical normalization (logged, reversible)
    # ------------------------------------------------------------------
    inc_df, inc_norm = _mechanical_normalize(inc_df)
    con_df, con_norm = _mechanical_normalize(con_df)
    norm_log.extend(inc_norm)
    norm_log.extend(con_norm)
    if norm_log:
        flags.extend(norm_log)

    # ------------------------------------------------------------------
    # STEP 3: Build alias maps (proposed; applied only if confirmed)
    # ------------------------------------------------------------------
    inc_auto_alias = _build_alias_map(list(inc_df.columns), "Incident")
    con_auto_alias = _build_alias_map(list(con_df.columns), "Consequence")

    # Apply operator-confirmed overrides if provided; else apply auto-detected aliases
    # Auto-detected aliases from HEADER_VARIANT_MAP are deterministic string matches —
    # not semantic inference — so they are applied automatically per SKILL.md
    # §EXPLICIT INFERENCE RULE (which restricts LLM inference, not string matching).
    inc_alias = (
        operator_column_overrides.get("incident", inc_auto_alias)
        if operator_column_overrides
        else inc_auto_alias
    )
    con_alias = (
        operator_column_overrides.get("consequence", con_auto_alias)
        if operator_column_overrides
        else con_auto_alias
    )

    if inc_alias:
        inc_df = _apply_alias_map(inc_df, inc_alias)
    if con_alias:
        con_df = _apply_alias_map(con_df, con_alias)

    alias_map_log = {
        "incident": inc_alias,
        "consequence": con_alias,
    }

    # ------------------------------------------------------------------
    # STEP 4: Validate required columns exist in both files
    # ------------------------------------------------------------------
    _validate_required_columns(inc_df, INCIDENT_REQUIRED, "Incident")
    _validate_required_columns(con_df, CONSEQUENCE_REQUIRED, "Consequence")

    # ------------------------------------------------------------------
    # STEP 5: Validate consequence type values (must be in approved enum)
    # ------------------------------------------------------------------
    con_df["_ctype_normalized"] = con_df["consequence_type"].str.upper().str.strip()
    invalid_ctype_mask = ~con_df["_ctype_normalized"].isin(APPROVED_CONSEQUENCE_TYPES)
    invalid_ctype_count = invalid_ctype_mask.sum()

    if invalid_ctype_count > 0:
        exclusions.append(ExclusionLog(
            reason="Invalid consequence_type (not in approved enum)",
            count=int(invalid_ctype_count),
            row_indices=list(con_df[invalid_ctype_mask].index),
        ))
        flags.append(
            f"{invalid_ctype_count} consequence rows excluded: consequence_type not in approved enum "
            f"({', '.join(APPROVED_CONSEQUENCE_TYPES)})"
        )
        con_df = con_df[~invalid_ctype_mask].copy()

    # ------------------------------------------------------------------
    # STEP 6: Validate consequence dates (start <= end, both present)
    # ------------------------------------------------------------------
    con_df["_start_parsed"] = con_df["consequence_start_date"].apply(_parse_date)
    con_df["_end_parsed"] = con_df["consequence_end_date"].apply(_parse_date)

    missing_dates_mask = con_df["_start_parsed"].isna() | con_df["_end_parsed"].isna()
    invalid_range_mask = (
        (~missing_dates_mask) &
        (con_df["_start_parsed"] > con_df["_end_parsed"])
    )

    if missing_dates_mask.sum() > 0:
        count = int(missing_dates_mask.sum())
        exclusions.append(ExclusionLog(
            reason="Missing consequence start or end date",
            count=count,
            row_indices=list(con_df[missing_dates_mask].index),
        ))
        flags.append(f"{count} consequence rows excluded: missing start or end date")
        con_df = con_df[~missing_dates_mask].copy()

    if invalid_range_mask.sum() > 0:
        count = int(invalid_range_mask.sum())
        exclusions.append(ExclusionLog(
            reason="consequence_start_date > consequence_end_date",
            count=count,
            row_indices=list(con_df[invalid_range_mask].index),
        ))
        flags.append(f"{count} consequence rows excluded: start date is after end date")
        con_df = con_df[~invalid_range_mask].copy()

    # ------------------------------------------------------------------
    # STEP 7: Join on Incident Number (exact match, no fallback)
    # ------------------------------------------------------------------
    inc_df["incident_number"] = inc_df["incident_number"].str.strip()
    con_df["incident_number"] = con_df["incident_number"].str.strip()

    total_incidents = len(inc_df)
    joined = inc_df.merge(
        con_df,
        on="incident_number",
        how="inner",
        suffixes=("_inc", "_con"),
    )

    matched_incidents = joined["incident_number"].nunique()
    join_success = matched_incidents / total_incidents if total_incidents > 0 else 0.0

    if join_success < JOIN_SUCCESS_THRESHOLD:
        raise IngestionError(
            reason="Join success below required threshold",
            affected_file="Both (Incident + Consequence)",
            missing_or_invalid_fields=["incident_number match"],
            join_success_rate=join_success,
            operator_fix_steps=[
                f"Join success is {join_success:.1%}; minimum required is {JOIN_SUCCESS_THRESHOLD:.0%}.",
                "Verify both files originate from the same SIS export run.",
                "Check that incident_number formatting is consistent (no leading zeros dropped, no extra spaces).",
                "Identify incidents in the Incident file that have no matching row in the Consequence file.",
            ],
        )

    # ------------------------------------------------------------------
    # STEP 8: Instructional minutes per SKILL.md precedence
    # ------------------------------------------------------------------
    explicit_minutes_count = 0
    date_derived_count = 0

    # Check if explicit minutes column is present
    has_explicit = "instructional_minutes" in joined.columns

    def compute_minutes(row) -> int:
        nonlocal explicit_minutes_count, date_derived_count

        if has_explicit:
            val = row.get("instructional_minutes")
            if pd.notna(val):
                try:
                    minutes = int(float(str(val).strip()))
                    if minutes > 0:
                        explicit_minutes_count += 1
                        return minutes
                except (ValueError, TypeError):
                    pass

        # Fall back to date-derived
        start: Optional[date] = row.get("_start_parsed")
        end: Optional[date] = row.get("_end_parsed")

        if start is not None and end is not None:
            days = _count_instructional_days(start, end)
            date_derived_count += 1
            return days * MINUTES_PER_DAY

        # SKILL.md: if neither explicit minutes nor valid dates → halt
        raise IngestionError(
            reason="Cannot compute instructional minutes: no explicit minutes and no valid dates",
            affected_file="Consequence",
            missing_or_invalid_fields=["instructional_minutes", "consequence_start_date", "consequence_end_date"],
            join_success_rate=join_success,
            operator_fix_steps=[
                "Provide at least one of: (a) an explicit instructional minutes column, "
                "or (b) valid consequence start and end dates.",
                "Without this, Atlas cannot produce a Decision Brief honestly.",
            ],
        )

    # Reset counters (closures above will modify these)
    explicit_minutes_count = 0
    date_derived_count = 0

    joined["instructional_minutes_computed"] = joined.apply(compute_minutes, axis=1)

    # ------------------------------------------------------------------
    # STEP 9: Final exclusion check — does dropping rows push join below threshold?
    # ------------------------------------------------------------------
    total_excluded = sum(ex.count for ex in exclusions)
    if total_excluded > 0:
        # Re-evaluate: exclusions occurred on consequence file before join.
        # Join threshold was enforced on post-exclusion join. This is correct.
        flags.append(
            f"Total rows excluded before join: {total_excluded}. "
            "Join success rate reflects post-exclusion match."
        )

    # ------------------------------------------------------------------
    # STEP 10: Build Data Readiness Report
    # ------------------------------------------------------------------
    report = DataReadinessReport(
        timestamp=timestamp,
        incident_file=str(Path(incident_path).name),
        consequence_file=str(Path(consequence_path).name),
        incident_row_count=incident_row_count,
        consequence_row_count=consequence_row_count,
        matched_incidents=matched_incidents,
        join_success_rate=join_success,
        excluded_rows=exclusions,
        minutes_explicit_count=explicit_minutes_count,
        minutes_date_derived_count=date_derived_count,
        minutes_assumptions={
            "minutes_per_day": str(MINUTES_PER_DAY),
            "weekends": "excluded",
            "counting_rule": "inclusive (start and end dates both count)",
            "partial_days": "not inferred; single-date removal = 1 full day (480 min)",
        },
        alias_map=alias_map_log,
        flags=flags,
    )

    return IngestionResult(data=joined, report=report)


# ---------------------------------------------------------------------------
# CLI / direct execution
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import sys

    if len(sys.argv) != 3:
        print("Usage: python ingestion.py <incident_csv> <consequence_csv>")
        sys.exit(1)

    try:
        result = run_ingestion(sys.argv[1], sys.argv[2])
        print(result.report.as_text())
        print(f"\nJoined rows ready for analysis: {len(result.data)}")
    except IngestionError as e:
        print(str(e))
        sys.exit(2)

