"""
Atlas Integration Test Suite — skyward_ingestion.py
Tests the full pipeline: file read → column map → clean → validate → return result.
All tests are deterministic. No random data.
"""
import io
import pytest
import pandas as pd
from skyward_ingestion import run_skyward_ingestion, SkywardIngestionError

class MockFile:
    def __init__(self, buf: bytes, name: str):
        self._buf = io.BytesIO(buf)
        self.name = name
    def read(self, *args):
        return self._buf.read(*args)
    def seek(self, *args):
        return self._buf.seek(*args)
    def tell(self):
        return self._buf.tell()
    def seekable(self):
        return True
    def __iter__(self):
        return iter(self._buf)

def make_csv_file(rows, name="test.csv"):
    df = pd.DataFrame(rows)
    buf = df.to_csv(index=False).encode("utf-8")
    return MockFile(buf, name)

def make_xlsx_file(rows, name="test.xlsx"):
    df = pd.DataFrame(rows)
    buf = io.BytesIO()
    df.to_excel(buf, index=False)
    buf.seek(0)
    return MockFile(buf.read(), name)

VALID_ROW = {
    "Incident Date & Time": "2025-09-10 08:00:00",
    "Student Grade": "09",
    "Offense Description": "L06 - Skipping",
    "Location Description": "Classroom",
    "Action Description": "ISS",
    "Entity": "001 - Sample High School",
    "Days Removed": "3",
    "Race Description": "Hispanic/Latino",
    "Student Gender": "M",
}

def test_csv_file_reads_successfully():
    f = make_csv_file([VALID_ROW])
    result = run_skyward_ingestion(f)
    assert len(result.df) == 1

def test_xlsx_file_reads_successfully():
    f = make_xlsx_file([VALID_ROW])
    result = run_skyward_ingestion(f)
    assert len(result.df) == 1

def test_xls_extension_accepted():
    f = make_xlsx_file([VALID_ROW], name="test.xls")
    result = run_skyward_ingestion(f)
    assert len(result.df) >= 1

def test_unsupported_file_type_raises():
    f = MockFile(b"garbage", name="test.txt")
    with pytest.raises(SkywardIngestionError):
        run_skyward_ingestion(f)

def test_empty_file_raises():
    df = pd.DataFrame(columns=VALID_ROW.keys())
    buf = df.to_csv(index=False).encode("utf-8")
    f = MockFile(buf, "empty.csv")
    with pytest.raises(SkywardIngestionError):
        run_skyward_ingestion(f)

def test_skyward_columns_mapped_correctly():
    f = make_csv_file([VALID_ROW])
    result = run_skyward_ingestion(f)
    expected = {"Date", "Grade", "Incident_Type", "Location", "Response"}
    assert expected.issubset(set(result.df.columns))

def test_unmapped_columns_flagged():
    row = {**VALID_ROW, "Random Unknown Column": "value"}
    f = make_csv_file([row])
    result = run_skyward_ingestion(f)
    assert any("Unmapped" in flag for flag in result.flags)

def test_missing_required_column_raises():
    row = {k: v for k, v in VALID_ROW.items() if k != "Incident Date & Time"}
    f = make_csv_file([row])
    with pytest.raises(SkywardIngestionError):
        run_skyward_ingestion(f)

def test_time_block_derived_morning():
    row = {**VALID_ROW, "Incident Date & Time": "2025-09-10 08:00:00"}
    f = make_csv_file([row])
    result = run_skyward_ingestion(f)
    assert result.df["Time_Block"].iloc[0] == "Morning"

def test_time_block_derived_lunch():
    row = {**VALID_ROW, "Incident Date & Time": "2025-09-10 12:30:00"}
    f = make_csv_file([row])
    result = run_skyward_ingestion(f)
    assert result.df["Time_Block"].iloc[0] == "Lunch"

def test_time_block_derived_afternoon():
    row = {**VALID_ROW, "Incident Date & Time": "2025-09-10 14:00:00"}
    f = make_csv_file([row])
    result = run_skyward_ingestion(f)
    assert result.df["Time_Block"].iloc[0] == "Afternoon"

def test_days_removed_numeric():
    f = make_csv_file([VALID_ROW])
    result = run_skyward_ingestion(f)
    val = result.df["Days_Removed"].iloc[0]
    assert float(val) == 3.0

def test_rows_missing_required_fields_excluded():
    good = VALID_ROW.copy()
    bad = {**VALID_ROW, "Offense Description": ""}
    f = make_csv_file([good, bad])
    result = run_skyward_ingestion(f)
    assert result.rows_excluded == 1
    assert len(result.df) == 1
    assert any("excluded" in note.lower() for note in result.exclusion_notes)

def test_all_rows_excluded_raises():
    bad = {**VALID_ROW, "Offense Description": ""}
    f = make_csv_file([bad])
    with pytest.raises(SkywardIngestionError):
        run_skyward_ingestion(f)

def test_valid_rows_pass_through():
    rows = [VALID_ROW.copy() for _ in range(5)]
    f = make_csv_file(rows)
    result = run_skyward_ingestion(f)
    assert result.rows_excluded == 0
    assert len(result.df) == 5

def test_campus_name_from_entity_column():
    f = make_csv_file([VALID_ROW])
    result = run_skyward_ingestion(f)
    assert "Sample High School" in result.campus_identifier

def test_campus_fallback_used_when_no_entity():
    row = {k: v for k, v in VALID_ROW.items() if k != "Entity"}
    f = make_csv_file([row])
    result = run_skyward_ingestion(f, campus_name_fallback="Fallback Campus")
    assert result.campus_identifier == "Fallback Campus"

def test_default_fallback_is_campus():
    row = {k: v for k, v in VALID_ROW.items() if k != "Entity"}
    f = make_csv_file([row])
    result = run_skyward_ingestion(f)
    assert result.campus_identifier == "Campus"

def test_result_has_required_attributes():
    f = make_csv_file([VALID_ROW])
    result = run_skyward_ingestion(f)
    for attr in ["df", "campus_identifier", "rows_excluded", "exclusion_notes", "flags", "mapped_columns", "unmapped_columns"]:
        assert hasattr(result, attr)

def test_result_df_is_dataframe():
    f = make_csv_file([VALID_ROW])
    result = run_skyward_ingestion(f)
    assert isinstance(result.df, pd.DataFrame)

def test_multiple_rows_all_returned():
    rows = [VALID_ROW.copy() for _ in range(10)]
    f = make_csv_file(rows)
    result = run_skyward_ingestion(f)
    assert len(result.df) == 10
