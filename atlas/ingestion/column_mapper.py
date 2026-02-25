"""
Atlas Column Mapping Engine — Phase 1

Deterministic SIS alias library for header normalization.

RULES (non-negotiable):
- Deterministic string matching only. No fuzzy matching. No LLM inference.
- Case-insensitive. Whitespace stripped before comparison.
- Same input always produces same output.
- No column renamed without being logged.
- No column silently dropped.
- No inference — if a header does not match a known variant exactly
  (case-insensitive + stripped), it is unmatched.

Public API:
  resolve_columns(df, file_label) -> dict[str, str]
  get_unmatched_columns(df, resolved_map) -> list[str]
"""

from __future__ import annotations

import logging

import pandas as pd

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Atlas normalized field names (canonical schema)
# ---------------------------------------------------------------------------

NORMALIZED_FIELDS: frozenset[str] = frozenset({
    "incident_number",
    "incident_date",
    "campus",
    "grade",
    "incident_type",
    "location",
    "time_block",
    "response",
    "consequence_type",
    "consequence_start_date",
    "consequence_end_date",
    "days_removed",
    "instructional_minutes",
    "race",
    "gender",
    "special_population",
})

# ---------------------------------------------------------------------------
# SIS alias libraries
# ---------------------------------------------------------------------------
# Each section maps raw header variants from that SIS to Atlas normalized
# field names. Keys are written in their natural SIS casing; comparison
# is always case-insensitive + whitespace-stripped at lookup time.
#
# OVERLAP RULE: The same normalized variant may appear in multiple SIS
# sections provided it maps to the same target. If two systems use the
# same header for different fields, that variant is intentionally EXCLUDED
# (operator override via operator_column_overrides is required).
# ---------------------------------------------------------------------------

# ── Skyward ─────────────────────────────────────────────────────────────────
_SKYWARD_VARIANTS: dict[str, str] = {
    # incident_number
    "Incident Number":                 "incident_number",
    "Incident_Number":                 "incident_number",
    "Incident #":                      "incident_number",
    "Incident#":                       "incident_number",
    "Incident Nbr":                    "incident_number",   # Skyward uses "Nbr"
    "Incident_Nbr":                    "incident_number",
    "Inc Number":                      "incident_number",
    "Inc_Number":                      "incident_number",
    "Inc #":                           "incident_number",
    "Inc#":                            "incident_number",
    # incident_date
    "Incident Date & Time":            "incident_date",
    "Incident Date and Time":          "incident_date",
    "Incident_Date_Time":              "incident_date",
    "Incident Date":                   "incident_date",
    "Incident_Date":                   "incident_date",
    "Incident DateTime":               "incident_date",
    "Incident_DateTime":               "incident_date",
    # campus
    "Building":                        "campus",
    "Building Name":                   "campus",
    "Building_Name":                   "campus",
    "Entity Code":                     "campus",            # Skyward campus identifier
    "Entity_Code":                     "campus",
    "Campus":                          "campus",
    "Campus_Name":                     "campus",
    "Campus Name":                     "campus",
    "School":                          "campus",
    # grade
    "Grade Level":                     "grade",
    "Grade_Level":                     "grade",
    "Grade":                           "grade",
    "Student Grade":                   "grade",
    "Student_Grade":                   "grade",
    "Student Grade Level":             "grade",
    "Student_Grade_Level":             "grade",
    "GradeLevel":                      "grade",
    "Grade Lvl":                       "grade",
    "Grade_Lvl":                       "grade",
    # incident_type
    "Incident Type":                   "incident_type",
    "Incident_Type":                   "incident_type",
    "Behavior Type":                   "incident_type",
    "Behavior_Type":                   "incident_type",
    "Violation":                       "incident_type",
    "Violation Type":                  "incident_type",
    "Violation_Type":                  "incident_type",
    # location
    "Location":                        "location",
    "Incident Location":               "location",
    "Incident_Location":               "location",
    # time_block
    "Class Period":                    "time_block",
    "Class_Period":                    "time_block",
    "Period":                          "time_block",
    "Time Block":                      "time_block",
    "Time_Block":                      "time_block",
    "TimeBlock":                       "time_block",
    "Time Period":                     "time_block",
    "Time_Period":                     "time_block",
    # response
    "Action Taken":                    "response",          # Skyward initial staff response
    "Action_Taken":                    "response",
    # consequence_type
    "Consequence Type":                "consequence_type",
    "Consequence_Type":                "consequence_type",
    "Action Type":                     "consequence_type",
    "Action_Type":                     "consequence_type",
    # consequence_start_date
    "Consequence Start Date":          "consequence_start_date",
    "Consequence_Start_Date":          "consequence_start_date",
    "Start Date":                      "consequence_start_date",
    "Start_Date":                      "consequence_start_date",
    "Begin Date":                      "consequence_start_date",
    "Begin_Date":                      "consequence_start_date",
    # consequence_end_date
    "Consequence End Date":            "consequence_end_date",
    "Consequence_End_Date":            "consequence_end_date",
    "End Date":                        "consequence_end_date",
    "End_Date":                        "consequence_end_date",
    # days_removed
    "Days Removed":                    "days_removed",
    "Days_Removed":                    "days_removed",
    "Number of Days":                  "days_removed",
    "Number_of_Days":                  "days_removed",
    "Nbr Days":                        "days_removed",      # Skyward "Nbr" pattern
    "Nbr_Days":                        "days_removed",
    "Num Days":                        "days_removed",
    "Num_Days":                        "days_removed",
    # instructional_minutes
    "Instructional Minutes Lost":      "instructional_minutes",
    "Instructional_Minutes_Lost":      "instructional_minutes",
    "Minutes Lost":                    "instructional_minutes",
    "Minutes_Lost":                    "instructional_minutes",
    "Instructional Minutes":           "instructional_minutes",
    "Instructional_Minutes":           "instructional_minutes",
    # race
    "Race":                            "race",
    "Ethnicity":                       "race",
    "Race/Ethnicity":                  "race",
    # gender
    "Gender":                          "gender",
    "Sex":                             "gender",
    # special_population
    "Special Education":               "special_population",
    "Special_Education":               "special_population",
    "Spec Ed":                         "special_population",
    "Spec_Ed":                         "special_population",
    "Special Ed":                      "special_population",
    "Special_Ed":                      "special_population",
}

