"""
Atlas Ingestion Test Suite — SKILL.md v1.2 / CONTRACT.md

Every test is labeled with the rule it enforces.
Tests must pass deterministically. No random data.
"""

import os
import tempfile
import pytest
import pandas as pd
from datetime import date

from ingestion import (
    run_ingestion,
    IngestionError,
    IngestionResult,
    MINUTES_PER_DAY,
    JOIN_SUCCESS_THRESHOLD,
    _count_instructional_days,
    _parse_date,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def write_csv(df: pd.DataFrame, suffix: str = ".csv") -> str:
    tmp = tempfile.NamedTemporaryFile(mode="w", suffix=suffix, delete=False)
    df.to_csv(tmp.name, index=False)
    tmp.close()
    return tmp.name


def make_incident_file(rows: list[dict]) -> str:
    return write_csv(pd.DataFrame(rows))


def make_consequence_file(rows: list[dict]) -> str:
    return write_csv(pd.DataFrame(rows))


GOOD_INCIDENTS = [
    {"Incident Number": f"INC{i:03d}", "Incident Date & Time": "2024-09-10", "Building": "Campus A"}
    for i in range(1, 21)
]

GOOD_CONSEQUENCES = [
    {
        "Incident Number": f"INC{i:03d}",
        "Consequence Type": "OSS",
        "Consequence Start Date": "2024-09-11",
        "Consequence End Date": "2024-09-13",
    }
    for i in range(1, 21)
]


# ---------------------------------------------------------------------------
# RULE: Both files required
# ---------------------------------------------------------------------------

class TestBothFilesRequired:
    def test_incident_file_missing_halts(self):
        """SKILL.md: both files required; missing file = halt"""
        con = make_consequence_file(GOOD_CONSEQUENCES)
        try:
            with pytest.raises(IngestionError) as exc_info:
                run_ingestion("/nonexistent/incident.csv", con)
            assert "not found" in str(exc_info.value).lower()
        finally:
            os.unlink(con)

    def test_consequence_file_missing_halts(self):
        inc = make_incident_file(GOOD_INCIDENTS)
        try:
            with pytest.raises(IngestionError) as exc_info:
                run_ingestion(inc, "/nonexistent/consequence.csv")
            assert "not found" in str(exc_info.value).lower()
        finally:
            os.unlink(inc)


# ---------------------------------------------------------------------------
# RULE: Required columns must be present
# ---------------------------------------------------------------------------

class TestRequiredColumns:
    def test_missing_incident_number_in_incident_halts(self):
        """SKILL.md §REQUIRED FIELDS"""
        rows = [{"Incident Date & Time": "2024-09-10", "Building": "Campus A"}]
        inc = make_incident_file(rows)
        con = make_consequence_file(GOOD_CONSEQUENCES)
        try:
            with pytest.raises(IngestionError) as exc_info:
                run_ingestion(inc, con)
            assert "incident_number" in str(exc_info.value)
        finally:
            os.unlink(inc)
            os.unlink(con)

    def test_missing_consequence_type_halts(self):
        rows = [
            {
                "Incident Number": "INC001",
                "Consequence Start Date": "2024-09-11",
                "Consequence End Date": "2024-09-13",
            }
        ]
        inc = make_incident_file(GOOD_INCIDENTS[:5])
        con = make_consequence_file(rows)
        try:
            with pytest.raises(IngestionError) as exc_info:
                run_ingestion(inc, con)
            assert "consequence_type" in str(exc_info.value)
        finally:
            os.unlink(inc)
            os.unlink(con)

    def test_missing_start_date_column_halts(self):
        rows = [
            {
                "Incident Number": "INC001",
                "Consequence Type": "OSS",
                "Consequence End Date": "2024-09-13",
            }
        ]
        inc = make_incident_file(GOOD_INCIDENTS[:1])
        con = make_consequence_file(rows)
        try:
            with pytest.raises(IngestionError):
                run_ingestion(inc, con)
        finally:
            os.unlink(inc)
            os.unlink(con)


# ---------------------------------------------------------------------------
# RULE: Header alias resolution
# ---------------------------------------------------------------------------

class TestHeaderAliasResolution:
    def test_known_variant_headers_resolve(self):
        """SKILL.md: Atlas resolves known header variants deterministically"""
        inc = make_incident_file(GOOD_INCIDENTS)  # already uses "Incident Number" etc.
        con = make_consequence_file(GOOD_CONSEQUENCES)
        try:
            result = run_ingestion(inc, con)
            assert isinstance(result, IngestionResult)
            assert len(result.data) > 0
        finally:
            os.unlink(inc)
            os.unlink(con)

    def test_alias_map_is_logged(self):
        """SKILL.md §11: alias map must be logged in report"""
        inc = make_incident_file(GOOD_INCIDENTS)
        con = make_consequence_file(GOOD_CONSEQUENCES)
        try:
            result = run_ingestion(inc, con)
            report_text = result.report.as_text()
            assert "COLUMN ALIAS MAP" in report_text
        finally:
            os.unlink(inc)
            os.unlink(con)


# ---------------------------------------------------------------------------
# RULE: Consequence type enum enforcement
# ---------------------------------------------------------------------------

class TestConsequenceTypeEnum:
    def test_invalid_consequence_type_excluded_not_halted(self):
        """SKILL.md: invalid enum excluded and logged; does not halt unless join drops below 95%"""
        # 20 matching incidents, 19 valid + 1 invalid consequence
        valid_cons = [
            {
                "Incident Number": f"INC{i:03d}",
                "Consequence Type": "ISS",
                "Consequence Start Date": "2024-09-11",
                "Consequence End Date": "2024-09-11",
            }
            for i in range(1, 20)
        ]
        invalid_con = {
            "Incident Number": "INC020",
            "Consequence Type": "DETENTION",  # not in enum
            "Consequence Start Date": "2024-09-11",
            "Consequence End Date": "2024-09-11",
        }
        inc = make_incident_file(GOOD_INCIDENTS)
        con = make_consequence_file(valid_cons + [invalid_con])
        try:
            # 19/20 = 95% → should pass
            result = run_ingestion(inc, con)
            exclusion_reasons = [ex.reason for ex in result.report.excluded_rows]
            assert any("consequence_type" in r.lower() for r in exclusion_reasons)
        finally:
            os.unlink(inc)
            os.unlink(con)

    def test_all_six_approved_types_accepted(self):
        """CONTRACT.md: all six approved types must be accepted"""
        types = ["ISS", "OSS", "DAEP", "JJAEP", "EXPULSION", "LOCAL_ONLY"]
        incidents = [
            {"Incident Number": f"INC{i:03d}", "Incident Date & Time": "2024-09-10", "Building": "Campus A"}
            for i in range(1, len(types) + 1)
        ]
        consequences = [
            {
                "Incident Number": f"INC{i:03d}",
                "Consequence Type": t,
                "Consequence Start Date": "2024-09-11",
                "Consequence End Date": "2024-09-11",
            }
            for i, t in enumerate(types, 1)
        ]
        inc = make_incident_file(incidents)
        con = make_consequence_file(consequences)
        try:
            result = run_ingestion(inc, con)
            assert len(result.data) == len(types)
        finally:
            os.unlink(inc)
            os.unlink(con)

    def test_case_insensitive_enum_match(self):
        """CONTRACT.md: consequence types are case-insensitive"""
        incidents = [
            {"Incident Number": "INC001", "Incident Date & Time": "2024-09-10", "Building": "Campus A"}
        ]
        consequences = [
            {
                "Incident Number": "INC001",
                "Consequence Type": "oss",  # lowercase
                "Consequence Start Date": "2024-09-11",
                "Consequence End Date": "2024-09-11",
            }
        ]
        inc = make_incident_file(incidents)
        con = make_consequence_file(consequences)
        try:
            result = run_ingestion(inc, con)
            assert len(result.data) == 1
        finally:
            os.unlink(inc)
            os.unlink(con)


# ---------------------------------------------------------------------------
# RULE: Join threshold enforcement
# ---------------------------------------------------------------------------

class TestJoinThreshold:
    def test_join_below_95_halts(self):
        """SKILL.md §JOIN COMPLETENESS: join_success < 0.95 → halt"""
        # 20 incidents, only 18 have consequences → 90% → halt
        incidents = GOOD_INCIDENTS.copy()
        consequences = GOOD_CONSEQUENCES[:18]
        inc = make_incident_file(incidents)
        con = make_consequence_file(consequences)
        try:
            with pytest.raises(IngestionError) as exc_info:
                run_ingestion(inc, con)
            err = exc_info.value
            assert err.join_success_rate is not None
            assert err.join_success_rate < JOIN_SUCCESS_THRESHOLD
        finally:
            os.unlink(inc)
            os.unlink(con)

    def test_join_at_exactly_95_passes(self):
        """SKILL.md: join_success == 0.95 is passing"""
        # 20 incidents, 19 matched = 95%
        incidents = GOOD_INCIDENTS.copy()
        consequences = GOOD_CONSEQUENCES[:19]
        inc = make_incident_file(incidents)
        con = make_consequence_file(consequences)
        try:
            result = run_ingestion(inc, con)
            assert result.report.join_success_rate >= JOIN_SUCCESS_THRESHOLD
        finally:
            os.unlink(inc)
            os.unlink(con)

    def test_join_at_100_passes(self):
        inc = make_incident_file(GOOD_INCIDENTS)
        con = make_consequence_file(GOOD_CONSEQUENCES)
        try:
            result = run_ingestion(inc, con)
            assert result.report.join_success_rate == 1.0
        finally:
            os.unlink(inc)
            os.unlink(con)

    def test_no_fallback_join_attempted(self):
        """SKILL.md: no fallback joins. Mismatched IDs must lower success, not match."""
        incidents = [
            {"Incident Number": "INC001", "Incident Date & Time": "2024-09-10", "Building": "Campus A"}
        ]
        # Consequence has same student, same date — different incident number
        consequences = [
            {
                "Incident Number": "XYZ999",  # different key
                "Consequence Type": "OSS",
                "Consequence Start Date": "2024-09-10",
                "Consequence End Date": "2024-09-10",
            }
        ]
        inc = make_incident_file(incidents)
        con = make_consequence_file(consequences)
        try:
            with pytest.raises(IngestionError) as exc_info:
                run_ingestion(inc, con)
            # Should halt — 0% join success, not 100% via fallback
            assert exc_info.value.join_success_rate == 0.0
        finally:
            os.unlink(inc)
            os.unlink(con)


# ---------------------------------------------------------------------------
# RULE: Instructional minutes calculation
# ---------------------------------------------------------------------------

class TestInstructionalMinutes:
    def test_explicit_minutes_take_precedence(self):
        """SKILL.md: explicit minutes used when present"""
        incidents = [
            {"Incident Number": "INC001", "Incident Date & Time": "2024-09-10", "Building": "Campus A"}
        ]
        consequences = [
            {
                "Incident Number": "INC001",
                "Consequence Type": "OSS",
                "Consequence Start Date": "2024-09-11",
                "Consequence End Date": "2024-09-13",
                "Instructional Minutes Lost": "720",  # explicit
            }
        ]
        inc = make_incident_file(incidents)
        con = make_consequence_file(consequences)
        try:
            result = run_ingestion(inc, con)
            assert result.report.minutes_explicit_count == 1
            assert result.report.minutes_date_derived_count == 0
            assert result.data.iloc[0]["instructional_minutes_computed"] == 720
        finally:
            os.unlink(inc)
            os.unlink(con)

    def test_date_derived_when_no_explicit_minutes(self):
        """SKILL.md: date-derived at 480/day when no explicit minutes column"""
        incidents = [
            {"Incident Number": "INC001", "Incident Date & Time": "2024-09-10", "Building": "Campus A"}
        ]
        # Mon 2024-09-09 to Wed 2024-09-11 = 3 weekdays (inclusive)
        consequences = [
            {
                "Incident Number": "INC001",
                "Consequence Type": "OSS",
                "Consequence Start Date": "2024-09-09",
                "Consequence End Date": "2024-09-11",
            }
        ]
        inc = make_incident_file(incidents)
        con = make_consequence_file(consequences)
        try:
            result = run_ingestion(inc, con)
            expected = 3 * 480
            assert result.data.iloc[0]["instructional_minutes_computed"] == expected
        finally:
            os.unlink(inc)
            os.unlink(con)

    def test_single_day_removal_counts_480_minutes(self):
        """CONTRACT.md: single-date removal = 1 full day (480 min). No partial day inference."""
        incidents = [
            {"Incident Number": "INC001", "Incident Date & Time": "2024-09-10", "Building": "Campus A"}
        ]
        consequences = [
            {
                "Incident Number": "INC001",
                "Consequence Type": "ISS",
                "Consequence Start Date": "2024-09-10",
                "Consequence End Date": "2024-09-10",
            }
        ]
        inc = make_incident_file(incidents)
        con = make_consequence_file(consequences)
        try:
            result = run_ingestion(inc, con)
            assert result.data.iloc[0]["instructional_minutes_computed"] == 480
        finally:
            os.unlink(inc)
            os.unlink(con)

    def test_weekends_excluded_from_day_count(self):
        """CONTRACT.md: weekends excluded"""
        incidents = [
            {"Incident Number": "INC001", "Incident Date & Time": "2024-09-10", "Building": "Campus A"}
        ]
        # Fri 2024-09-13 to Mon 2024-09-16: Fri + Mon = 2 weekdays (Sat/Sun excluded)
        consequences = [
            {
                "Incident Number": "INC001",
                "Consequence Type": "OSS",
                "Consequence Start Date": "2024-09-13",
                "Consequence End Date": "2024-09-16",
            }
        ]
        inc = make_incident_file(incidents)
        con = make_consequence_file(consequences)
        try:
            result = run_ingestion(inc, con)
            assert result.data.iloc[0]["instructional_minutes_computed"] == 2 * 480
        finally:
            os.unlink(inc)
            os.unlink(con)

    def test_counting_is_inclusive(self):
        """CONTRACT.md: inclusive date counting"""
        # Mon–Fri = 5 days inclusive
        assert _count_instructional_days(date(2024, 9, 9), date(2024, 9, 13)) == 5

    def test_assumptions_logged_in_report(self):
        """SKILL.md §11: minutes assumptions must appear in report"""
        inc = make_incident_file(GOOD_INCIDENTS)
        con = make_consequence_file(GOOD_CONSEQUENCES)
        try:
            result = run_ingestion(inc, con)
            report_text = result.report.as_text()
            assert "480" in report_text
            assert "weekends" in report_text.lower()
            assert "inclusive" in report_text.lower()
        finally:
            os.unlink(inc)
            os.unlink(con)


# ---------------------------------------------------------------------------
# RULE: Determinism — same input → same output
# ---------------------------------------------------------------------------

class TestDeterminism:
    def test_identical_inputs_produce_identical_output(self):
        """SKILL.md §DETERMINISM: same input → same numbers, every run"""
        inc = make_incident_file(GOOD_INCIDENTS)
        con = make_consequence_file(GOOD_CONSEQUENCES)
        try:
            r1 = run_ingestion(inc, con)
            r2 = run_ingestion(inc, con)
            assert r1.report.join_success_rate == r2.report.join_success_rate
            assert r1.report.matched_incidents == r2.report.matched_incidents
            assert r1.report.minutes_date_derived_count == r2.report.minutes_date_derived_count
            # Row-level numeric output must match
            pd.testing.assert_frame_equal(
                r1.data[["incident_number", "instructional_minutes_computed"]].reset_index(drop=True),
                r2.data[["incident_number", "instructional_minutes_computed"]].reset_index(drop=True),
            )
        finally:
            os.unlink(inc)
            os.unlink(con)


# ---------------------------------------------------------------------------
# RULE: Data Readiness Report — required elements
# ---------------------------------------------------------------------------

class TestDataReadinessReport:
    def test_report_contains_all_required_elements(self):
        """SKILL.md §10: Data Readiness Report must include all listed elements"""
        inc = make_incident_file(GOOD_INCIDENTS)
        con = make_consequence_file(GOOD_CONSEQUENCES)
        try:
            result = run_ingestion(inc, con)
            r = result.report
            assert r.timestamp
            assert r.incident_file
            assert r.consequence_file
            assert r.incident_row_count == len(GOOD_INCIDENTS)
            assert r.consequence_row_count == len(GOOD_CONSEQUENCES)
            assert 0.0 <= r.join_success_rate <= 1.0
            assert isinstance(r.excluded_rows, list)
            assert isinstance(r.minutes_assumptions, dict)
            assert isinstance(r.alias_map, dict)
            assert isinstance(r.flags, list)
        finally:
            os.unlink(inc)
            os.unlink(con)

    def test_no_suppressed_flags(self):
        """SKILL.md §11: all flags surfaced.
        Uses 20 incidents: 19 valid consequences + 1 invalid type.
        19/20 = 95% → passes join threshold; exclusion flag must appear in report.
        """
        incidents = GOOD_INCIDENTS  # 20 rows
        consequences = [
            {
                "Incident Number": f"INC{i:03d}",
                "Consequence Type": "ISS",
                "Consequence Start Date": "2024-09-11",
                "Consequence End Date": "2024-09-11",
            }
            for i in range(1, 20)  # INC001–INC019 valid
        ] + [
            {
                "Incident Number": "INC020",
                "Consequence Type": "LUNCH_DETENTION",  # invalid enum
                "Consequence Start Date": "2024-09-11",
                "Consequence End Date": "2024-09-11",
            }
        ]
        inc = make_incident_file(incidents)
        con = make_consequence_file(consequences)
        try:
            result = run_ingestion(inc, con)
            # Flag must appear in report text
            report_text = result.report.as_text()
            assert len(result.report.flags) > 0
            for flag in result.report.flags:
                assert flag in report_text
        finally:
            os.unlink(inc)
            os.unlink(con)


# ---------------------------------------------------------------------------
# RULE: Date validation
# ---------------------------------------------------------------------------

class TestDateValidation:
    def test_start_after_end_row_excluded(self):
        """SKILL.md: start_date > end_date → exclude row and log"""
        incidents = [
            {"Incident Number": "INC001", "Incident Date & Time": "2024-09-10", "Building": "Campus A"},
            {"Incident Number": "INC002", "Incident Date & Time": "2024-09-10", "Building": "Campus A"},
        ]
        consequences = [
            {
                "Incident Number": "INC001",
                "Consequence Type": "OSS",
                "Consequence Start Date": "2024-09-15",
                "Consequence End Date": "2024-09-10",  # start > end
            },
            {
                "Incident Number": "INC002",
                "Consequence Type": "OSS",
                "Consequence Start Date": "2024-09-10",
                "Consequence End Date": "2024-09-12",
            },
        ]
        inc = make_incident_file(incidents)
        con = make_consequence_file(consequences)
        try:
            # 1 valid of 2 incidents = 50% → halts
            with pytest.raises(IngestionError) as exc_info:
                run_ingestion(inc, con)
            assert exc_info.value.join_success_rate is not None
        finally:
            os.unlink(inc)
            os.unlink(con)


# ---------------------------------------------------------------------------
# RULE: Mechanical normalization logged
# ---------------------------------------------------------------------------

class TestMechanicalNormalization:
    def test_bom_stripped_and_logged(self):
        """SKILL.md: BOM removal is mechanical, logged, reversible"""
        # Write a file with BOM
        rows = [
            {"\ufeffIncident Number": "INC001", "Incident Date & Time": "2024-09-10", "Building": "Campus A"}
        ]
        # Write manually to preserve BOM in header
        import tempfile
        tmp = tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False, encoding="utf-8-sig")
        tmp.write("Incident Number,Incident Date & Time,Building\n")
        tmp.write("INC001,2024-09-10,Campus A\n")
        tmp.close()

        cons_rows = [
            {
                "Incident Number": "INC001",
                "Consequence Type": "OSS",
                "Consequence Start Date": "2024-09-10",
                "Consequence End Date": "2024-09-10",
            }
        ]
        con = make_consequence_file(cons_rows)
        try:
            result = run_ingestion(tmp.name, con)
            # Should succeed — BOM stripped
            assert len(result.data) == 1
        finally:
            os.unlink(tmp.name)
            os.unlink(con)


# ---------------------------------------------------------------------------
# RULE: _count_instructional_days utility
# ---------------------------------------------------------------------------

class TestCountInstructionalDays:
    def test_monday_only(self):
        assert _count_instructional_days(date(2024, 9, 9), date(2024, 9, 9)) == 1

    def test_saturday_only_returns_zero(self):
        assert _count_instructional_days(date(2024, 9, 14), date(2024, 9, 14)) == 0

    def test_full_week_mon_fri(self):
        assert _count_instructional_days(date(2024, 9, 9), date(2024, 9, 13)) == 5

    def test_week_with_weekend_included(self):
        # Mon–Sun
        assert _count_instructional_days(date(2024, 9, 9), date(2024, 9, 15)) == 5

    def test_start_equals_end_weekend(self):
        assert _count_instructional_days(date(2024, 9, 14), date(2024, 9, 14)) == 0

    def test_start_greater_than_end_returns_zero(self):
        assert _count_instructional_days(date(2024, 9, 13), date(2024, 9, 9)) == 0

