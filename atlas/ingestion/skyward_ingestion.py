"""
Atlas Skyward Ingestion Gate - V1
Single-file entry point for Skyward Discipline - Incident Offense Name Actions export.
"""

from __future__ import annotations
import io
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional
import pandas as pd

REQUIRED_COLUMNS = ["Date", "Grade", "Incident_Type", "Location", "Time_Block", "Response"]

SKYWARD_COLUMN_MAP = {
    "Incident Date": "Date", "Incident Date & Time": "Date",
    "Incident Date and Time": "Date", "Incident_Date": "Date",
    "Incident_Date_Time": "Date", "IncidentDate": "Date", "date": "Date",
    "Grade": "Grade", "Student Grade": "Grade", "Grade Level": "Grade", "Grd": "Grade",
    "Offense": "Incident_Type", "Offense Description": "Incident_Type",
    "Offense Name": "Incident_Type", "Incident Type": "Incident_Type",
    "Incident_Type": "Incident_Type", "IncidentType": "Incident_Type",
    "Location": "Location", "Incident Location": "Location",
    "Location Description": "Location",
    "Action": "Response", "Action Type": "Response",
    "Action Description": "Response", "Response": "Response",
    "Consequence": "Response", "Consequence Type": "Response",
    "Total to Serve": "Days_Removed", "Days to Serve": "Days_Removed",
    "Total Days": "Days_Removed", "Days Removed": "Days_Removed",
    "Days_Removed": "Days_Removed", "Serve Days": "Days_Removed",
    "Student Number": "Student_ID", "Student ID": "Student_ID",
    "StudentID": "Student_ID", "Stu Number": "Student_ID",
    "Reported Federal Race": "Race", "Federal Race": "Race",
    "Race": "Race", "Ethnicity": "Race",
    "Gender": "Gender", "Sex": "Gender",
    "Has Active Special Education": "SPED", "Special Education": "SPED",
    "SPED": "SPED", "SpEd": "SPED",
    "Has Active EB": "EB", "English Learner": "EB",
    "EL Status": "EB", "EL": "EB", "EB": "EB",
    "Entity": "Entity", "Entity Code": "Entity",
    "Campus": "Campus", "School": "Campus", "Building": "Campus",
}

@dataclass
class SkywardIngestionError(Exception):
    reason: str
    fix_steps: list

    def __str__(self):
        lines = ["ATLAS INGESTION HALT", f"Reason: {self.reason}", "", "How to fix:"]
        for i, step in enumerate(self.fix_steps, 1):
            lines.append(f"  {i}. {step}")
        return "\n".join(lines)

@dataclass
class SkywardIngestionResult:
    df: object
    rows_uploaded: int
    rows_excluded: int
    exclusion_notes: list
    campus_identifier: str
    mapped_columns: dict
    unmapped_columns: list
    flags: list

def _read_file(uploaded_file):
    name = getattr(uploaded_file, "name", "unknown")
    try:
        if name.endswith(".csv"):
            return pd.read_csv(uploaded_file, dtype=str)
        elif name.endswith((".xlsx", ".xls")):
            return pd.read_excel(uploaded_file, dtype=str)
        else:
            raise SkywardIngestionError(
                reason=f"Unsupported file type: '{name}'",
                fix_steps=["Upload a CSV or Excel file.", "Export from Skyward Discipline report."],
            )
    except SkywardIngestionError:
        raise
    except Exception as e:
        raise SkywardIngestionError(
            reason=f"File could not be read: {e}",
            fix_steps=["Verify file is not corrupted.", "Re-export from Skyward and try again."],
        )

def _build_column_map(raw_columns):
    lookup = {k.lower().strip(): v for k, v in SKYWARD_COLUMN_MAP.items()}
    mapped, unmapped = {}, []
    for col in raw_columns:
        key = col.lower().strip()
        if key in lookup:
            mapped[col] = lookup[key]
        else:
            unmapped.append(col)
    return mapped, unmapped

def _derive_time_block(dt):
    if pd.isnull(dt):
        return "Unknown"
    try:
        h = pd.Timestamp(dt).hour
        if h < 12: return "Morning"
        elif h < 14: return "Lunch"
        else: return "Afternoon"
    except Exception:
        return "Unknown"

def _clean_grade(val):
    s = str(val).strip()
    return s[:-2] if s.endswith(".0") else s

def _clean_days_removed(val):
    import re
    match = re.search(r"([0-9]+(?:\.[0-9]+)?)", str(val).strip())
    try:
        return float(match.group(1)) if match else 0.0
    except ValueError:
        return 0.0

def run_skyward_ingestion(uploaded_file, campus_name_fallback="Campus"):
    flags, exclusion_notes = [], []
    raw_df = _read_file(uploaded_file)
    rows_uploaded = len(raw_df)

    if rows_uploaded == 0:
        raise SkywardIngestionError(
            reason="File contains no data rows.",
            fix_steps=["Verify export contains discipline records.", "Check date range in Skyward."],
        )

    mapped, unmapped = _build_column_map(list(raw_df.columns))
    if unmapped:
        flags.append(f"Unmapped columns (ignored): {', '.join(unmapped)}")

    df = raw_df.rename(columns=mapped)

    pre_derive = [c for c in REQUIRED_COLUMNS if c != "Time_Block"]
    missing = [c for c in pre_derive if c not in df.columns]
    if missing:
        raise SkywardIngestionError(
            reason=f"Required column(s) not found: {', '.join(missing)}",
            fix_steps=[
                "Verify you are using the Skyward Discipline - Incident Offense Name Actions export.",
                f"Missing: {', '.join(missing)}",
                f"Columns found in file: {', '.join(raw_df.columns.tolist())}",
            ],
        )

    df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
    failures = df["Date"].isna().sum()
    if failures > 0:
        flags.append(f"{failures} rows have unparseable dates.")
    df["Time_Block"] = df["Date"].apply(_derive_time_block)

    if "Grade" in df.columns:
        df["Grade"] = df["Grade"].apply(_clean_grade)
    if "Days_Removed" in df.columns:
        df["Days_Removed"] = df["Days_Removed"].apply(_clean_days_removed)

    rows_before = len(df)
    check_cols = [c for c in REQUIRED_COLUMNS if c in df.columns]
    missing_mask = df[check_cols].isnull().any(axis=1)
    for col in check_cols:
        if df[col].dtype == object:
            missing_mask = missing_mask | (df[col].str.strip() == "")

    rows_excluded = int(missing_mask.sum())
    if rows_excluded > 0:
        exclusion_notes.append(f"{rows_excluded} of {rows_before} rows excluded: missing required fields.")
        df = df[~missing_mask].copy()

    if len(df) == 0:
        raise SkywardIngestionError(
            reason="No valid rows remain after exclusions.",
            fix_steps=["Check that export contains complete records.", "Re-export from Skyward."],
        )

    campus_identifier = campus_name_fallback
    if "Entity" in df.columns and df["Entity"].notna().any():
        campus_identifier = str(df["Entity"].dropna().unique()[0])
    elif "Campus" in df.columns and df["Campus"].notna().any():
        campus_identifier = str(df["Campus"].dropna().unique()[0])

    return SkywardIngestionResult(
        df=df,
        rows_uploaded=rows_uploaded,
        rows_excluded=rows_excluded,
        exclusion_notes=exclusion_notes,
        campus_identifier=campus_identifier,
        mapped_columns=mapped,
        unmapped_columns=unmapped,
        flags=flags,
    )