# ── PowerSchool ──────────────────────────────────────────────────────────────
_POWERSCHOOL_VARIANTS: dict[str, str] = {
    # incident_number — PS calls these "offenses" or "incidents"
    "Incident Number":                 "incident_number",
    "Incident_Number":                 "incident_number",
    "Incident_ID":                     "incident_number",   # PS Incident_ID
    "Incident ID":                     "incident_number",
    "Offense_ID":                      "incident_number",   # PS offense system
    "Offense ID":                      "incident_number",
    "Offense_Number":                  "incident_number",
    "Offense Number":                  "incident_number",
    # incident_date
    "Incident_Date":                   "incident_date",
    "Incident Date":                   "incident_date",
    "Date_Of_Incident":                "incident_date",
    "Date of Incident":                "incident_date",
    "Offense_Date":                    "incident_date",     # PS offense date
    "Offense Date":                    "incident_date",
    # campus
    "School_Name":                     "campus",
    "School Name":                     "campus",
    "Campus_Name":                     "campus",
    "Campus Name":                     "campus",
    "School":                          "campus",
    "Campus":                          "campus",
    # grade
    "Grade_Level":                     "grade",
    "Grade Level":                     "grade",
    "Grade":                           "grade",
    "Student_Grade":                   "grade",
    "Student Grade":                   "grade",
    "Student Grade Level":             "grade",
    "Student_Grade_Level":             "grade",
    # incident_type
    "Offense_Type":                    "incident_type",     # PS offense type
    "Offense Type":                    "incident_type",
    "Incident_Type":                   "incident_type",
    "Incident Type":                   "incident_type",
    "Behavior_Type":                   "incident_type",
    "Behavior Type":                   "incident_type",
    # location
    "Offense_Location":                "location",          # PS offense location
    "Offense Location":                "location",
    "Incident_Location":               "location",
    "Incident Location":               "location",
    "Location":                        "location",
    # time_block
    "Class_Period":                    "time_block",
    "Class Period":                    "time_block",
    "Period":                          "time_block",
    "TimeBlock":                       "time_block",
    # response
    "Action_Taken":                    "response",
    "Action Taken":                    "response",
    "Staff_Response":                  "response",
    "Staff Response":                  "response",
    # consequence_type
    "Consequence_Type":                "consequence_type",
    "Consequence Type":                "consequence_type",
    "Action_Type":                     "consequence_type",
    "Action Type":                     "consequence_type",
    "Response_Type":                   "consequence_type",
    "Response Type":                   "consequence_type",
    # consequence_start_date
    "Consequence_Start_Date":          "consequence_start_date",
    "Consequence Start Date":          "consequence_start_date",
    "Start_Date":                      "consequence_start_date",
    "Start Date":                      "consequence_start_date",
    "Action_Start_Date":               "consequence_start_date",
    "Action Start Date":               "consequence_start_date",
    "ActionStartDate":                 "consequence_start_date",  # PS camelCase
    "Suspension Start Date":           "consequence_start_date",
    "Suspension_Start_Date":           "consequence_start_date",
    # consequence_end_date
    "Consequence_End_Date":            "consequence_end_date",
    "Consequence End Date":            "consequence_end_date",
    "End_Date":                        "consequence_end_date",
    "End Date":                        "consequence_end_date",
    "Action_End_Date":                 "consequence_end_date",
    "Action End Date":                 "consequence_end_date",
    "ActionEndDate":                   "consequence_end_date",    # PS camelCase
    "Suspension End Date":             "consequence_end_date",
    "Suspension_End_Date":             "consequence_end_date",
    "Return Date":                     "consequence_end_date",
    "Return_Date":                     "consequence_end_date",
    # days_removed
    "Days_Removed":                    "days_removed",
    "Days Removed":                    "days_removed",
    "Days_Assigned":                   "days_removed",      # PS days assigned
    "Days Assigned":                   "days_removed",
    "DaysAssigned":                    "days_removed",      # PS camelCase
    "Days_Suspended":                  "days_removed",
    "Days Suspended":                  "days_removed",
    "Number_of_Days":                  "days_removed",
    "Number of Days":                  "days_removed",
    # instructional_minutes
    "Instructional_Minutes_Lost":      "instructional_minutes",
    "Instructional Minutes Lost":      "instructional_minutes",
    "Minutes_Lost":                    "instructional_minutes",
    "Minutes Lost":                    "instructional_minutes",
    "Instructional_Minutes":           "instructional_minutes",
    "Instructional Minutes":           "instructional_minutes",
    # race
    "Race":                            "race",
    "Ethnicity":                       "race",
    "Race_Ethnicity":                  "race",
    "Race/Ethnicity":                  "race",
    # gender
    "Gender":                          "gender",
    "Sex":                             "gender",
    # special_population
    "Special_Ed":                      "special_population",
    "Special Ed":                      "special_population",
    "Special_Education":               "special_population",
    "Special Education":               "special_population",
    "IEP":                             "special_population",
    "504_Status":                      "special_population",
    "504 Status":                      "special_population",
    "ELL":                             "special_population",
    "LEP":                             "special_population",
}

