"""
Atlas Column Mapper Test Suite — Phase 1

Tests cover:
- Every SIS system (Skyward, PowerSchool, DeansList, Infinite Campus, TEAMS)
- Case-insensitive matching
- Whitespace stripping
- Unmatched columns returned correctly
- Determinism (same input, same output)
- No column silently dropped
- No inference (exact match only)
"""

import pytest
import pandas as pd

from column_mapper import (
    resolve_columns,
    get_unmatched_columns,
    NORMALIZED_FIELDS,
    _ALIAS_LOOKUP,
    _SKYWARD_VARIANTS,
    _POWERSCHOOL_VARIANTS,
    _DEANSLIST_VARIANTS,
    _INFINITE_CAMPUS_VARIANTS,
    _TEAMS_VARIANTS,
    _GENERIC_VARIANTS,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_df(columns: list[str]) -> pd.DataFrame:
    """Create a single-row DataFrame with the given column names."""
    return pd.DataFrame([{col: "dummy" for col in columns}])


# ---------------------------------------------------------------------------
# Library integrity
# ---------------------------------------------------------------------------

class TestLibraryIntegrity:
    def test_alias_lookup_is_not_empty(self):
        assert len(_ALIAS_LOOKUP) > 0

    def test_all_values_are_normalized_fields(self):
        """Every entry in the combined lookup must map to a known normalized field."""
        for variant, target in _ALIAS_LOOKUP.items():
            assert target in NORMALIZED_FIELDS, (
                f"Variant '{variant}' maps to '{target}' which is not a recognized "
                f"normalized field. Valid fields: {sorted(NORMALIZED_FIELDS)}"
            )

    def test_all_lookup_keys_are_lowercase_stripped(self):
        """All keys in the combined lookup must already be normalized."""
        for key in _ALIAS_LOOKUP:
            assert key == key.strip().lower(), (
                f"Lookup key '{key}' is not normalized (should be '{key.strip().lower()}')"
            )

    def test_no_conflict_between_sis_sections(self):
        """
        Building the lookup at import time would have raised ValueError on conflict.
        Importing the module without error confirms no conflicts exist.
        """
        # If we got here, _build_alias_lookup() completed without conflict.
        assert _ALIAS_LOOKUP is not None


# ---------------------------------------------------------------------------
# Skyward
# ---------------------------------------------------------------------------

class TestSkywardVariants:
    def test_incident_number_skyward(self):
        df = make_df(["Incident Number"])
        result = resolve_columns(df, "incident")
        assert result["Incident Number"] == "incident_number"

    def test_incident_nbr_skyward(self):
        """Skyward uses 'Nbr' abbreviation."""
        df = make_df(["Incident Nbr"])
        result = resolve_columns(df, "incident")
        assert result["Incident Nbr"] == "incident_number"

    def test_incident_nbr_underscore_skyward(self):
        df = make_df(["Incident_Nbr"])
        result = resolve_columns(df, "incident")
        assert result["Incident_Nbr"] == "incident_number"

    def test_incident_date_and_time_skyward(self):
        df = make_df(["Incident Date & Time"])
        result = resolve_columns(df, "incident")
        assert result["Incident Date & Time"] == "incident_date"

    def test_building_skyward(self):
        """Skyward uses 'Building' for campus."""
        df = make_df(["Building"])
        result = resolve_columns(df, "incident")
        assert result["Building"] == "campus"

    def test_entity_code_skyward(self):
        """Skyward uses 'Entity Code' as the campus identifier."""
        df = make_df(["Entity Code"])
        result = resolve_columns(df, "incident")
        assert result["Entity Code"] == "campus"

    def test_entity_code_underscore_skyward(self):
        df = make_df(["Entity_Code"])
        result = resolve_columns(df, "incident")
        assert result["Entity_Code"] == "campus"

    def test_begin_date_skyward(self):
        """Skyward uses 'Begin Date' for consequence start."""
        df = make_df(["Begin Date"])
        result = resolve_columns(df, "consequence")
        assert result["Begin Date"] == "consequence_start_date"

    def test_action_taken_skyward(self):
        """Skyward 'Action Taken' maps to response (initial staff action)."""
        df = make_df(["Action Taken"])
        result = resolve_columns(df, "incident")
        assert result["Action Taken"] == "response"

    def test_action_type_skyward(self):
        """Skyward 'Action Type' maps to consequence_type."""
        df = make_df(["Action Type"])
        result = resolve_columns(df, "consequence")
        assert result["Action Type"] == "consequence_type"

    def test_nbr_days_skyward(self):
        """Skyward 'Nbr Days' maps to days_removed."""
        df = make_df(["Nbr Days"])
        result = resolve_columns(df, "consequence")
        assert result["Nbr Days"] == "days_removed"

    def test_grade_level_skyward(self):
        df = make_df(["Grade Level"])
        result = resolve_columns(df, "incident")
        assert result["Grade Level"] == "grade"

    def test_behavior_type_skyward(self):
        df = make_df(["Behavior Type"])
        result = resolve_columns(df, "incident")
        assert result["Behavior Type"] == "incident_type"

    def test_race_ethnicity_skyward(self):
        df = make_df(["Race/Ethnicity"])
        result = resolve_columns(df, "incident")
        assert result["Race/Ethnicity"] == "race"

    def test_special_education_skyward(self):
        df = make_df(["Special Education"])
        result = resolve_columns(df, "incident")
        assert result["Special Education"] == "special_population"

    def test_full_skyward_incident_set(self):
        """Simulate a typical Skyward incident export header row."""
        columns = [
            "Incident Number",
            "Incident Date & Time",
            "Building",
            "Grade Level",
            "Incident Type",
            "Location",
            "Class Period",
            "Action Taken",
            "Race/Ethnicity",
            "Gender",
            "Special Education",
        ]
        df = make_df(columns)
        result = resolve_columns(df, "incident")
        assert result["Incident Number"] == "incident_number"
        assert result["Incident Date & Time"] == "incident_date"
        assert result["Building"] == "campus"
        assert result["Grade Level"] == "grade"
        assert result["Incident Type"] == "incident_type"
        assert result["Location"] == "location"
        assert result["Class Period"] == "time_block"
        assert result["Action Taken"] == "response"
        assert result["Race/Ethnicity"] == "race"
        assert result["Gender"] == "gender"
        assert result["Special Education"] == "special_population"

    def test_full_skyward_consequence_set(self):
        """Simulate a typical Skyward consequence export header row."""
        columns = [
            "Incident Number",
            "Consequence Type",
            "Begin Date",
            "End Date",
            "Days Removed",
            "Instructional Minutes Lost",
        ]
        df = make_df(columns)
        result = resolve_columns(df, "consequence")
        assert result["Incident Number"] == "incident_number"
        assert result["Consequence Type"] == "consequence_type"
        assert result["Begin Date"] == "consequence_start_date"
        assert result["End Date"] == "consequence_end_date"
        assert result["Days Removed"] == "days_removed"
        assert result["Instructional Minutes Lost"] == "instructional_minutes"


# ---------------------------------------------------------------------------
# PowerSchool
# ---------------------------------------------------------------------------

class TestPowerSchoolVariants:
    def test_offense_id_powerschool(self):
        """PowerSchool uses 'Offense_ID' for incident number."""
        df = make_df(["Offense_ID"])
        result = resolve_columns(df, "incident")
        assert result["Offense_ID"] == "incident_number"

    def test_offense_id_space_powerschool(self):
        df = make_df(["Offense ID"])
        result = resolve_columns(df, "incident")
        assert result["Offense ID"] == "incident_number"

    def test_offense_number_powerschool(self):
        df = make_df(["Offense_Number"])
        result = resolve_columns(df, "incident")
        assert result["Offense_Number"] == "incident_number"

    def test_offense_date_powerschool(self):
        """PowerSchool uses 'Offense_Date' for incident date."""
        df = make_df(["Offense_Date"])
        result = resolve_columns(df, "incident")
        assert result["Offense_Date"] == "incident_date"

    def test_offense_date_space_powerschool(self):
        df = make_df(["Offense Date"])
        result = resolve_columns(df, "incident")
        assert result["Offense Date"] == "incident_date"

    def test_school_name_powerschool(self):
        df = make_df(["School_Name"])
        result = resolve_columns(df, "incident")
        assert result["School_Name"] == "campus"

    def test_offense_type_powerschool(self):
        df = make_df(["Offense_Type"])
        result = resolve_columns(df, "incident")
        assert result["Offense_Type"] == "incident_type"

    def test_offense_location_powerschool(self):
        df = make_df(["Offense_Location"])
        result = resolve_columns(df, "incident")
        assert result["Offense_Location"] == "location"

    def test_action_start_date_camel_powerschool(self):
        """PowerSchool camelCase 'ActionStartDate'."""
        df = make_df(["ActionStartDate"])
        result = resolve_columns(df, "consequence")
        assert result["ActionStartDate"] == "consequence_start_date"

    def test_action_end_date_camel_powerschool(self):
        """PowerSchool camelCase 'ActionEndDate'."""
        df = make_df(["ActionEndDate"])
        result = resolve_columns(df, "consequence")
        assert result["ActionEndDate"] == "consequence_end_date"

    def test_days_assigned_powerschool(self):
        """PowerSchool uses 'Days_Assigned' for days removed."""
        df = make_df(["Days_Assigned"])
        result = resolve_columns(df, "consequence")
        assert result["Days_Assigned"] == "days_removed"

    def test_days_assigned_camel_powerschool(self):
        df = make_df(["DaysAssigned"])
        result = resolve_columns(df, "consequence")
        assert result["DaysAssigned"] == "days_removed"

    def test_ell_powerschool(self):
        df = make_df(["ELL"])
        result = resolve_columns(df, "incident")
        assert result["ELL"] == "special_population"

    def test_iep_powerschool(self):
        df = make_df(["IEP"])
        result = resolve_columns(df, "incident")
        assert result["IEP"] == "special_population"

    def test_full_powerschool_export(self):
        """Simulate a typical PowerSchool offense export."""
        columns = [
            "Offense_ID",
            "Offense_Date",
            "School_Name",
            "Grade_Level",
            "Offense_Type",
            "Offense_Location",
            "Class_Period",
            "Action_Type",
            "Consequence_Start_Date",
            "Consequence_End_Date",
            "Days_Assigned",
            "Race",
            "Gender",
            "IEP",
        ]
        df = make_df(columns)
        result = resolve_columns(df, "incident")
        assert result["Offense_ID"] == "incident_number"
        assert result["Offense_Date"] == "incident_date"
        assert result["School_Name"] == "campus"
        assert result["Grade_Level"] == "grade"
        assert result["Offense_Type"] == "incident_type"
        assert result["Offense_Location"] == "location"
        assert result["Class_Period"] == "time_block"
        assert result["Action_Type"] == "consequence_type"
        assert result["Consequence_Start_Date"] == "consequence_start_date"
        assert result["Consequence_End_Date"] == "consequence_end_date"
        assert result["Days_Assigned"] == "days_removed"
        assert result["Race"] == "race"
        assert result["Gender"] == "gender"
        assert result["IEP"] == "special_population"


# ---------------------------------------------------------------------------
# DeansList
# ---------------------------------------------------------------------------

class TestDeansListVariants:
    def test_incident_id_deanslist(self):
        """DeansList uses 'Incident ID' for incident number."""
        df = make_df(["Incident ID"])
        result = resolve_columns(df, "incident")
        assert result["Incident ID"] == "incident_number"

    def test_infraction_deanslist(self):
        """DeansList-specific term for incident type."""
        df = make_df(["Infraction"])
        result = resolve_columns(df, "incident")
        assert result["Infraction"] == "incident_type"

    def test_infraction_type_deanslist(self):
        df = make_df(["Infraction Type"])
        result = resolve_columns(df, "incident")
        assert result["Infraction Type"] == "incident_type"

    def test_incident_category_deanslist(self):
        """DeansList 'Incident Category' maps to incident_type."""
        df = make_df(["Incident Category"])
        result = resolve_columns(df, "incident")
        assert result["Incident Category"] == "incident_type"

    def test_consequence_deanslist(self):
        """DeansList bare 'Consequence' column maps to consequence_type."""
        df = make_df(["Consequence"])
        result = resolve_columns(df, "consequence")
        assert result["Consequence"] == "consequence_type"

    def test_sped_deanslist(self):
        """DeansList uses 'SPED' abbreviation."""
        df = make_df(["SPED"])
        result = resolve_columns(df, "incident")
        assert result["SPED"] == "special_population"

    def test_sanction_type_deanslist(self):
        df = make_df(["Sanction Type"])
        result = resolve_columns(df, "consequence")
        assert result["Sanction Type"] == "consequence_type"

    def test_full_deanslist_export(self):
        """Simulate a typical DeansList export."""
        columns = [
            "Incident ID",
            "Incident Date",
            "School",
            "Grade",
            "Infraction",
            "Location",
            "Period",
            "Action Taken",
            "Consequence",
            "Start Date",
            "End Date",
            "Race/Ethnicity",
            "Gender",
            "SPED",
        ]
        df = make_df(columns)
        result = resolve_columns(df, "incident")
        assert result["Incident ID"] == "incident_number"
        assert result["Incident Date"] == "incident_date"
        assert result["School"] == "campus"
        assert result["Grade"] == "grade"
        assert result["Infraction"] == "incident_type"
        assert result["Location"] == "location"
        assert result["Period"] == "time_block"
        assert result["Action Taken"] == "response"
        assert result["Consequence"] == "consequence_type"
        assert result["Start Date"] == "consequence_start_date"
        assert result["End Date"] == "consequence_end_date"
        assert result["Race/Ethnicity"] == "race"
        assert result["Gender"] == "gender"
        assert result["SPED"] == "special_population"


# ---------------------------------------------------------------------------
# Infinite Campus
# ---------------------------------------------------------------------------

class TestInfiniteCampusVariants:
    def test_event_id_infinite_campus(self):
        """Infinite Campus uses 'Event_ID' for incident number."""
        df = make_df(["Event_ID"])
        result = resolve_columns(df, "incident")
        assert result["Event_ID"] == "incident_number"

    def test_event_id_space_infinite_campus(self):
        df = make_df(["Event ID"])
        result = resolve_columns(df, "incident")
        assert result["Event ID"] == "incident_number"

    def test_eventid_nospace_infinite_campus(self):
        df = make_df(["EventID"])
        result = resolve_columns(df, "incident")
        assert result["EventID"] == "incident_number"

    def test_calendar_name_infinite_campus(self):
        """Infinite Campus uses 'Calendar Name' for campus."""
        df = make_df(["Calendar Name"])
        result = resolve_columns(df, "incident")
        assert result["Calendar Name"] == "campus"

    def test_calendar_name_underscore_infinite_campus(self):
        df = make_df(["Calendar_Name"])
        result = resolve_columns(df, "incident")
        assert result["Calendar_Name"] == "campus"

    def test_event_type_infinite_campus(self):
        """Infinite Campus uses 'Event Type' for incident type."""
        df = make_df(["Event Type"])
        result = resolve_columns(df, "incident")
        assert result["Event Type"] == "incident_type"

    def test_event_type_underscore_infinite_campus(self):
        df = make_df(["Event_Type"])
        result = resolve_columns(df, "incident")
        assert result["Event_Type"] == "incident_type"

    def test_event_location_infinite_campus(self):
        df = make_df(["Event Location"])
        result = resolve_columns(df, "incident")
        assert result["Event Location"] == "location"

    def test_consequence_start_short_infinite_campus(self):
        """Infinite Campus uses 'Consequence Start' (short form)."""
        df = make_df(["Consequence Start"])
        result = resolve_columns(df, "consequence")
        assert result["Consequence Start"] == "consequence_start_date"

    def test_consequence_end_short_infinite_campus(self):
        """Infinite Campus uses 'Consequence End' (short form)."""
        df = make_df(["Consequence End"])
        result = resolve_columns(df, "consequence")
        assert result["Consequence End"] == "consequence_end_date"

    def test_resolution_type_infinite_campus(self):
        """Infinite Campus uses 'Resolution Type' for consequence type."""
        df = make_df(["Resolution Type"])
        result = resolve_columns(df, "consequence")
        assert result["Resolution Type"] == "consequence_type"

    def test_resolution_bare_infinite_campus(self):
        """Infinite Campus bare 'Resolution' maps to consequence_type."""
        df = make_df(["Resolution"])
        result = resolve_columns(df, "consequence")
        assert result["Resolution"] == "consequence_type"

    def test_disability_status_infinite_campus(self):
        df = make_df(["Disability Status"])
        result = resolve_columns(df, "incident")
        assert result["Disability Status"] == "special_population"

    def test_full_infinite_campus_export(self):
        """Simulate a typical Infinite Campus export."""
        columns = [
            "Event ID",
            "Incident Date",
            "Calendar Name",
            "Grade Level",
            "Event Type",
            "Event Location",
            "Period",
            "Resolution Type",
            "Consequence Start",
            "Consequence End",
            "Days Removed",
            "Instructional Minutes",
            "Race",
            "Gender",
            "IEP",
        ]
        df = make_df(columns)
        result = resolve_columns(df, "incident")
        assert result["Event ID"] == "incident_number"
        assert result["Incident Date"] == "incident_date"
        assert result["Calendar Name"] == "campus"
        assert result["Grade Level"] == "grade"
        assert result["Event Type"] == "incident_type"
        assert result["Event Location"] == "location"
        assert result["Period"] == "time_block"
        assert result["Resolution Type"] == "consequence_type"
        assert result["Consequence Start"] == "consequence_start_date"
        assert result["Consequence End"] == "consequence_end_date"
        assert result["Days Removed"] == "days_removed"
        assert result["Instructional Minutes"] == "instructional_minutes"
        assert result["Race"] == "race"
        assert result["Gender"] == "gender"
        assert result["IEP"] == "special_population"


# ---------------------------------------------------------------------------
# TEAMS (Texas SIS)
# ---------------------------------------------------------------------------

class TestTEAMSVariants:
    def test_referral_number_teams(self):
        """TEAMS uses 'Referral Number' for incident number."""
        df = make_df(["Referral Number"])
        result = resolve_columns(df, "incident")
        assert result["Referral Number"] == "incident_number"

    def test_referral_number_underscore_teams(self):
        df = make_df(["Referral_Number"])
        result = resolve_columns(df, "incident")
        assert result["Referral_Number"] == "incident_number"

    def test_referral_hash_teams(self):
        """TEAMS uses 'Referral #' shorthand."""
        df = make_df(["Referral #"])
        result = resolve_columns(df, "incident")
        assert result["Referral #"] == "incident_number"

    def test_referral_id_teams(self):
        df = make_df(["Referral ID"])
        result = resolve_columns(df, "incident")
        assert result["Referral ID"] == "incident_number"

    def test_referral_date_teams(self):
        """TEAMS uses 'Referral Date' for incident date."""
        df = make_df(["Referral Date"])
        result = resolve_columns(df, "incident")
        assert result["Referral Date"] == "incident_date"

    def test_referral_date_underscore_teams(self):
        df = make_df(["Referral_Date"])
        result = resolve_columns(df, "incident")
        assert result["Referral_Date"] == "incident_date"

    def test_campus_id_teams(self):
        """TEAMS uses numeric Campus ID."""
        df = make_df(["Campus ID"])
        result = resolve_columns(df, "incident")
        assert result["Campus ID"] == "campus"

    def test_campus_number_teams(self):
        df = make_df(["Campus Number"])
        result = resolve_columns(df, "incident")
        assert result["Campus Number"] == "campus"

    def test_conduct_code_teams(self):
        """TEAMS uses 'Conduct Code' for incident type."""
        df = make_df(["Conduct Code"])
        result = resolve_columns(df, "incident")
        assert result["Conduct Code"] == "incident_type"

    def test_conduct_code_underscore_teams(self):
        df = make_df(["Conduct_Code"])
        result = resolve_columns(df, "incident")
        assert result["Conduct_Code"] == "incident_type"

    def test_offense_code_teams(self):
        """TEAMS uses 'Offense Code' for incident type."""
        df = make_df(["Offense Code"])
        result = resolve_columns(df, "incident")
        assert result["Offense Code"] == "incident_type"

    def test_disciplinary_action_teams(self):
        """TEAMS uses 'Disciplinary Action' for consequence type."""
        df = make_df(["Disciplinary Action"])
        result = resolve_columns(df, "consequence")
        assert result["Disciplinary Action"] == "consequence_type"

    def test_removal_begin_date_teams(self):
        """TEAMS uses 'Removal Begin Date' for consequence start."""
        df = make_df(["Removal Begin Date"])
        result = resolve_columns(df, "consequence")
        assert result["Removal Begin Date"] == "consequence_start_date"

    def test_removal_end_date_teams(self):
        """TEAMS uses 'Removal End Date' for consequence end."""
        df = make_df(["Removal End Date"])
        result = resolve_columns(df, "consequence")
        assert result["Removal End Date"] == "consequence_end_date"

    def test_daep_begin_date_teams(self):
        """TEAMS DAEP-specific start date header."""
        df = make_df(["DAEP Begin Date"])
        result = resolve_columns(df, "consequence")
        assert result["DAEP Begin Date"] == "consequence_start_date"

    def test_daep_end_date_teams(self):
        df = make_df(["DAEP End Date"])
        result = resolve_columns(df, "consequence")
        assert result["DAEP End Date"] == "consequence_end_date"

    def test_removal_days_teams(self):
        """TEAMS uses 'Removal Days' for days removed."""
        df = make_df(["Removal Days"])
        result = resolve_columns(df, "consequence")
        assert result["Removal Days"] == "days_removed"

    def test_location_code_teams(self):
        df = make_df(["Location Code"])
        result = resolve_columns(df, "incident")
        assert result["Location Code"] == "location"

    def test_at_risk_teams(self):
        """TEAMS at-risk flag maps to special_population."""
        df = make_df(["At Risk"])
        result = resolve_columns(df, "incident")
        assert result["At Risk"] == "special_population"

    def test_full_teams_export(self):
        """Simulate a typical TEAMS (Texas) export."""
        columns = [
            "Referral Number",
            "Referral Date",
            "Campus ID",
            "Grade Level",
            "Conduct Code",
            "Location Code",
            "Class Period",
            "Disciplinary Action",
            "Removal Begin Date",
            "Removal End Date",
            "Removal Days",
            "Instructional Minutes Lost",
            "Race",
            "Gender",
            "SPED",
        ]
        df = make_df(columns)
        result = resolve_columns(df, "incident")
        assert result["Referral Number"] == "incident_number"
        assert result["Referral Date"] == "incident_date"
        assert result["Campus ID"] == "campus"
        assert result["Grade Level"] == "grade"
        assert result["Conduct Code"] == "incident_type"
        assert result["Location Code"] == "location"
        assert result["Class Period"] == "time_block"
        assert result["Disciplinary Action"] == "consequence_type"
        assert result["Removal Begin Date"] == "consequence_start_date"
        assert result["Removal End Date"] == "consequence_end_date"
        assert result["Removal Days"] == "days_removed"
        assert result["Instructional Minutes Lost"] == "instructional_minutes"
        assert result["Race"] == "race"
        assert result["Gender"] == "gender"
        assert result["SPED"] == "special_population"


# ---------------------------------------------------------------------------
# Case-insensitive matching
# ---------------------------------------------------------------------------

class TestCaseInsensitiveMatching:
    def test_all_lowercase(self):
        df = make_df(["incident number", "incident date & time", "building"])
        result = resolve_columns(df, "incident")
        assert result["incident number"] == "incident_number"
        assert result["incident date & time"] == "incident_date"
        assert result["building"] == "campus"

    def test_all_uppercase(self):
        df = make_df(["INCIDENT NUMBER", "BUILDING", "GENDER"])
        result = resolve_columns(df, "incident")
        assert result["INCIDENT NUMBER"] == "incident_number"
        assert result["BUILDING"] == "campus"
        assert result["GENDER"] == "gender"

    def test_mixed_case(self):
        df = make_df(["Incident NUMBER", "INCIDENT Date & Time", "bUiLdInG"])
        result = resolve_columns(df, "incident")
        assert result["Incident NUMBER"] == "incident_number"
        assert result["INCIDENT Date & Time"] == "incident_date"
        assert result["bUiLdInG"] == "campus"

    def test_title_case(self):
        df = make_df(["Consequence Type", "Start Date", "End Date"])
        result = resolve_columns(df, "consequence")
        assert result["Consequence Type"] == "consequence_type"
        assert result["Start Date"] == "consequence_start_date"
        assert result["End Date"] == "consequence_end_date"

    def test_sis_specific_case_variants(self):
        """SIS-specific abbreviations are case-insensitive."""
        df = make_df(["sped", "ell", "iep", "lep", "esl"])
        result = resolve_columns(df, "incident")
        assert result["sped"] == "special_population"
        assert result["ell"] == "special_population"
        assert result["iep"] == "special_population"
        assert result["lep"] == "special_population"
        assert result["esl"] == "special_population"

    def test_powerschool_camel_case_variants(self):
        """PowerSchool camelCase headers match regardless of input casing."""
        df = make_df(["actionstartdate", "ACTIONSTARTDATE", "ActionStartDate"])
        result = resolve_columns(df, "consequence")
        assert result["actionstartdate"] == "consequence_start_date"
        assert result["ACTIONSTARTDATE"] == "consequence_start_date"
        assert result["ActionStartDate"] == "consequence_start_date"

    def test_referral_number_case_variants(self):
        """TEAMS 'Referral Number' matches regardless of case."""
        for variant in ["referral number", "REFERRAL NUMBER", "Referral Number", "REFERRAL number"]:
            df = make_df([variant])
            result = resolve_columns(df, "incident")
            assert result[variant] == "incident_number", (
                f"Expected 'incident_number' for '{variant}'"
            )


# ---------------------------------------------------------------------------
# Whitespace stripping
# ---------------------------------------------------------------------------

class TestWhitespaceStripping:
    def test_leading_whitespace(self):
        df = make_df(["  Incident Number"])
        result = resolve_columns(df, "incident")
        assert result["  Incident Number"] == "incident_number"

    def test_trailing_whitespace(self):
        df = make_df(["Building   "])
        result = resolve_columns(df, "incident")
        assert result["Building   "] == "campus"

    def test_leading_and_trailing_whitespace(self):
        df = make_df(["  Consequence Type  "])
        result = resolve_columns(df, "consequence")
        assert result["  Consequence Type  "] == "consequence_type"

    def test_tab_character(self):
        df = make_df(["\tIncident Number\t"])
        result = resolve_columns(df, "incident")
        assert result["\tIncident Number\t"] == "incident_number"

    def test_multiple_spaces(self):
        df = make_df(["   Gender   "])
        result = resolve_columns(df, "incident")
        assert result["   Gender   "] == "gender"

    def test_whitespace_plus_case(self):
        """Whitespace stripping and case-insensitivity work together."""
        df = make_df(["  INCIDENT NUMBER  ", "  building  "])
        result = resolve_columns(df, "incident")
        assert result["  INCIDENT NUMBER  "] == "incident_number"
        assert result["  building  "] == "campus"

    def test_whitespace_on_sis_specific_header(self):
        df = make_df(["  Referral Number  "])
        result = resolve_columns(df, "incident")
        assert result["  Referral Number  "] == "incident_number"


# ---------------------------------------------------------------------------
# Unmatched columns
# ---------------------------------------------------------------------------

class TestUnmatchedColumns:
    def test_completely_unknown_column(self):
        df = make_df(["Incident Number", "Some_Unknown_Column_XYZ"])
        resolved = resolve_columns(df, "incident")
        unmatched = get_unmatched_columns(df, resolved)
        assert "Some_Unknown_Column_XYZ" in unmatched
        assert "Incident Number" not in unmatched

    def test_all_columns_unmatched(self):
        df = make_df(["col_a", "col_b", "col_c"])
        resolved = resolve_columns(df, "incident")
        unmatched = get_unmatched_columns(df, resolved)
        assert set(unmatched) == {"col_a", "col_b", "col_c"}
        assert resolved == {}

    def test_no_unmatched_columns(self):
        df = make_df(["Incident Number", "Building", "Incident Date & Time"])
        resolved = resolve_columns(df, "incident")
        unmatched = get_unmatched_columns(df, resolved)
        assert unmatched == []

    def test_partial_match(self):
        df = make_df(["Incident Number", "My Custom Field", "Gender"])
        resolved = resolve_columns(df, "incident")
        unmatched = get_unmatched_columns(df, resolved)
        assert "My Custom Field" in unmatched
        assert "Incident Number" not in unmatched
        assert "Gender" not in unmatched

    def test_unmatched_not_in_resolved(self):
        """Unmatched columns must not appear in the resolved map."""
        df = make_df(["Incident Number", "XYZZY_UNKNOWN"])
        resolved = resolve_columns(df, "incident")
        assert "XYZZY_UNKNOWN" not in resolved

    def test_near_match_not_resolved(self):
        """
        Slight misspellings or non-exact variants must NOT match.
        'Incdent Number' (typo) is not a known variant.
        """
        df = make_df(["Incdent Number"])  # typo — 'i' missing
        resolved = resolve_columns(df, "incident")
        unmatched = get_unmatched_columns(df, resolved)
        assert "Incdent Number" in unmatched
        assert resolved == {}

    def test_partial_word_not_resolved(self):
        """'Building Nam' (truncated) must not match 'Building Name'."""
        df = make_df(["Building Nam"])
        resolved = resolve_columns(df, "incident")
        assert resolved == {}

    def test_extra_word_not_resolved(self):
        """'Incident Number Field' is not a known variant and must not match."""
        df = make_df(["Incident Number Field"])
        resolved = resolve_columns(df, "incident")
        assert resolved == {}


# ---------------------------------------------------------------------------
# No inference — exact match only
# ---------------------------------------------------------------------------

class TestNoInference:
    def test_semantic_similar_but_unknown_not_resolved(self):
        """'Student ID' sounds like incident_number but is not in the library."""
        df = make_df(["Student ID"])
        resolved = resolve_columns(df, "incident")
        assert resolved == {}

    def test_abbreviation_not_in_library_not_resolved(self):
        """'Inc Dt' is not a registered variant — must not be inferred."""
        df = make_df(["Inc Dt"])
        resolved = resolve_columns(df, "incident")
        assert resolved == {}

    def test_numeric_column_name_not_resolved(self):
        df = make_df(["1", "2", "123"])
        resolved = resolve_columns(df, "incident")
        assert resolved == {}

    def test_empty_column_name_not_resolved(self):
        """An empty column name (blank header) is not a known variant."""
        df = make_df([""])
        resolved = resolve_columns(df, "incident")
        # empty string normalizes to "" which is not in the library
        assert resolved == {}


# ---------------------------------------------------------------------------
# Determinism — same input always produces same output
# ---------------------------------------------------------------------------

class TestDeterminism:
    def test_same_input_same_output_single_column(self):
        """Calling resolve_columns twice with identical input produces identical output."""
        df = make_df(["Incident Number", "Building", "Incident Date & Time"])
        r1 = resolve_columns(df, "incident")
        r2 = resolve_columns(df, "incident")
        assert r1 == r2

    def test_same_input_same_output_mixed_columns(self):
        columns = [
            "Referral Number",
            "Referral Date",
            "Campus ID",
            "Conduct Code",
            "Unknown_XYZ",
        ]
        df = make_df(columns)
        r1 = resolve_columns(df, "incident")
        r2 = resolve_columns(df, "incident")
        r3 = resolve_columns(df, "incident")
        assert r1 == r2 == r3

    def test_unmatched_determinism(self):
        df = make_df(["Incident Number", "XYZ_UNKNOWN", "Building"])
        resolved = resolve_columns(df, "incident")
        unmatched1 = get_unmatched_columns(df, resolved)
        unmatched2 = get_unmatched_columns(df, resolved)
        assert unmatched1 == unmatched2

    def test_column_order_consistent(self):
        """resolve_columns preserves DataFrame column order in the result keys."""
        columns = ["Incident Number", "Building", "Gender", "Grade Level"]
        df = make_df(columns)
        resolved = resolve_columns(df, "incident")
        resolved_keys = list(resolved.keys())
        # Keys in resolved should appear in the same order as df.columns
        df_order = [col for col in df.columns if col in resolved]
        assert resolved_keys == df_order

    def test_file_label_does_not_change_mappings(self):
        """
        The file_label parameter affects logging only.
        The same headers must resolve identically regardless of label.
        """
        df = make_df(["Incident Number", "Building", "Consequence Type"])
        r_incident = resolve_columns(df, "incident")
        r_consequence = resolve_columns(df, "consequence")
        r_other = resolve_columns(df, "some_other_label")
        assert r_incident == r_consequence == r_other


# ---------------------------------------------------------------------------
# get_unmatched_columns contract
# ---------------------------------------------------------------------------

class TestGetUnmatchedColumnsContract:
    def test_returns_list(self):
        df = make_df(["Incident Number"])
        resolved = resolve_columns(df, "incident")
        result = get_unmatched_columns(df, resolved)
        assert isinstance(result, list)

    def test_empty_df_returns_empty_list(self):
        df = pd.DataFrame()
        resolved = resolve_columns(df, "incident")
        result = get_unmatched_columns(df, resolved)
        assert result == []

    def test_all_matched_returns_empty_list(self):
        df = make_df(["Incident Number", "Building", "Gender"])
        resolved = resolve_columns(df, "incident")
        result = get_unmatched_columns(df, resolved)
        assert result == []

    def test_unmatched_preserves_original_header_string(self):
        """
        The unmatched column list must contain the exact original header string,
        including original casing and whitespace.
        """
        original = "  MY_CUSTOM_FIELD  "
        df = make_df([original])
        resolved = resolve_columns(df, "incident")
        unmatched = get_unmatched_columns(df, resolved)
        assert original in unmatched


# ---------------------------------------------------------------------------
# Integration: resolve_columns + get_unmatched_columns together
# ---------------------------------------------------------------------------

class TestResolveAndUnmatchedTogether:
    def test_resolved_plus_unmatched_covers_all_columns(self):
        """
        Every column must appear in exactly one of: resolved keys or unmatched list.
        No column is silently dropped.
        """
        columns = [
            "Incident Number",    # known
            "Building",           # known
            "MY_CUSTOM_1",        # unknown
            "Gender",             # known
            "MY_CUSTOM_2",        # unknown
        ]
        df = make_df(columns)
        resolved = resolve_columns(df, "incident")
        unmatched = get_unmatched_columns(df, resolved)

        all_accounted = set(resolved.keys()) | set(unmatched)
        assert all_accounted == set(df.columns)

    def test_no_overlap_between_resolved_and_unmatched(self):
        """A column cannot appear in both resolved and unmatched."""
        columns = ["Incident Number", "MY_CUSTOM", "Grade Level"]
        df = make_df(columns)
        resolved = resolve_columns(df, "incident")
        unmatched = get_unmatched_columns(df, resolved)
        overlap = set(resolved.keys()) & set(unmatched)
        assert overlap == set()