# ── DeansList ────────────────────────────────────────────────────────────────
_DEANSLIST_VARIANTS: dict[str, str] = {
    # incident_number — DL uses "Incident ID"
    "Incident ID":                     "incident_number",
    "Incident_ID":                     "incident_number",
    "Incident Number":                 "incident_number",
    "Incident_Number":                 "incident_number",
    # incident_date — DL uses "Created" for submission date; "Incident Date" for event
    "Incident Date":                   "incident_date",
    "Incident_Date":                   "incident_date",
    "Date of Incident":                "incident_date",
    "Date_of_Incident":                "incident_date",
    # campus
    "School":                          "campus",
    "Campus":                          "campus",
    "Campus_Name":                     "campus",
    "Campus Name":                     "campus",
    # grade
    "Grade":                           "grade",
    "Grade Level":                     "grade",
    "Grade_Level":                     "grade",
    "Student Grade":                   "grade",
    "Student_Grade":                   "grade",
    # incident_type — DL uses "Infraction" and "Incident Category"
    "Infraction":                      "incident_type",    # DeansList-specific term
    "Infraction Type":                 "incident_type",
    "Infraction_Type":                 "incident_type",
    "Incident Category":               "incident_type",    # DeansList category
    "Incident_Category":               "incident_type",
    "Incident Type":                   "incident_type",
    "Incident_Type":                   "incident_type",
    "Behavior":                        "incident_type",    # DeansList behavior field
    # location
    "Location":                        "location",
    "Incident Location":               "location",
    "Incident_Location":               "location",
    # time_block
    "Period":                          "time_block",
    "Class Period":                    "time_block",
    "Class_Period":                    "time_block",
    "Time Block":                      "time_block",
    "Time_Block":                      "time_block",
    # response — DL "Action" = initial staff response
    "Action Taken":                    "response",
    "Action_Taken":                    "response",
    "Staff Response":                  "response",
    "Staff_Response":                  "response",
    # consequence_type — DL "Consequence" = consequence type
    "Consequence":                     "consequence_type",  # DeansList bare "Consequence"
    "Consequence Type":                "consequence_type",
    "Consequence_Type":                "consequence_type",
    "Action Type":                     "consequence_type",
    "Action_Type":                     "consequence_type",
    "Sanction":                        "consequence_type",
    "Sanction Type":                   "consequence_type",
    "Sanction_Type":                   "consequence_type",
    # consequence_start_date — DL uses "Start Date"
    "Start Date":                      "consequence_start_date",
    "Start_Date":                      "consequence_start_date",
    "Consequence Start Date":          "consequence_start_date",
    "Consequence_Start_Date":          "consequence_start_date",
    "Begin Date":                      "consequence_start_date",
    "Begin_Date":                      "consequence_start_date",
    # consequence_end_date — DL uses "End Date"
    "End Date":                        "consequence_end_date",
    "End_Date":                        "consequence_end_date",
    "Consequence End Date":            "consequence_end_date",
    "Consequence_End_Date":            "consequence_end_date",
    # days_removed
    "Days Removed":                    "days_removed",
    "Days_Removed":                    "days_removed",
    "Days Suspended":                  "days_removed",
    "Days_Suspended":                  "days_removed",
    "Number of Days":                  "days_removed",
    "Number_of_Days":                  "days_removed",
    # instructional_minutes
    "Instructional Minutes Lost":      "instructional_minutes",
    "Instructional_Minutes_Lost":      "instructional_minutes",
    "Instructional Minutes":           "instructional_minutes",
    "Instructional_Minutes":           "instructional_minutes",
    "Minutes Lost":                    "instructional_minutes",
    "Minutes_Lost":                    "instructional_minutes",
    # race
    "Race":                            "race",
    "Race/Ethnicity":                  "race",
    "Ethnicity":                       "race",
    # gender
    "Gender":                          "gender",
    # special_population — DL uses SPED, IEP, ELL abbreviations
    "SPED":                            "special_population",  # DeansList abbreviation
    "IEP":                             "special_population",
    "ELL":                             "special_population",
    "LEP":                             "special_population",
    "Special Education":               "special_population",
    "Special_Education":               "special_population",
    "Spec Ed":                         "special_population",
    "Spec_Ed":                         "special_population",
    "504 Status":                      "special_population",
    "504_Status":                      "special_population",
}

# ── Infinite Campus ──────────────────────────────────────────────────────────
_INFINITE_CAMPUS_VARIANTS: dict[str, str] = {
    # incident_number — IC uses "Event ID"
    "Incident Number":                 "incident_number",
    "Incident_Number":                 "incident_number",
    "Event_ID":                        "incident_number",   # IC event system
    "Event ID":                        "incident_number",
    "EventID":                         "incident_number",
    # incident_date
    "Incident Date":                   "incident_date",
    "Incident_Date":                   "incident_date",
    "Incident Date & Time":            "incident_date",
    "Date of Incident":                "incident_date",
    "Date_of_Incident":                "incident_date",
    # campus — IC uses "Calendar Name" for the school/campus
    "Calendar Name":                   "campus",            # IC campus identifier
    "Calendar_Name":                   "campus",
    "School Name":                     "campus",
    "School_Name":                     "campus",
    "Campus":                          "campus",
    "Campus Name":                     "campus",
    "Campus_Name":                     "campus",
    "School":                          "campus",
    # grade
    "Grade":                           "grade",
    "Grade Level":                     "grade",
    "Grade_Level":                     "grade",
    "Student Grade Level":             "grade",
    "Student_Grade_Level":             "grade",
    "Student Grade":                   "grade",
    "Student_Grade":                   "grade",
    # incident_type — IC uses "Event Type" or "Behavior"
    "Event Type":                      "incident_type",     # IC event type
    "Event_Type":                      "incident_type",
    "Incident Type":                   "incident_type",
    "Incident_Type":                   "incident_type",
    "Behavior Type":                   "incident_type",
    "Behavior_Type":                   "incident_type",
    # location
    "Location":                        "location",
    "Event Location":                  "location",          # IC event location
    "Event_Location":                  "location",
    "Incident Location":               "location",
    "Incident_Location":               "location",
    # time_block
    "Period":                          "time_block",
    "Class Period":                    "time_block",
    "Class_Period":                    "time_block",
    "Time Block":                      "time_block",
    "Time_Block":                      "time_block",
    # response — IC "Resolution" when it means staff response
    "Staff Response":                  "response",
    "Staff_Response":                  "response",
    "Action Taken":                    "response",
    "Action_Taken":                    "response",
    # consequence_type — IC uses "Resolution Type" or "Consequence Type"
    "Resolution Type":                 "consequence_type",  # IC resolution type
    "Resolution_Type":                 "consequence_type",
    "Resolution":                      "consequence_type",  # IC bare resolution
    "Consequence Type":                "consequence_type",
    "Consequence_Type":                "consequence_type",
    "Action Type":                     "consequence_type",
    "Action_Type":                     "consequence_type",
    "Intervention Type":               "consequence_type",
    "Intervention_Type":               "consequence_type",
    # consequence_start_date — IC uses "Consequence Start"
    "Consequence Start":               "consequence_start_date",   # IC short form
    "Consequence_Start":               "consequence_start_date",
    "Consequence Start Date":          "consequence_start_date",
    "Consequence_Start_Date":          "consequence_start_date",
    "Start Date":                      "consequence_start_date",
    "Start_Date":                      "consequence_start_date",
    "Begin Date":                      "consequence_start_date",
    "Begin_Date":                      "consequence_start_date",
    # consequence_end_date — IC uses "Consequence End"
    "Consequence End":                 "consequence_end_date",     # IC short form
    "Consequence_End":                 "consequence_end_date",
    "Consequence End Date":            "consequence_end_date",
    "Consequence_End_Date":            "consequence_end_date",
    "End Date":                        "consequence_end_date",
    "End_Date":                        "consequence_end_date",
    "Return Date":                     "consequence_end_date",
    "Return_Date":                     "consequence_end_date",
    # days_removed
    "Days Removed":                    "days_removed",
    "Days_Removed":                    "days_removed",
    "Days Suspended":                  "days_removed",
    "Days_Suspended":                  "days_removed",
    "Number of Days":                  "days_removed",
    "Number_of_Days":                  "days_removed",
    # instructional_minutes
    "Instructional Minutes Lost":      "instructional_minutes",
    "Instructional_Minutes_Lost":      "instructional_minutes",
    "Instructional Minutes":           "instructional_minutes",
    "Instructional_Minutes":           "instructional_minutes",
    "Minutes Lost":                    "instructional_minutes",
    "Minutes_Lost":                    "instructional_minutes",
    # race
    "Race":                            "race",
    "Race/Ethnicity":                  "race",
    "Ethnicity":                       "race",
    # gender
    "Gender":                          "gender",
    "Sex":                             "gender",
    # special_population
    "Special Education":               "special_population",
    "Special_Education":               "special_population",
    "IEP":                             "special_population",
    "ELL":                             "special_population",
    "LEP":                             "special_population",
    "504 Status":                      "special_population",
    "504_Status":                      "special_population",
    "Disability Status":               "special_population",
    "Disability_Status":               "special_population",
}

# ── TEAMS (Texas SIS) ────────────────────────────────────────────────────────
_TEAMS_VARIANTS: dict[str, str] = {
    # incident_number — TEAMS uses "Incident Nbr" and "Referral Number"
    "Incident Nbr":                    "incident_number",   # TEAMS Nbr pattern
    "Incident_Nbr":                    "incident_number",
    "Incident Number":                 "incident_number",
    "Incident_Number":                 "incident_number",
    "Referral Number":                 "incident_number",   # TEAMS referral system
    "Referral_Number":                 "incident_number",
    "Referral #":                      "incident_number",
    "Referral#":                       "incident_number",
    "Referral ID":                     "incident_number",
    "Referral_ID":                     "incident_number",
    # incident_date — TEAMS uses "Referral Date" or "Incident Date"
    "Incident Date":                   "incident_date",
    "Incident_Date":                   "incident_date",
    "Referral Date":                   "incident_date",     # TEAMS referral date
    "Referral_Date":                   "incident_date",
    "Date of Incident":                "incident_date",
    "Date_of_Incident":                "incident_date",
    # campus — TEAMS uses numeric Campus ID and Campus Number
    "Campus":                          "campus",
    "Campus ID":                       "campus",            # TEAMS numeric campus
    "Campus_ID":                       "campus",
    "Campus Number":                   "campus",            # TEAMS campus number
    "Campus_Number":                   "campus",
    "Campus Name":                     "campus",
    "Campus_Name":                     "campus",
    "School":                          "campus",
    "School Name":                     "campus",
    "School_Name":                     "campus",
    # grade
    "Grade":                           "grade",
    "Grade Level":                     "grade",
    "Grade_Level":                     "grade",
    "Student Grade":                   "grade",
    "Student_Grade":                   "grade",
    # incident_type — TEAMS uses "Conduct Code" and "Offense Code"
    "Conduct Code":                    "incident_type",     # TEAMS conduct code
    "Conduct_Code":                    "incident_type",
    "Offense Code":                    "incident_type",     # TEAMS offense code
    "Offense_Code":                    "incident_type",
    "Incident Type":                   "incident_type",
    "Incident_Type":                   "incident_type",
    "Conduct":                         "incident_type",     # TEAMS bare conduct
    # location
    "Location":                        "location",
    "Location Code":                   "location",          # TEAMS location code
    "Location_Code":                   "location",
    "Incident Location":               "location",
    "Incident_Location":               "location",
    # time_block
    "Period":                          "time_block",
    "Class Period":                    "time_block",
    "Class_Period":                    "time_block",
    "Time Block":                      "time_block",
    "Time_Block":                      "time_block",
    # response
    "Action Taken":                    "response",
    "Action_Taken":                    "response",
    "Staff Response":                  "response",
    "Staff_Response":                  "response",
    # consequence_type — TEAMS uses "Disciplinary Action" and "Removal Type"
    "Consequence Type":                "consequence_type",
    "Consequence_Type":                "consequence_type",
    "Disciplinary Action":             "consequence_type",  # TEAMS disciplinary
    "Disciplinary_Action":             "consequence_type",
    "Removal Type":                    "consequence_type",  # TEAMS removal type
    "Removal_Type":                    "consequence_type",
    "Action Type":                     "consequence_type",
    "Action_Type":                     "consequence_type",
    # consequence_start_date — TEAMS uses "Removal Begin Date"
    "Consequence Start Date":          "consequence_start_date",
    "Consequence_Start_Date":          "consequence_start_date",
    "Removal Begin Date":              "consequence_start_date",  # TEAMS removal
    "Removal_Begin_Date":              "consequence_start_date",
    "Start Date":                      "consequence_start_date",
    "Start_Date":                      "consequence_start_date",
    "Begin Date":                      "consequence_start_date",
    "Begin_Date":                      "consequence_start_date",
    "DAEP Begin Date":                 "consequence_start_date",  # TEAMS DAEP
    "DAEP_Begin_Date":                 "consequence_start_date",
    "Suspension Start Date":           "consequence_start_date",
    "Suspension_Start_Date":           "consequence_start_date",
    # consequence_end_date — TEAMS uses "Removal End Date"
    "Consequence End Date":            "consequence_end_date",
    "Consequence_End_Date":            "consequence_end_date",
    "Removal End Date":                "consequence_end_date",    # TEAMS removal
    "Removal_End_Date":                "consequence_end_date",
    "End Date":                        "consequence_end_date",
    "End_Date":                        "consequence_end_date",
    "DAEP End Date":                   "consequence_end_date",    # TEAMS DAEP
    "DAEP_End_Date":                   "consequence_end_date",
    "Suspension End Date":             "consequence_end_date",
    "Suspension_End_Date":             "consequence_end_date",
    "Return Date":                     "consequence_end_date",
    "Return_Date":                     "consequence_end_date",
    # days_removed — TEAMS uses "Removal Days"
    "Days Removed":                    "days_removed",
    "Days_Removed":                    "days_removed",
    "Removal Days":                    "days_removed",      # TEAMS
    "Removal_Days":                    "days_removed",
    "Days Suspended":                  "days_removed",
    "Days_Suspended":                  "days_removed",
    "Number of Days":                  "days_removed",
    "Number_of_Days":                  "days_removed",
    "Days of Removal":                 "days_removed",
    "Days_of_Removal":                 "days_removed",
    # instructional_minutes
    "Instructional Minutes Lost":      "instructional_minutes",
    "Instructional_Minutes_Lost":      "instructional_minutes",
    "Instructional Minutes":           "instructional_minutes",
    "Instructional_Minutes":           "instructional_minutes",
    "Minutes Lost":                    "instructional_minutes",
    "Minutes_Lost":                    "instructional_minutes",
    # race
    "Race":                            "race",
    "Race/Ethnicity":                  "race",
    "Ethnicity":                       "race",
    "Race Ethnicity":                  "race",
    "Race_Ethnicity":                  "race",
    # gender
    "Gender":                          "gender",
    "Sex":                             "gender",
    # special_population — TEAMS uses EC (Early Childhood), SPED, ELL/LEP
    "Special Education":               "special_population",
    "Special_Education":               "special_population",
    "Special Ed":                      "special_population",
    "Special_Ed":                      "special_population",
    "SPED":                            "special_population",   # TEAMS abbreviation
    "IEP":                             "special_population",
    "ELL":                             "special_population",
    "LEP":                             "special_population",
    "ESL":                             "special_population",
    "At Risk":                         "special_population",   # TEAMS at-risk flag
    "At_Risk":                         "special_population",
}

# ── Generic / Unknown SIS ────────────────────────────────────────────────────
_GENERIC_VARIANTS: dict[str, str] = {
    # incident_number
    "Incident Number":                 "incident_number",
    "Incident_Number":                 "incident_number",
    "IncidentNumber":                  "incident_number",
    "Incident #":                      "incident_number",
    "Incident#":                       "incident_number",
    "Inc Number":                      "incident_number",
    "Inc_Number":                      "incident_number",
    "Inc #":                           "incident_number",
    "Inc#":                            "incident_number",
    "Incident ID":                     "incident_number",
    "Incident_ID":                     "incident_number",
    # incident_date
    "Incident Date & Time":            "incident_date",
    "Incident Date and Time":          "incident_date",
    "Incident_Date_Time":              "incident_date",
    "Incident_Date":                   "incident_date",
    "Incident Date":                   "incident_date",
    "Incident DateTime":               "incident_date",
    "Incident_DateTime":               "incident_date",
    "Date of Incident":                "incident_date",
    "Date_of_Incident":                "incident_date",
    "Date":                            "incident_date",    # broad fallback
    # campus
    "Campus":                          "campus",
    "Campus_Name":                     "campus",
    "Campus Name":                     "campus",
    "School":                          "campus",
    "School Name":                     "campus",
    "School_Name":                     "campus",
    "Building":                        "campus",
    "Building Name":                   "campus",
    "Building_Name":                   "campus",
    "Entity Code":                     "campus",
    "Entity_Code":                     "campus",
    # grade
    "Grade":                           "grade",
    "Grade Level":                     "grade",
    "Grade_Level":                     "grade",
    "Student Grade":                   "grade",
    "Student_Grade":                   "grade",
    "Student Grade Level":             "grade",
    "Student_Grade_Level":             "grade",
    "GradeLevel":                      "grade",
    "Grade Lvl":                       "grade",
    "Grade_Lvl":                       "grade",
    # incident_type
    "Incident Type":                   "incident_type",
    "Incident_Type":                   "incident_type",
    "Behavior Type":                   "incident_type",
    "Behavior_Type":                   "incident_type",
    "Infraction Type":                 "incident_type",
    "Infraction_Type":                 "incident_type",
    "Violation":                       "incident_type",
    "Violation Type":                  "incident_type",
    "Violation_Type":                  "incident_type",
    "Incident Category":               "incident_type",
    "Incident_Category":               "incident_type",
    # location
    "Location":                        "location",
    "Incident Location":               "location",
    "Incident_Location":               "location",
    # time_block
    "Time Block":                      "time_block",
    "Time_Block":                      "time_block",
    "Class Period":                    "time_block",
    "Class_Period":                    "time_block",
    "Period":                          "time_block",
    "TimeBlock":                       "time_block",
    "Time Period":                     "time_block",
    "Time_Period":                     "time_block",
    "Block":                           "time_block",
    # response
    "Response":                        "response",
    "Action Taken":                    "response",
    "Action_Taken":                    "response",
    "Staff Response":                  "response",
    "Staff_Response":                  "response",
    "Teacher Response":                "response",
    "Teacher_Response":                "response",
    "Teacher Action":                  "response",
    "Teacher_Action":                  "response",
    # consequence_type
    "Consequence Type":                "consequence_type",
    "Consequence_Type":                "consequence_type",
    "Action Type":                     "consequence_type",
    "Action_Type":                     "consequence_type",
    "Response Type":                   "consequence_type",
    "Response_Type":                   "consequence_type",
    "Consequence":                     "consequence_type",
    "Sanction":                        "consequence_type",
    "Sanction Type":                   "consequence_type",
    "Sanction_Type":                   "consequence_type",
    "Intervention Type":               "consequence_type",
    "Intervention_Type":               "consequence_type",
    "Disciplinary Action":             "consequence_type",
    "Disciplinary_Action":             "consequence_type",
    "Removal Type":                    "consequence_type",
    "Removal_Type":                    "consequence_type",
    "Resolution Type":                 "consequence_type",
    "Resolution_Type":                 "consequence_type",
    "Resolution":                      "consequence_type",
    # consequence_start_date
    "Consequence Start Date":          "consequence_start_date",
    "Consequence_Start_Date":          "consequence_start_date",
    "Start Date":                      "consequence_start_date",
    "Start_Date":                      "consequence_start_date",
    "Begin Date":                      "consequence_start_date",
    "Begin_Date":                      "consequence_start_date",
    "Consequence Start":               "consequence_start_date",
    "Consequence_Start":               "consequence_start_date",
    "Removal Begin Date":              "consequence_start_date",
    "Removal_Begin_Date":              "consequence_start_date",
    "Action Start Date":               "consequence_start_date",
    "Action_Start_Date":               "consequence_start_date",
    "Suspension Start Date":           "consequence_start_date",
    "Suspension_Start_Date":           "consequence_start_date",
    # consequence_end_date
    "Consequence End Date":            "consequence_end_date",
    "Consequence_End_Date":            "consequence_end_date",
    "End Date":                        "consequence_end_date",
    "End_Date":                        "consequence_end_date",
    "Consequence End":                 "consequence_end_date",
    "Consequence_End":                 "consequence_end_date",
    "Removal End Date":                "consequence_end_date",
    "Removal_End_Date":                "consequence_end_date",
    "Action End Date":                 "consequence_end_date",
    "Action_End_Date":                 "consequence_end_date",
    "Suspension End Date":             "consequence_end_date",
    "Suspension_End_Date":             "consequence_end_date",
    "Return Date":                     "consequence_end_date",
    "Return_Date":                     "consequence_end_date",
    # days_removed
    "Days Removed":                    "days_removed",
    "Days_Removed":                    "days_removed",
    "Days Suspended":                  "days_removed",
    "Days_Suspended":                  "days_removed",
    "Number of Days":                  "days_removed",
    "Number_of_Days":                  "days_removed",
    "Days Assigned":                   "days_removed",
    "Days_Assigned":                   "days_removed",
    "Removal Days":                    "days_removed",
    "Removal_Days":                    "days_removed",
    "Num Days":                        "days_removed",
    "Num_Days":                        "days_removed",
    "Nbr Days":                        "days_removed",
    "Nbr_Days":                        "days_removed",
    "# Days":                          "days_removed",
    "Days of Removal":                 "days_removed",
    "Days_of_Removal":                 "days_removed",
    # instructional_minutes
    "Instructional Minutes Lost":      "instructional_minutes",
    "Instructional_Minutes_Lost":      "instructional_minutes",
    "Minutes Lost":                    "instructional_minutes",
    "Minutes_Lost":                    "instructional_minutes",
    "Instructional_Minutes":           "instructional_minutes",
    "Instructional Minutes":           "instructional_minutes",
    "Inst Minutes":                    "instructional_minutes",
    "Inst_Minutes":                    "instructional_minutes",
    "Minutes Removed":                 "instructional_minutes",
    "Minutes_Removed":                 "instructional_minutes",
    "Minutes of Removal":              "instructional_minutes",
    "Minutes_of_Removal":              "instructional_minutes",
    # race
    "Race":                            "race",
    "Ethnicity":                       "race",
    "Race/Ethnicity":                  "race",
    "Race Ethnicity":                  "race",
    "Race_Ethnicity":                  "race",
    "Student Race":                    "race",
    "Student_Race":                    "race",
    "Student Ethnicity":               "race",
    "Student_Ethnicity":               "race",
    "Racial/Ethnic Group":             "race",
    "Racial_Ethnic_Group":             "race",
    # gender
    "Gender":                          "gender",
    "Sex":                             "gender",
    "Student Gender":                  "gender",
    "Student_Gender":                  "gender",
    "Student Sex":                     "gender",
    "Student_Sex":                     "gender",
    # special_population
    "Special Population":              "special_population",
    "Special_Population":              "special_population",
    "Special Education":               "special_population",
    "Special_Education":               "special_population",
    "Spec Ed":                         "special_population",
    "Spec_Ed":                         "special_population",
    "Special Ed":                      "special_population",
    "Special_Ed":                      "special_population",
    "SPED":                            "special_population",
    "IEP":                             "special_population",
    "ELL":                             "special_population",
    "LEP":                             "special_population",
    "ESL":                             "special_population",
    "Disability":                      "special_population",
    "Disability Status":               "special_population",
    "Disability_Status":               "special_population",
    "504 Status":                      "special_population",
    "504_Status":                      "special_population",
    "IEP Status":                      "special_population",
    "IEP_Status":                      "special_population",
    "English Learner":                 "special_population",
    "English_Learner":                 "special_population",
    "Limited English Proficient":      "special_population",
    "Limited_English_Proficient":      "special_population",
    "At Risk":                         "special_population",
    "At_Risk":                         "special_population",
    "Economically Disadvantaged":      "special_population",
    "Economically_Disadvantaged":      "special_population",
}

# ---------------------------------------------------------------------------
# Source registry — ordered list of (label, dict) for all SIS systems
# ---------------------------------------------------------------------------

_ALL_SOURCES: list[tuple[str, dict[str, str]]] = [
    ("Skyward",         _SKYWARD_VARIANTS),
    ("PowerSchool",     _POWERSCHOOL_VARIANTS),
    ("DeansList",       _DEANSLIST_VARIANTS),
    ("Infinite Campus", _INFINITE_CAMPUS_VARIANTS),
    ("TEAMS",           _TEAMS_VARIANTS),
    ("Generic",         _GENERIC_VARIANTS),
]


# ---------------------------------------------------------------------------
# Build the combined lookup at module load time
# ---------------------------------------------------------------------------

def _build_alias_lookup() -> dict[str, str]:
    """
    Merge all SIS variant dicts into a single flat lookup.
    Keys are normalized (lowercase + stripped) variants.
    Values are Atlas normalized field names.

    Raises ValueError if the same normalized variant maps to different
    targets in different SIS sections (unresolvable conflict).
    """
    lookup: dict[str, str] = {}
    for sis_name, variants in _ALL_SOURCES:
        for raw_variant, normalized_key in variants.items():
            normalized_variant = raw_variant.strip().lower()
            if normalized_variant in lookup:
                existing = lookup[normalized_variant]
                if existing != normalized_key:
                    raise ValueError(
                        f"Alias library conflict detected in '{sis_name}': "
                        f"variant '{raw_variant}' (normalized: '{normalized_variant}') "
                        f"maps to '{normalized_key}' but was already mapped to '{existing}'. "
                        f"Remove or reconcile the conflicting entry."
                    )
                # Same key, same target — harmless overlap, skip
                continue
            lookup[normalized_variant] = normalized_key
    return lookup


# Module-level alias lookup — built once, never mutated.
_ALIAS_LOOKUP: dict[str, str] = _build_alias_lookup()


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def resolve_columns(df: pd.DataFrame, file_label: str) -> dict[str, str]:
    """
    Resolve raw DataFrame column headers to Atlas normalized field names.

    Matching is deterministic: case-insensitive, whitespace-stripped, exact
    string match only. No fuzzy matching. No inference.

    Parameters
    ----------
    df : pd.DataFrame
        DataFrame whose columns will be inspected.
    file_label : str
        Human-readable label for the file (e.g. "incident" or "consequence").
        Used only in log messages.

    Returns
    -------
    dict[str, str]
        Mapping of {raw_header: normalized_key} for every column that
        matched a known alias variant. Unmatched columns are NOT included.
    """
    resolved: dict[str, str] = {}
    for col in df.columns:
        normalized_variant = col.strip().lower()
        if normalized_variant in _ALIAS_LOOKUP:
            normalized_key = _ALIAS_LOOKUP[normalized_variant]
            resolved[col] = normalized_key
            logger.info(
                "[column_mapper] %s: '%s' → '%s'",
                file_label, col, normalized_key,
            )
    return resolved


def get_unmatched_columns(
    df: pd.DataFrame,
    resolved_map: dict[str, str],
) -> list[str]:
    """
    Return raw column headers that had no match in the alias library.

    These are surfaced to the operator and never silently dropped.

    Parameters
    ----------
    df : pd.DataFrame
        DataFrame whose columns will be inspected.
    resolved_map : dict[str, str]
        The resolved alias map returned by resolve_columns().

    Returns
    -------
    list[str]
        Raw header strings for every column not present in resolved_map.
    """
    return [col for col in df.columns if col not in resolved_map]
