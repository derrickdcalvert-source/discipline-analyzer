"""
ATLAS DISCIPLINE INTELLIGENCE — CORE ANALYSIS ENGINE
Texas TEA Compliance Mode
Version: 2.0 (Updated Jan 2026)

Changes in this version:
- Instructional Impact moved to Section 3
- Per-grade table format for instructional loss
- Chronic absenteeism context added
"""

import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.figure import Figure
import pandas
import pandas as pd
import numpy as np
import hashlib
from datetime import datetime
# ============================================================================
# CONFIGURATION
# ============================================================================

STATE_MODE = "TEXAS_TEA"

# TEA Action Code Mapping (Texas Education Code Chapter 37)
TEA_ACTION_MAPPING = {
    'ISS': '06',
    'In-School Suspension': '06',
    'In School Suspension': '06',
    'OSS': '05',
    'Out-of-School Suspension': '05',
    'Out of School Suspension': '05',
    'DAEP': '07',
    'JJAEP': '13',
    'Expulsion': ['01', '02', '03', '04'],
    'Expelled': ['01', '02', '03', '04']
}
# ============================================================================
# FERPA COMPLIANCE - PII DETECTION
# ============================================================================

def check_for_pii_columns(df):
    """
    Scan dataframe columns for potential PII (Personally Identifiable Information).
    Returns tuple: (flagged_columns, clean_df)
    - flagged_columns: list of column names that may contain PII
    - clean_df: dataframe with PII columns removed
    """
    pii_patterns = [
        'name', 'first', 'last', 'fname', 'lname', 
        'student_name', 'full_name', 'studentname',
        'ssn', 'social', 'address', 'street',
        'phone', 'email', 'parent', 'guardian',
        'dob', 'birth', 'birthdate'
    ]
    
    flagged_columns = []
    for col in df.columns:
        col_lower = col.lower().replace('_', '').replace(' ', '').replace('-', '')
        for pattern in pii_patterns:
            if pattern in col_lower:
                flagged_columns.append(col)
                break
    
    # Create clean dataframe with PII columns removed
    safe_columns = [c for c in df.columns if c not in flagged_columns]
    clean_df = df[safe_columns].copy()
    
    return flagged_columns, clean_df


# ============================================================================
# FERPA COMPLIANCE - PII DETECTION
# ============================================================================

def check_for_pii_columns(df):
    """
    Scan dataframe columns for potential PII (Personally Identifiable Information).
    Returns tuple: (flagged_columns, clean_df)
    - flagged_columns: list of column names that may contain PII
    - clean_df: dataframe with PII columns removed
    """
    pii_patterns = [
        'name', 'first', 'last', 'fname', 'lname', 
        'student_name', 'full_name', 'studentname',
        'ssn', 'social', 'address', 'street',
        'phone', 'email', 'parent', 'guardian',
        'dob', 'birth', 'birthdate'
    ]
    
    flagged_columns = []
    for col in df.columns:
        col_lower = col.lower().replace('_', '').replace(' ', '').replace('-', '')
        for pattern in pii_patterns:
            if pattern in col_lower:
                flagged_columns.append(col)
                break
    
    # Create clean dataframe with PII columns removed
    safe_columns = [c for c in df.columns if c not in flagged_columns]
    clean_df = df[safe_columns].copy()
    
    return flagged_columns, clean_df

# ============================================================================
# TEA ACTION MAPPING
# ============================================================================

def apply_tea_mapping(df):
    """
    Map Response values to TEA action groups
    Adds Is_Removal column for analysis
    """
    
    df = df.copy()
    
    # Initialize TEA_Group column
    df['TEA_Group'] = 'LOCAL_ONLY'
    df['Is_Removal'] = False
    
    # Map responses to TEA groups
    for response in df['Response'].unique():
        response_upper = str(response).upper().strip()
        
        # ISS
        if any(x in response_upper for x in ['ISS', 'IN-SCHOOL', 'IN SCHOOL']):
            df.loc[df['Response'] == response, 'TEA_Group'] = 'ISS'
            df.loc[df['Response'] == response, 'Is_Removal'] = True
        
        # OSS
        elif any(x in response_upper for x in ['OSS', 'OUT-OF-SCHOOL', 'OUT OF SCHOOL']):
            df.loc[df['Response'] == response, 'TEA_Group'] = 'OSS'
            df.loc[df['Response'] == response, 'Is_Removal'] = True
        
        # DAEP
        elif 'DAEP' in response_upper or 'ALTERNATIVE' in response_upper:
            df.loc[df['Response'] == response, 'TEA_Group'] = 'DAEP'
            df.loc[df['Response'] == response, 'Is_Removal'] = True
        
        # JJAEP
        elif 'JJAEP' in response_upper or 'JUVENILE' in response_upper:
            df.loc[df['Response'] == response, 'TEA_Group'] = 'JJAEP'
            df.loc[df['Response'] == response, 'Is_Removal'] = True
        
        # Expulsion
        elif 'EXPUL' in response_upper or 'EXPELLED' in response_upper:
            df.loc[df['Response'] == response, 'TEA_Group'] = 'EXPULSION'
            df.loc[df['Response'] == response, 'Is_Removal'] = True
    
    return df

# ============================================================================
# STATISTICS CALCULATION
# ============================================================================

def calculate_school_brief_stats(df, state_mode="TEXAS_TEA"):
    """
    Calculate core statistics for School Campus Decision Brief
    """
    
    total = len(df)
    
    if total == 0:
        return {
            'total_incidents': 0,
            'LOCAL_ONLY': 0, 'LOCAL_ONLY_pct': 0,
            'ISS': 0, 'ISS_pct': 0,
            'OSS': 0, 'OSS_pct': 0,
            'DAEP': 0, 'DAEP_pct': 0,
            'JJAEP': 0, 'JJAEP_pct': 0,
            'Expulsion': 0, 'Expulsion_pct': 0,
            'total_removals': 0,
            'removal_pct': 0
        }
    
    # Count by TEA group
    tea_counts = df['TEA_Group'].value_counts().to_dict()
    
    stats = {
        'total_incidents': total,
        'LOCAL_ONLY': tea_counts.get('LOCAL_ONLY', 0),
        'ISS': tea_counts.get('ISS', 0),
        'OSS': tea_counts.get('OSS', 0),
        'DAEP': tea_counts.get('DAEP', 0),
        'JJAEP': tea_counts.get('JJAEP', 0),
        'Expulsion': tea_counts.get('EXPULSION', 0)
    }
    
    # Calculate percentages
    stats['LOCAL_ONLY_pct'] = (stats['LOCAL_ONLY'] / total * 100)
    stats['ISS_pct'] = (stats['ISS'] / total * 100)
    stats['OSS_pct'] = (stats['OSS'] / total * 100)
    stats['DAEP_pct'] = (stats['DAEP'] / total * 100)
    stats['JJAEP_pct'] = (stats['JJAEP'] / total * 100)
    stats['Expulsion_pct'] = (stats['Expulsion'] / total * 100)
    
    # Total removals
    stats['total_removals'] = df['Is_Removal'].sum()
    stats['removal_pct'] = (stats['total_removals'] / total * 100)
    
    return stats

# ============================================================================
# DISTRICT TEA STATISTICS
# ============================================================================

def calculate_district_tea_stats(df):
    """
    Calculate statistics for District TEA Compliance Report
    """
    
    total = len(df)
    tea_actions = df[df['Is_Removal'] == True]
    
    stats = {
        'total_incidents': total,
        'total_tea_actions': len(tea_actions),
        'tea_action_pct': (len(tea_actions) / total * 100) if total > 0 else 0,
        'tea_groups': df['TEA_Group'].value_counts().to_dict()
    }
    
    return stats

# ============================================================================
# INSTRUCTIONAL IMPACT ANALYSIS (UPDATED)
# ============================================================================

def analyze_instructional_impact(df, state_mode="TEXAS_TEA"):
    """
    Calculate instructional time lost due to disciplinary removals
    Returns dict with grade-level breakdown for table formatting
    """
    
    # Check if Days_Removed exists
    if 'Days_Removed' not in df.columns:
        return {
            'suppressed': True,
            'reason': 'Days_Removed data not available in uploaded file',
            'total_minutes': 0,
            'total_days': 0,
            'grade_distribution': {}
        }
    
    # Filter for removal actions only
    if state_mode == "TEXAS_TEA":
        removal_df = df[df['Is_Removal'] == True].copy()
    else:
        removal_responses = ['ISS', 'OSS', 'Expulsion']
        removal_df = df[df['Response'].isin(removal_responses)].copy()
    
    # Check if we have any Days_Removed data
    removal_df = removal_df[removal_df['Days_Removed'].notna()].copy()
    
    if len(removal_df) == 0:
        return {
            'suppressed': True,
            'reason': 'No Days_Removed data available for removal incidents',
            'total_minutes': 0,
            'total_days': 0,
            'grade_distribution': {}
        }
    
    # Convert Days_Removed to numeric
    removal_df['Days_Removed'] = pd.to_numeric(removal_df['Days_Removed'], errors='coerce')
    removal_df = removal_df[removal_df['Days_Removed'] > 0].copy()
    
    if len(removal_df) == 0:
        return {
            'suppressed': True,
            'reason': 'No valid Days_Removed values found',
            'total_minutes': 0,
            'total_days': 0,
            'grade_distribution': {}
        }
    
    # Default: High school minutes per day
    MINUTES_PER_DAY = 390
    
    # Calculate total impact
    total_days = removal_df['Days_Removed'].sum()
    total_minutes = total_days * MINUTES_PER_DAY
    
    # Calculate by grade
    grade_distribution = {}
    for grade in sorted(removal_df['Grade'].unique(), key=lambda x: (str(x).isdigit() is False, str(x))):
        grade_data = removal_df[removal_df['Grade'] == grade]
        grade_days = grade_data['Days_Removed'].sum()
        grade_minutes = grade_days * MINUTES_PER_DAY
        
        grade_distribution[grade] = {
            'Days_Removed': grade_days,
            'Minutes_Lost': grade_minutes
        }
    
    return {
        'suppressed': False,
        'reason': None,
        'total_minutes': int(total_minutes),
        'total_days': round(total_days, 1),
        'grade_distribution': grade_distribution
    }
# Backward compatibility alias
def calculate_instructional_impact(df, state_mode="TEXAS_TEA"):
    """Backward compatiibility wrapper"""
    return analyze_instructional_impact(df, state_mode)

# ============================================================================
# EQUITY PATTERN ANALYSIS
# ============================================================================

def analyze_equity_patterns(df, state_mode="TEXAS_TEA"):
    """
    Analyze equity patterns in removal rates
    Only reports when subgroup N >= 10 (FERPA compliance)
    """
    
    MIN_N = 10
    campus_removal_rate = (df['Is_Removal'].sum() / len(df) * 100) if len(df) > 0 else 0
    
    equity_data = {
        'suppressed': False,
        'reason': None,
        'by_race': {},
        'by_gender': {},
        'by_special_population': {}
    }
    
    # Analyze by Race (if column exists)
    if 'Race' in df.columns:
        for race in df['Race'].unique():
            if pd.isna(race):
                continue
            race_df = df[df['Race'] == race]
            if len(race_df) >= MIN_N:
                removal_rate = (race_df['Is_Removal'].sum() / len(race_df) * 100)
                equity_data['by_race'][race] = {
                    'count': len(race_df),
                    'removals': int(race_df['Is_Removal'].sum()),
                    'removal_rate': removal_rate
                }
    
    # Analyze by Gender (if column exists)
    if 'Gender' in df.columns:
        for gender in df['Gender'].unique():
            if pd.isna(gender):
                continue
            gender_df = df[df['Gender'] == gender]
            if len(gender_df) >= MIN_N:
                removal_rate = (gender_df['Is_Removal'].sum() / len(gender_df) * 100)
                equity_data['by_gender'][gender] = {
                    'count': len(gender_df),
                    'removals': int(gender_df['Is_Removal'].sum()),
                    'removal_rate': removal_rate
                }
    
    # Analyze by Special Population (if column exists)
    if 'Special_Population' in df.columns:
        for pop in df['Special_Population'].unique():
            if pd.isna(pop):
                continue
            pop_df = df[df['Special_Population'] == pop]
            if len(pop_df) >= MIN_N:
                removal_rate = (pop_df['Is_Removal'].sum() / len(pop_df) * 100)
                equity_data['by_special_population'][pop] = {
                    'count': len(pop_df),
                    'removals': int(pop_df['Is_Removal'].sum()),
                    'removal_rate': removal_rate
                }
    
    # Check if we have any reportable data
    has_data = (len(equity_data['by_race']) > 0 or 
                len(equity_data['by_gender']) > 0 or 
                len(equity_data['by_special_population']) > 0)
    
    if not has_data:
        equity_data['suppressed'] = True
        equity_data['reason'] = 'No subgroups meet minimum N >= 10 reporting threshold (FERPA compliance)'
    
    return equity_data

# ============================================================================
# DECISION POSTURE (TEXAS MODE)
# ============================================================================

def determine_posture_texas(stats):
    """
    Determine Decision Posture using Texas TEA rules
    """
    
    total = stats['total_incidents']
    
    if total == 0:
        return "STABLE", "Stable"
    
    # Calculate removal percentages
    removal_pct = stats['removal_pct']
    oss_pct = stats['OSS_pct']
    expulsion_count = stats['Expulsion']
    
    # ESCALATE
    if removal_pct >= 60 or oss_pct >= 20 or expulsion_count > 0:
        return "ESCALATE", "Escalating"
    
    # INTERVENE
    if (removal_pct >= 45 and removal_pct < 60) or (oss_pct >= 15 and oss_pct < 20):
        return "INTERVENE", "Drifting → Early Escalation Pressure"
    
    # CALIBRATE
    if (removal_pct >= 35 and removal_pct < 45) or (oss_pct >= 10 and oss_pct < 15):
        return "CALIBRATE", "Elevated Pressure"
    
    # STABLE
    return "STABLE", "Stable"

# ============================================================================
# SCHOOL CAMPUS DECISION BRIEF (UPDATED WITH SECTION 3 INSTRUCTIONAL IMPACT)
# ============================================================================

def generate_school_brief(df, campus_name="School Campus", state_mode="TEXAS_TEA"):
    """
    Generate School Campus Decision Brief (Principal-Facing)
    Updated: Instructional Impact moved to Section 3
    """
    
    # Calculate all required metrics
    stats = calculate_school_brief_stats(df, state_mode)
    posture, system_state = determine_posture_texas(stats)
    impact = analyze_instructional_impact(df, state_mode)
    equity = analyze_equity_patterns(df, state_mode)
    
    # Generate data hash
    data_hash = hashlib.md5(df.to_string().encode()).hexdigest()
    
    # Start building the brief
    brief = ""
    brief += "=" * 80 + "\n"
    brief += "ATLAS DISCIPLINE INTELLIGENCE — SCHOOL CAMPUS DECISION BRIEF\n"
    brief += "=" * 80 + "\n\n"
    
    # ========================================================================
    # SECTION 1: HEADER
    # ========================================================================
    
    brief += f"**Campus:** {campus_name}\n"
    brief += f"**Date Range:** {df['Date'].min()} to {df['Date'].max()}\n"
    brief += f"**State Mode:** {state_mode}\n"
    brief += f"**Data Hash:** {data_hash[:16]}...\n"
    brief += f"**Rows Analyzed:** {len(df):,}\n"
    brief += f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
    
    # ========================================================================
    # SECTION 2: DISCIPLINE SYSTEM STATUS — AT A GLANCE
    # ========================================================================
    
    brief += "## DISCIPLINE SYSTEM STATUS — AT A GLANCE\n\n"
    brief += f"**Overall System State:** {system_state}\n\n"
    brief += f"**Decision Posture:** {posture}\n\n"
    
    # Leadership interpretation
    removal_pct = stats['removal_pct']
    if posture == "ESCALATE":
        brief += f"**Leadership Interpretation:** System pressure exceeds intervention thresholds. Removal rate at {removal_pct:.1f}% requires immediate executive attention.\n\n"
    elif posture == "INTERVENE":
        brief += f"**Leadership Interpretation:** System trending toward crisis thresholds. Removal rate at {removal_pct:.1f}% demands active monitoring and targeted intervention.\n\n"
    elif posture == "CALIBRATE":
        brief += f"**Leadership Interpretation:** System pressure elevated but manageable. Removal rate at {removal_pct:.1f}% approaching intervention threshold.\n\n"
    else:
        brief += f"**Leadership Interpretation:** System operating within normal parameters. Removal rate at {removal_pct:.1f}% remains stable.\n\n"
    
    brief += "─" * 80 + "\n\n"
    
    # ========================================================================
    # SECTION 3: INSTRUCTIONAL IMPACT (MOVED FROM SECTION 10)
    # ========================================================================
    
    brief += "## INSTRUCTIONAL IMPACT\n\n"
    
    if impact['suppressed']:
        brief += f"*Section suppressed: {impact['reason']}*\n\n"
    else:
        brief += "**Impact by Grade:**\n\n"
        brief += "```\n"
        
        # Sort by grade and display in table format
        for grade in sorted(impact['grade_distribution'].keys(), key=lambda x: int(x) if str(x).isdigit() else -1):
            data = impact['grade_distribution'][grade]
            days = data['Days_Removed']
            minutes = data['Minutes_Lost']
            brief += f"Grade {str(grade):>2}: {int(minutes):>6,} minutes ({days:>5.1f} days)\n"
        
        brief += "─" * 40 + "\n"
        brief += f"TOTAL:    {impact['total_minutes']:>6,} minutes ({impact['total_days']:>5.1f} days)\n"
        brief += "```\n\n"
        
        # STAAR & Accountability Context (UPDATED WITH CHRONIC ABSENTEEISM)
        brief += "**STAAR & Accountability Context:**\n\n"
        brief += "Sustained instructional loss at this magnitude is associated in Texas accountability research with lower STAAR performance, particularly when loss exceeds multiple weeks at the grade level.\n\n"
        brief += "Under Texas accountability, students removed from instruction for 10% or more of enrolled days meet the chronic absenteeism threshold. Disciplinary removals count toward this metric and affect campus ratings in the Academic Achievement domain.\n\n"
    
    brief += "─" * 80 + "\n\n"
    
    # ========================================================================
    # SECTION 4: RESPONSE / REMOVAL SNAPSHOT
    # ========================================================================
    
    brief += "## RESPONSE / REMOVAL SNAPSHOT\n\n"
    brief += f"**Total Incidents:** {stats['total_incidents']}\n\n"
    
    brief += "**Response Distribution:**\n\n"
    brief += f"- LOCAL_ONLY: {stats['LOCAL_ONLY']} ({stats['LOCAL_ONLY_pct']:.1f}%)\n"
    brief += f"- ISS: {stats['ISS']} ({stats['ISS_pct']:.1f}%)\n"
    brief += f"- OSS: {stats['OSS']} ({stats['OSS_pct']:.1f}%)\n"
    brief += f"- DAEP: {stats['DAEP']} ({stats['DAEP_pct']:.1f}%)\n"
    brief += f"- JJAEP: {stats['JJAEP']} ({stats['JJAEP_pct']:.1f}%)\n"
    brief += f"- EXPULSION: {stats['Expulsion']} ({stats['Expulsion_pct']:.1f}%)\n\n"
    
    brief += f"**Total Removals:** {stats['total_removals']} ({stats['removal_pct']:.1f}%)\n\n"
    
    brief += "─" * 80 + "\n\n"
    
    # ========================================================================
    # SECTION 5: GRADE-LEVEL PRESSURE ANALYSIS
    # ========================================================================
    
    brief += "## GRADE-LEVEL PRESSURE ANALYSIS\n\n"
    
    grade_analysis = df.groupby('Grade').agg({
        'Response': 'count',
        'Is_Removal': 'sum'
    }).reset_index()
    grade_analysis['Removal_Rate'] = (grade_analysis['Is_Removal'] / grade_analysis['Response'] * 100)
    grade_analysis['Variance'] = grade_analysis['Removal_Rate'] - stats['removal_pct']
    grade_analysis = grade_analysis.sort_values('Grade', key=lambda x: x.apply(lambda g: int(g) if str(g).isdigit() else -1))
    
    brief += "**Removal Rate by Grade:**\n\n"
    for _, row in grade_analysis.iterrows():
        variance_sign = "+" if row['Variance'] >= 0 else ""
        brief += f"- Grade {row['Grade']}: {row['Removal_Rate']:.1f}% ({variance_sign}{row['Variance']:.1f}% vs campus avg)\n"
    
    brief += "\n"
    brief += "─" * 80 + "\n\n"
    
    # ========================================================================
    # SECTION 6: TOP INCIDENT TYPES
    # ========================================================================
    
    brief += "## TOP INCIDENT TYPES\n\n"
    
    incident_analysis = df.groupby('Incident_Type').agg({
        'Response': 'count',
        'Is_Removal': 'sum'
    }).reset_index()
    incident_analysis['Removal_Rate'] = (incident_analysis['Is_Removal'] / incident_analysis['Response'] * 100)
    incident_analysis = incident_analysis.sort_values('Response', ascending=False)
    
    brief += "**Top 3 by Volume:**\n\n"
    for _, row in incident_analysis.head(3).iterrows():
        brief += f"- {row['Incident_Type']}: {int(row['Response'])} incidents, {row['Removal_Rate']:.1f}% removal rate\n"
    
    brief += "\n"
    brief += "─" * 80 + "\n\n"
    
    # ========================================================================
    # SECTION 7: LOCATION HOTSPOTS
    # ========================================================================
    
    brief += "## LOCATION HOTSPOTS\n\n"
    
    location_analysis = df.groupby('Location').agg({
        'Response': 'count',
        'Is_Removal': 'sum'
    }).reset_index()
    location_analysis['Removal_Rate'] = (location_analysis['Is_Removal'] / location_analysis['Response'] * 100)
    location_analysis = location_analysis.sort_values('Response', ascending=False)
    
    brief += "**Top 3 Locations:**\n\n"
    for _, row in location_analysis.head(3).iterrows():
        brief += f"- {row['Location']}: {int(row['Response'])} incidents, {row['Removal_Rate']:.1f}% removal rate\n"
    
    brief += "\n"
    brief += "─" * 80 + "\n\n"
    
    # ========================================================================
    # SECTION 8: TIME BLOCK PATTERNS
    # ========================================================================
    
    brief += "## TIME BLOCK PATTERNS\n\n"
    
    time_analysis = df.groupby('Time_Block').agg({
        'Response': 'count',
        'Is_Removal': 'sum'
    }).reset_index()
    time_analysis['Removal_Rate'] = (time_analysis['Is_Removal'] / time_analysis['Response'] * 100)
    time_analysis = time_analysis.sort_values('Response', ascending=False)
    
    brief += "**Incident Concentration:**\n\n"
    for _, row in time_analysis.head(3).iterrows():
        brief += f"- {row['Time_Block']}: {int(row['Response'])} incidents, {row['Removal_Rate']:.1f}% removal rate\n"
    
    brief += "\n"
    brief += "─" * 80 + "\n\n"
    
    # ========================================================================
    # SECTION 9: BEHAVIORAL PRESSURE SIGNAL
    # ========================================================================
    
    brief += "## BEHAVIORAL PRESSURE SIGNAL\n\n"
    
    # Top removal-driving incident type
    top_removal_incident = incident_analysis.sort_values('Is_Removal', ascending=False).iloc[0]
    top_removal_location = location_analysis.sort_values('Is_Removal', ascending=False).iloc[0]
    top_removal_time = time_analysis.sort_values('Is_Removal', ascending=False).iloc[0]
    
    brief += f"**What drives system pressure:** {top_removal_incident['Incident_Type']} incidents account for {int(top_removal_incident['Is_Removal'])} removals ({(top_removal_incident['Is_Removal']/stats['total_removals']*100):.1f}% of total).\n\n"
    brief += f"**Where it concentrates:** {top_removal_location['Location']} and {top_removal_time['Time_Block']}.\n\n"
    brief += f"**Why it matters:** This behavior pattern converts to removal at {top_removal_incident['Removal_Rate']:.1f}% rate, directly driving current posture.\n\n"
    
    brief += "─" * 80 + "\n\n"
    
    # ========================================================================
    # SECTION 10: TOP RISK
    # ========================================================================
    
    brief += "## TOP RISK (URGENT ATTENTION)\n\n"
    
    # Generate specific risk assessment
    if posture == "ESCALATE":
        top_grade = grade_analysis.iloc[0]
        brief += f"**What is breaking:** Grade {top_grade['Grade']} operates at {top_grade['Removal_Rate']:.1f}% removal rate. "
        brief += f"{top_removal_incident['Incident_Type']} incidents in {top_removal_location['Location']} convert to removal at {top_removal_incident['Removal_Rate']:.1f}%.\n\n"
        brief += f"**Where leadership attention must go:** Immediate focus on Grade {top_grade['Grade']} during {top_removal_time['Time_Block']}. "
        brief += f"System cannot sustain current removal rate without operational consequences.\n\n"
    elif posture == "INTERVENE":
        brief += f"**What is breaking:** Removal rate approaching crisis threshold. {top_removal_incident['Incident_Type']} incidents driving system pressure.\n\n"
        brief += f"**Where leadership attention must go:** Monitor Grade {grade_analysis.iloc[0]['Grade']} closely. Deploy targeted support to {top_removal_location['Location']}.\n\n"
    elif posture == "CALIBRATE":
        brief += f"**What is breaking:** System trending toward intervention levels. Early pressure signals in Grade {grade_analysis.iloc[0]['Grade']}.\n\n"
        brief += f"**Where leadership attention must go:** Active monitoring of {top_removal_incident['Incident_Type']} incidents. Prevent escalation through early intervention.\n\n"
    else:
        brief += "**Current assessment:** No immediate crisis indicators. System operating within normal parameters. Continue routine monitoring.\n\n"
    
    brief += "─" * 80 + "\n\n"
    
    # ========================================================================
    # SECTION 11: EQUITY PATTERN SUMMARY
    # ========================================================================
    
    brief += "## EQUITY PATTERN SUMMARY\n\n"
    
    if equity['suppressed']:
        brief += f"*Section suppressed: {equity['reason']}*\n\n"
    else:
        brief += "**Removal Rate by Subgroup (N ≥ 10 only):**\n\n"
        
        if equity['by_race']:
            brief += "**By Race:**\n"
            for race, data in equity['by_race'].items():
                ratio = data['removal_rate'] / stats['removal_pct'] if stats['removal_pct'] > 0 else 0
                brief += f"- {race}: {data['removal_rate']:.1f}% ({ratio:.2f}x campus avg)\n"
            brief += "\n"
        
        if equity['by_gender']:
            brief += "**By Gender:**\n"
            for gender, data in equity['by_gender'].items():
                ratio = data['removal_rate'] / stats['removal_pct'] if stats['removal_pct'] > 0 else 0
                brief += f"- {gender}: {data['removal_rate']:.1f}% ({ratio:.2f}x campus avg)\n"
            brief += "\n"
        
        if equity['by_special_population']:
            brief += "**By Special Population:**\n"
            for pop, data in equity['by_special_population'].items():
                ratio = data['removal_rate'] / stats['removal_pct'] if stats['removal_pct'] > 0 else 0
                brief += f"- {pop}: {data['removal_rate']:.1f}% ({ratio:.2f}x campus avg)\n"
            brief += "\n"
    
    brief += "─" * 80 + "\n\n"
    
    # ========================================================================
    # SECTION 12: WATCH LIST
    # ========================================================================
    
    brief += "## WATCH LIST (MONITOR FOR ESCALATION)\n\n"
    
    watch_items = []
    
    # Check for grades approaching threshold
    for _, row in grade_analysis.iterrows():
        if 30 <= row['Removal_Rate'] < 45:
            watch_items.append(f"Grade {row['Grade']} at {row['Removal_Rate']:.1f}% removal rate (approaching calibration threshold)")
    
    # Check for OSS approaching threshold
    if 8 <= stats['OSS_pct'] < 15:
        watch_items.append(f"OSS usage at {stats['OSS_pct']:.1f}% (monitor for 15% threshold)")
    
    # Check for locations with high removal rates
    for _, row in location_analysis.head(3).iterrows():
        if row['Removal_Rate'] > stats['removal_pct'] * 1.2:
            watch_items.append(f"{row['Location']} converting to removal at {row['Removal_Rate']:.1f}% (above campus avg)")
    
    if watch_items:
        for item in watch_items:
            brief += f"- {item}\n"
    else:
        brief += "No patterns currently flagged for monitoring.\n"
    
    brief += "\n"
    brief += "─" * 80 + "\n\n"
    
    # ========================================================================
    # SECTION 13: POSTURE BOUNDARIES
    # ========================================================================
    
    brief += "## POSTURE BOUNDARIES (THRESHOLD REFERENCE)\n\n"
    
    brief += "**STABLE:** Removal < 35%, OSS < 10%, Expulsions = 0\n"
    brief += "**CALIBRATE:** Removal 35-44%, OSS < 15%\n"
    brief += "**INTERVENE:** Removal 45-59%, OSS < 20%\n"
    brief += "**ESCALATE:** Removal ≥ 60% OR OSS ≥ 20% OR Expulsions present\n\n"
    
    brief += f"**Current Position:**\n"
    brief += f"- Removal Rate: {stats['removal_pct']:.1f}%\n"
    brief += f"- OSS Rate: {stats['OSS_pct']:.1f}%\n"
    brief += f"- Expulsions: {stats['Expulsion']}\n"
    brief += f"- Posture: {posture}\n\n"
    
    brief += "─" * 80 + "\n\n"
    
    # ========================================================================
    # SECTION 14: BOTTOM LINE FOR LEADERSHIP
    # ========================================================================
    
    brief += "## BOTTOM LINE FOR LEADERSHIP\n\n"
    
    if posture == "ESCALATE":
        brief += f"Campus discipline system operates in crisis mode at {stats['removal_pct']:.1f}% removal rate. "
        brief += f"Grade {grade_analysis.iloc[0]['Grade']} drives system pressure through {top_removal_incident['Incident_Type']} incidents. "
        brief += f"Current trajectory unsustainable. Executive intervention required immediately.\n\n"
    elif posture == "INTERVENE":
        brief += f"System pressure approaching crisis thresholds at {stats['removal_pct']:.1f}% removal. "
        brief += f"Targeted action needed in Grade {grade_analysis.iloc[0]['Grade']} and {top_removal_location['Location']}. "
        brief += f"Window for preventive intervention closing.\n\n"
    elif posture == "CALIBRATE":
        brief += f"System trending toward intervention zone at {stats['removal_pct']:.1f}% removal. "
        brief += f"Monitor {top_removal_incident['Incident_Type']} incidents closely. "
        brief += f"Early action can prevent escalation.\n\n"
    else:
        brief += f"System stable at {stats['removal_pct']:.1f}% removal rate. "
        brief += f"Continue routine monitoring. No immediate action required.\n\n"
    
    brief += "=" * 80 + "\n"
    brief += "END OF SCHOOL CAMPUS DECISION BRIEF\n"
    brief += "=" * 80 + "\n"
    
    return brief

# ============================================================================
# DISTRICT TEA COMPLIANCE REPORT
# ============================================================================

def generate_district_tea_report(df, campus_name="School Campus"):
    """
    Generate District TEA Compliance Report (District-Facing)
    """
    
    stats = calculate_district_tea_stats(df)
    data_hash = hashlib.md5(df.to_string().encode()).hexdigest()
    
    report = ""
    report += "=" * 80 + "\n"
    report += "ATLAS DISCIPLINE INTELLIGENCE — DISTRICT TEA COMPLIANCE REPORT\n"
    report += "=" * 80 + "\n\n"
    
    report += f"**Campus:** {campus_name}\n"
    report += f"**Date Range:** {df['Date'].min()} to {df['Date'].max()}\n"
    report += f"**Data Hash:** {data_hash[:16]}...\n"
    report += f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
    report += "─" * 80 + "\n\n"
    
    # TEA Action Summary
    report += "## TEA ACTION SUMMARY\n\n"
    report += f"**Total Incidents:** {stats['total_incidents']}\n"
    report += f"**Total TEA Actions:** {stats['total_tea_actions']} ({stats['tea_action_pct']:.1f}%)\n\n"
    
    report += "**TEA Action Groups:**\n\n"
    for group, count in sorted(stats['tea_groups'].items()):
        pct = (count / stats['total_incidents'] * 100) if stats['total_incidents'] > 0 else 0
        report += f"- {group}: {count} ({pct:.1f}%)\n"
    
    report += "\n"
    report += "─" * 80 + "\n\n"
    
    # Data Quality Note
    report += "## DATA QUALITY NOTES\n\n"
    
    has_tea_codes = 'TEA_Action_Code' in df.columns
    has_reason_codes = 'TEA_Action_Reason_Code' in df.columns
    has_days_removed = 'Days_Removed' in df.columns
    
    report += f"- TEA Action Codes present: {'Yes' if has_tea_codes else 'No'}\n"
    report += f"- TEA Reason Codes present: {'Yes' if has_reason_codes else 'No'}\n"
    report += f"- Days_Removed data present: {'Yes' if has_days_removed else 'No'}\n\n"
    
    if not has_reason_codes:
        report += "**Note:** Cannot validate statutory compliance without TEA Action Reason Codes.\n\n"
    
    report += "=" * 80 + "\n"
    report += "END OF DISTRICT TEA COMPLIANCE REPORT\n"
    report += "=" * 80 + "\n"
    
    return report
# =============================================================================
# DISTRICT CONSOLIDATED REPORT GENERATION
# =============================================================================

def generate_district_consolidated_report(campus_results, district_name="District (All Campuses)"):
    """
    Generate consolidated district report with same 14-section structure as School Brief
    
    Args:
        campus_results: Dictionary of {campus_name: {df, stats, posture, system_state, impact, brief}}
        district_name: Name for the district
        
    Returns:
        String containing formatted district report
    """
    from datetime import datetime
    import hashlib
    
    # Extract dataframes correctly
    all_dfs = []
    for campus_name, result in campus_results.items():
        if isinstance(result, dict) and 'df' in result:
            all_dfs.append(result['df'])
    # Combine dataframes
    if len(all_dfs) == 0:
        raise ValueError("No dataframes found in campus_results")
    elif len(all_dfs) == 1:
        district_df = all_dfs[0]
    else:
        district_df = pd.concat(all_dfs, ignore_index=True)

    # Determine district posture
    district_stats = calculate_school_brief_stats(district_df)

    district_posture, district_system_state = determine_posture_texas(district_stats)

    # Calculate district impact
    district_impact = calculate_instructional_impact(district_df)
    
    # Build header
    date_range_start = district_df['Date'].min()
    date_range_end = district_df['Date'].max()
    data_hash = hashlib.md5(str(len(district_df)).encode()).hexdigest()[:16]
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    report = f"""{'='*80}
ATLAS DISCIPLINE INTELLIGENCE — DISTRICT CONSOLIDATED REPORT
{'='*80}

**District:** {district_name}
**Campuses:** {len(campus_results)}
**Date Range:** {date_range_start} to {date_range_end}
**State Mode:** TEXAS_TEA
**Data Hash:** {data_hash}...
**Generated:** {timestamp}

{'─'*80}

## DISCIPLINE SYSTEM STATUS — AT A GLANCE

**Overall System State:** {district_system_state}
**Decision Posture:** {district_posture}
**Leadership Interpretation:** District operates at {district_stats['removal_pct']:.1f}% removal rate across {len(campus_results)} campuses. {len([c for c in campus_results.values() if c['posture'] in ['ESCALATE', 'INTERVENE']])} campus(es) require immediate attention.

{'─'*80}

## RESPONSE / REMOVAL SNAPSHOT

**Total Incidents:** {district_stats['total_incidents']}

**Response Distribution:**
- LOCAL_ONLY: {district_stats['LOCAL_ONLY']} ({district_stats['LOCAL_ONLY_pct']:.1f}%)
- ISS: {district_stats['ISS']} ({district_stats['ISS_pct']:.1f}%)
- OSS: {district_stats['OSS']} ({district_stats['OSS_pct']:.1f}%)
- DAEP: {district_stats['DAEP']} ({district_stats['DAEP_pct']:.1f}%)
- JJAEP: {district_stats['JJAEP']} ({district_stats['JJAEP_pct']:.1f}%)
- EXPULSION: {district_stats['Expulsion']} ({district_stats['Expulsion_pct']:.1f}%)

**Total Removals:** {district_stats['total_removals']} ({district_stats['removal_pct']:.1f}%)

{'─'*80}

## CAMPUS-LEVEL POSTURE ANALYSIS

## CAMPUS-LEVEL POSTURE ANALYSIS

**Posture Distribution:**
"""
    
    # Count campuses by posture
    posture_counts = {}
    for result in campus_results.values():
        p = result['posture']
        posture_counts[p] = posture_counts.get(p, 0) + 1
    
    for posture in ['ESCALATE', 'INTERVENE', 'CALIBRATE', 'STABLE']:
        count = posture_counts.get(posture, 0)
        report += f"- {posture}: {count} campus(es)\n"
    
    report += f"\n**High-Priority Campuses:**\n"
    watchlist = [(name, r) for name, r in campus_results.items() if r['posture'] in ['ESCALATE', 'INTERVENE']]
    if watchlist:
        for campus_name, result in sorted(watchlist, key=lambda x: x[1]['stats']['removal_pct'], reverse=True):
            report += f"- {campus_name}: {result['posture']} — {result['stats']['removal_pct']:.1f}% removal rate\n"
    else:
        report += "- None requiring immediate attention\n"
    
    report += f"\n{'─'*80}\n\n"
    
    # Top incident types (district-wide)
    incident_counts = district_df['Incident_Type'].value_counts().head(3)
    report += "## TOP INCIDENT TYPES (DISTRICT-WIDE)\n\n**Top 3 by Volume:**\n"
    for incident_type, count in incident_counts.items():
        incidents_of_type = district_df[district_df['Incident_Type'] == incident_type]
        removals = incidents_of_type[incidents_of_type['Response'].isin(['ISS', 'OSS', 'DAEP', 'JJAEP', 'Expulsion'])].shape[0]
        removal_rate = (removals / count * 100) if count > 0 else 0
        report += f"- {incident_type}: {count} incidents, {removal_rate:.1f}% removal rate\n"
    
    report += f"\n{'─'*80}\n\n"
    
# Instructional Impact
    report += "## INSTRUCTIONAL IMPACT (DISTRICT-WIDE)\n\n"
    
    # Calculate total from all campuses
    total_minutes = sum(r['impact'].get('total_minutes', 0) for r in campus_results.values() if r.get('impact'))
    total_days = sum(r['impact'].get('total_days', 0) for r in campus_results.values() if r.get('impact'))
    
    if total_days > 0:
        report += f"**TOTAL:** {total_minutes:,.0f} minutes ({total_days:.1f} days)\n\n"
        report += "**Impact by Campus:**\n"
        for campus_name, result in sorted(campus_results.items(), key=lambda x: x[1]['impact'].get('total_days', 0), reverse=True):
            days = result['impact'].get('total_days', 0)
            if days > 0:
                report += f"- {campus_name}: {days:.1f} days\n"
        
        report += "\n**STAAR & Accountability Context:**\n"
        report += "Sustained instructional loss at this magnitude is associated in Texas accountability research with lower STAAR performance, particularly when loss exceeds multiple weeks at the grade level.\n"
    else:
        report += "*Instructional impact data not available*\n"
    
    report += f"\n{'─'*80}\n\n"
    
    # Bottom line
    report += "## BOTTOM LINE FOR DISTRICT LEADERSHIP\n\n"
    escalate_count = len([c for c in campus_results.values() if c['posture'] == 'ESCALATE'])
    intervene_count = len([c for c in campus_results.values() if c['posture'] == 'INTERVENE'])
    
    # Posture-appropriate district language
    if district_posture == 'ESCALATE':
        report += f"District faces crisis-level pressure with {escalate_count} campus(es) in ESCALATE posture. "
    elif district_posture == 'INTERVENE':
        report += f"District requires coordinated intervention with {intervene_count + escalate_count} campus(es) at elevated posture. "
    elif district_posture == 'CALIBRATE':
        report += f"District shows elevated pressure requiring monitoring. "
        if escalate_count > 0:
            report += f"{escalate_count} campus(es) require immediate attention. "
    else:  # STABLE
        report += "District operates within expected parameters. "
    
    report += f"District-wide removal rate at {district_stats['removal_pct']:.1f}%.\n"
    
    report += f"\n{'='*80}\n"
    report += "END OF DISTRICT CONSOLIDATED REPORT\n"
    report += f"{'='*80}\n"
    
    return report
"""
POSTURE GAUGE FUNCTION

Required imports (add to top of discipline_analyzer.py):
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.figure import Figure
"""
# =============================================================================
# CHART GENERATION FUNCTIONS FOR PDF INTEGRATION
# =============================================================================
# Add these functions to discipline_analyzer.py before the posture gauge function

import numpy as np

def calculate_grade_removal_rates(df):
    """
    Calculate removal rates by grade level for chart generation.
    
    Parameters:
    -----------
    df : pandas.DataFrame
        Must have 'Grade' and 'Is_Removal' columns
    
    Returns:
    --------
    tuple : (grade_data dict, campus_avg float)
    """
    # Count total incidents and removals by grade
    grade_stats = df.groupby('Grade').agg({
        'Is_Removal': ['count', 'sum']
    }).reset_index()
    
    grade_stats.columns = ['Grade', 'total_incidents', 'removal_incidents']
    
    # Calculate removal rate per grade
    grade_stats['removal_rate'] = (grade_stats['removal_incidents'] / grade_stats['total_incidents'] * 100).round(1)
    
    # Create dictionary for chart
    grade_data = dict(zip(grade_stats['Grade'].astype(str), grade_stats['removal_rate']))
    
    # Calculate campus-wide average removal rate
    total_incidents = len(df)
    total_removals = df['Is_Removal'].sum()
    campus_avg = round((total_removals / total_incidents * 100), 1) if total_incidents > 0 else 0
    
    return grade_data, campus_avg


def generate_grade_level_removal_chart_pdf(grade_data, campus_avg):
    """
    Generate grade-level removal rate chart as matplotlib Figure for PDF embedding.
    
    Returns:
    --------
    matplotlib.figure.Figure : Chart figure ready for PDF embedding
    """
    if not grade_data:
        return None
    
    # Sort grades in logical order (K, 1-12)
    grade_order = ['K', '1', '2', '3', '4', '5', '6', '7', '8', '9', '10', '11', '12']
    
    # Filter to only grades present in data and maintain order
    grades = [g for g in grade_order if g in grade_data]
    removal_rates = [grade_data[g] for g in grades]
    
    if not grades:
        return None
    
    # Determine colors based on variance from campus average
    colors = ['#FF8C42' if rate > campus_avg else '#5B7C99' for rate in removal_rates]
    
    # Create figure
    fig, ax = plt.subplots(figsize=(8, 5))
    
    # Create horizontal bars
    y_pos = np.arange(len(grades))
    bars = ax.barh(y_pos, removal_rates, color=colors, alpha=0.85, edgecolor='white', linewidth=1.5)
    
    # Add campus average reference line
    ax.axvline(campus_avg, color='#2C3E50', linestyle='--', linewidth=2, zorder=3)
    
    # Add value labels on bars
    for i, (bar, rate) in enumerate(zip(bars, removal_rates)):
        ax.text(rate + 1, i, f'{rate:.1f}%', va='center', fontsize=9, fontweight='bold')
    
    # Styling
    ax.set_yticks(y_pos)
    ax.set_yticklabels(grades, fontsize=10)
    ax.set_xlabel('Removal Rate (%)', fontsize=11, fontweight='bold')
    ax.set_title('Grade-Level Removal Rates', fontsize=12, fontweight='bold', pad=15)
    ax.set_xlim(0, max(removal_rates) + 10 if removal_rates else 100)
    ax.grid(axis='x', alpha=0.3, linestyle=':')
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    
    # Legend
    import matplotlib.patches as mpatches
    orange_patch = mpatches.Patch(color='#FF8C42', label='Above Campus Avg', alpha=0.85)
    blue_patch = mpatches.Patch(color='#5B7C99', label='At/Below Avg', alpha=0.85)
    ax.legend(handles=[orange_patch, blue_patch], 
              loc='upper right', frameon=False, fontsize=9)
    
    plt.tight_layout()
    
    return fig


def calculate_time_block_distribution(df):
    """
    Calculate incident distribution by time block for chart generation.
    
    Parameters:
    -----------
    df : pandas.DataFrame
        Must have 'Time_Block' column
    
    Returns:
    --------
    tuple : (time_block_data dict, avg_incidents float)
    """
    # Count incidents per time block
    time_block_counts = df['Time_Block'].value_counts().to_dict()
    
    # Calculate average incidents per time block
    avg_incidents = round(sum(time_block_counts.values()) / len(time_block_counts), 1) if time_block_counts else 0
    
    return time_block_counts, avg_incidents


def generate_time_block_distribution_chart_pdf(time_block_data, avg_incidents):
    """
    Generate time block distribution chart as matplotlib Figure for PDF embedding.
    
    Returns:
    --------
    matplotlib.figure.Figure : Chart figure ready for PDF embedding
    """
    if not time_block_data:
        return None
    
    # Define standard time block order
    time_order = ['Early Morning', 'Morning', 'Mid-Morning', 'Lunch', 'Afternoon', 'Late Afternoon', 'After School']
    
    # Filter to only time blocks present in data and maintain order
    time_blocks = [t for t in time_order if t in time_block_data]
    incident_counts = [time_block_data[t] for t in time_blocks]
    
    # If no standard blocks found, use whatever blocks exist (sorted by count)
    if not time_blocks:
        sorted_items = sorted(time_block_data.items(), key=lambda x: x[1], reverse=True)
        time_blocks = [item[0] for item in sorted_items]
        incident_counts = [item[1] for item in sorted_items]
    
    if not time_blocks:
        return None
    
    # Determine colors based on variance from average
    colors = ['#FF8C42' if count > avg_incidents else '#5B7C99' for count in incident_counts]
    
    # Create figure
    fig, ax = plt.subplots(figsize=(8, 5))
    
    # Create horizontal bars
    y_pos = np.arange(len(time_blocks))
    bars = ax.barh(y_pos, incident_counts, color=colors, alpha=0.85, edgecolor='white', linewidth=1.5)
    
    # Add average reference line
    ax.axvline(avg_incidents, color='#2C3E50', linestyle='--', linewidth=2, zorder=3)
    
    # Add value labels on bars
    for i, (bar, count) in enumerate(zip(bars, incident_counts)):
        ax.text(count + (max(incident_counts) * 0.02), i, f'{count}', 
                va='center', fontsize=9, fontweight='bold')
    
    # Styling
    ax.set_yticks(y_pos)
    ax.set_yticklabels(time_blocks, fontsize=10)
    ax.set_xlabel('Number of Incidents', fontsize=11, fontweight='bold')
    ax.set_title('Incident Distribution by Time Block', fontsize=12, fontweight='bold', pad=15)
    ax.set_xlim(0, max(incident_counts) * 1.15 if incident_counts else 100)
    ax.grid(axis='x', alpha=0.3, linestyle=':')
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    
    # Legend
    import matplotlib.patches as mpatches
    orange_patch = mpatches.Patch(color='#FF8C42', label='Above Average', alpha=0.85)
    blue_patch = mpatches.Patch(color='#5B7C99', label='At/Below Avg', alpha=0.85)
    ax.legend(handles=[orange_patch, blue_patch],
              loc='upper right', frameon=False, fontsize=9)
    
    plt.tight_layout()
    
    return fig


def calculate_campus_comparison_data(campus_results):
    """
    Calculate campus removal rates for district comparison chart.
    
    Parameters:
    -----------
    campus_results : dict
        Dictionary where each key is a campus name and value contains stats
    
    Returns:
    --------
    tuple : (campus_data dict, district_avg float)
    """
    # Extract removal rates for each campus
    campus_data = {}
    total_removal_rate = 0
    
    for campus_name, results in campus_results.items():
        if 'stats' in results and 'removal_pct' in results['stats']:
            campus_data[campus_name] = results['stats']['removal_pct']
            total_removal_rate += results['stats']['removal_pct']
    
    # Calculate district average
    district_avg = round(total_removal_rate / len(campus_data), 1) if campus_data else 0
    
    return campus_data, district_avg


def generate_campus_comparison_chart_pdf(campus_data, district_avg):
    """
    Generate campus comparison chart as matplotlib Figure for PDF embedding.
    
    Returns:
    --------
    matplotlib.figure.Figure : Chart figure ready for PDF embedding
    """
    if not campus_data:
        return None
    
    # Sort campuses by removal rate (highest to lowest)
    sorted_items = sorted(campus_data.items(), key=lambda x: x[1], reverse=True)
    campus_names = [item[0] for item in sorted_items]
    removal_rates = [item[1] for item in sorted_items]
    
    if not campus_names:
        return None
    
    # Determine colors based on variance from district average
    colors = ['#FF8C42' if rate > district_avg else '#5B7C99' for rate in removal_rates]
    
    # Create figure with dynamic height
    fig_height = max(5, len(campus_names) * 0.4)
    fig, ax = plt.subplots(figsize=(8, fig_height))
    
    # Create horizontal bars
    y_pos = np.arange(len(campus_names))
    bars = ax.barh(y_pos, removal_rates, color=colors, alpha=0.85, edgecolor='white', linewidth=1.5)
    
    # Add district average reference line
    ax.axvline(district_avg, color='#2C3E50', linestyle='--', linewidth=2, zorder=3)
    
    # Add value labels on bars
    for i, (bar, rate) in enumerate(zip(bars, removal_rates)):
        ax.text(rate + 1, i, f'{rate:.1f}%', va='center', fontsize=9, fontweight='bold')
    
    # Styling
    ax.set_yticks(y_pos)
    ax.set_yticklabels(campus_names, fontsize=9)
    ax.set_xlabel('Removal Rate (%)', fontsize=11, fontweight='bold')
    ax.set_title('Campus Removal Rate Comparison', fontsize=12, fontweight='bold', pad=15)
    ax.set_xlim(0, max(removal_rates) + 10 if removal_rates else 100)
    ax.grid(axis='x', alpha=0.3, linestyle=':')
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    
    # Legend
    import matplotlib.patches as mpatches
    orange_patch = mpatches.Patch(color='#FF8C42', label='Above District Avg', alpha=0.85)
    blue_patch = mpatches.Patch(color='#5B7C99', label='At/Below Avg', alpha=0.85)
    ax.legend(handles=[orange_patch, blue_patch],
              loc='upper left', bbox_to_anchor=(1.02, 1), frameon=False, fontsize=9)
    plt.tight_layout(rect=[0, 0, 0.85, 1])
    
    return fig

def generate_instructional_impact_chart_pdf(df, grade_band_minutes=None):
    """
    Generate instructional impact chart showing days lost by grade level.
    
    Returns:
    --------
    matplotlib.figure.Figure : Chart figure ready for PDF embedding
    """
    if 'Days_Removed' not in df.columns or 'Grade' not in df.columns:
        return None    
    # Default instructional minutes by grade band
    if grade_band_minutes is None:
        grade_band_minutes = {
            'elementary': 360,  # K-5
            'middle': 375,      # 6-8
            'high': 390         # 9-12
        }
    
    # Calculate days lost by grade
    grade_impact = df.groupby('Grade')['Days_Removed'].sum().reset_index()
    grade_impact.columns = ['Grade', 'Days_Lost']
    
    if grade_impact.empty or grade_impact['Days_Lost'].sum() == 0:
        return None
    
    # Sort grades properly (handle K, PK, numeric)
    def grade_sort_key(g):
        g_str = str(g).strip().upper()
        if g_str in ['PK', 'PRE-K']:
            return -1
        elif g_str == 'K':
            return 0
        else:
            try:
                return int(float(g_str))
            except:
                return 999
    
    grade_impact['sort_key'] = grade_impact['Grade'].apply(grade_sort_key)
    grade_impact = grade_impact.sort_values('sort_key')
    
    grades = [str(g).replace('.0', '') for g in grade_impact['Grade'].tolist()]
    days_lost = grade_impact['Days_Lost'].tolist()
    
    if not grades:
        return None
    
    # Calculate average for variance coloring
    avg_days = sum(days_lost) / len(days_lost)
    
    # Determine colors based on variance from average
    colors = ['#FF8C42' if d > avg_days else '#5B7C99' for d in days_lost]
    
    # Create figure
    fig_height = max(4, len(grades) * 0.5)
    fig, ax = plt.subplots(figsize=(8, fig_height))
    
    # Create horizontal bars
    y_pos = np.arange(len(grades))
    bars = ax.barh(y_pos, days_lost, color=colors, alpha=0.85, edgecolor='white', linewidth=1.5)
    
    # Add 10-day chronic absence threshold line
    ax.axvline(10, color='#DC2626', linestyle='--', linewidth=2, zorder=3, label='Chronic Absence Threshold (10 days)')
    
    # Add value labels on bars
    for i, (bar, days) in enumerate(zip(bars, days_lost)):
        ax.text(days + 0.5, i, f'{days:.0f}', va='center', fontsize=9, fontweight='bold')
    
    # Styling
    ax.set_yticks(y_pos)
    ax.set_yticklabels([f'Grade {g}' for g in grades], fontsize=10)
    ax.set_xlabel('Instructional Days Lost', fontsize=11, fontweight='bold')
    ax.set_title('Instructional Days Lost by Grade', fontsize=12, fontweight='bold', pad=15)
    ax.set_xlim(0, max(days_lost) + 5 if days_lost else 15)
    ax.grid(axis='x', alpha=0.3, linestyle=':')
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    
    # Legend
    import matplotlib.patches as mpatches
    orange_patch = mpatches.Patch(color='#FF8C42', label='Above Avg Loss', alpha=0.85)
    blue_patch = mpatches.Patch(color='#5B7C99', label='At/Below Avg', alpha=0.85)
    threshold_line = plt.Line2D([0], [0], color='#DC2626', linestyle='--', linewidth=2, label='Chronic Threshold (10 days)')
    ax.legend(handles=[orange_patch, blue_patch, threshold_line],
              loc='lower right', frameon=False, fontsize=8)
    
    plt.tight_layout()
    
    return fig
def generate_district_instructional_impact_chart_pdf(campus_impact_data):
    """
    Generate district-level instructional impact chart showing days lost by campus.
    
    Parameters:
    -----------
    campus_impact_data : dict
        Dictionary of campus_name -> days_lost
    
    Returns:
    --------
    matplotlib.figure.Figure : Chart figure ready for PDF embedding
    """
    if not campus_impact_data:
        return None
    
    # Sort campuses by days lost (highest first)
    sorted_items = sorted(campus_impact_data.items(), key=lambda x: x[1], reverse=True)
    campus_names = [item[0] for item in sorted_items]
    days_lost = [item[1] for item in sorted_items]
    
    if not campus_names or sum(days_lost) == 0:
        return None
    
    # Calculate average for variance coloring
    avg_days = sum(days_lost) / len(days_lost)
    
    # Determine colors based on variance from average
    colors = ['#FF8C42' if d > avg_days else '#5B7C99' for d in days_lost]
    
    # Create figure
    fig_height = max(4, len(campus_names) * 0.6)
    fig, ax = plt.subplots(figsize=(8, fig_height))
    
    # Create horizontal bars
    y_pos = np.arange(len(campus_names))
    bars = ax.barh(y_pos, days_lost, color=colors, alpha=0.85, edgecolor='white', linewidth=1.5)
    
    # Add 10-day chronic absence threshold line
    ax.axvline(10, color='#DC2626', linestyle='--', linewidth=2, zorder=3)
    
    # Add value labels on bars
    for i, (bar, days) in enumerate(zip(bars, days_lost)):
        ax.text(days + 0.5, i, f'{days:.0f}', va='center', fontsize=9, fontweight='bold')
    
    # Styling
    ax.set_yticks(y_pos)
    ax.set_yticklabels(campus_names, fontsize=10)
    ax.set_xlabel('Instructional Days Lost', fontsize=11, fontweight='bold')
    ax.set_title('Instructional Days Lost by Campus', fontsize=12, fontweight='bold', pad=15)
    ax.set_xlim(0, max(days_lost) + 10 if days_lost else 15)
    ax.grid(axis='x', alpha=0.3, linestyle=':')
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    
    # Legend
    import matplotlib.patches as mpatches
    orange_patch = mpatches.Patch(color='#FF8C42', label='Above Avg Loss', alpha=0.85)
    blue_patch = mpatches.Patch(color='#5B7C99', label='At/Below Avg', alpha=0.85)
    threshold_line = plt.Line2D([0], [0], color='#DC2626', linestyle='--', linewidth=2, label='Chronic Threshold (10 days)')
    ax.legend(handles=[orange_patch, blue_patch, threshold_line],
              loc='upper right', frameon=False, fontsize=8)
    
    plt.tight_layout()
    
    return fig
def generate_equity_chart_pdf(equity_data, campus_avg):
    """
    Generate equity pattern chart as matplotlib Figure for PDF embedding.
    Shows removal rates by race and gender compared to campus average.
    
    Returns:
    --------
    matplotlib.figure.Figure : Chart figure ready for PDF embedding
    """
    if not equity_data or equity_data.get('suppressed', False):
        return None
    
    # Collect all subgroups
    labels = []
    rates = []
    
    # Add race data
    if equity_data.get('by_race'):
        for race, data in equity_data['by_race'].items():
            labels.append(f"{race}")
            rates.append(data['removal_rate'])
    
    # Add gender data
    if equity_data.get('by_gender'):
        for gender, data in equity_data['by_gender'].items():
            label = "Male" if gender == "M" else "Female" if gender == "F" else gender
            labels.append(f"{label}")
            rates.append(data['removal_rate'])
    
    if not labels:
        return None
    
    # Determine colors based on variance from campus average
    colors = ['#FF8C42' if rate > campus_avg else '#5B7C99' for rate in rates]
    
    # Create figure
    fig_height = max(4, len(labels) * 0.5)
    fig, ax = plt.subplots(figsize=(8, fig_height))
    
    # Create horizontal bars
    y_pos = np.arange(len(labels))
    bars = ax.barh(y_pos, rates, color=colors, alpha=0.85, edgecolor='white', linewidth=1.5)
    
    # Add campus average reference line
    ax.axvline(campus_avg, color='#2C3E50', linestyle='--', linewidth=2, zorder=3)
    
    # Add value labels on bars
    for i, (bar, rate) in enumerate(zip(bars, rates)):
        ax.text(rate + 1, i, f'{rate:.1f}%', va='center', fontsize=9, fontweight='bold')
    
    # Styling
    ax.set_yticks(y_pos)
    ax.set_yticklabels(labels, fontsize=10)
    ax.set_xlabel('Removal Rate (%)', fontsize=11, fontweight='bold')
    ax.set_title('Removal Rates by Subgroup', fontsize=12, fontweight='bold', pad=15)
    ax.set_xlim(0, max(rates) + 15 if rates else 100)
    ax.grid(axis='x', alpha=0.3, linestyle=':')
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    
    # Legend
    import matplotlib.patches as mpatches
    orange_patch = mpatches.Patch(color='#FF8C42', label='Above Campus Avg', alpha=0.85)
    blue_patch = mpatches.Patch(color='#5B7C99', label='At/Below Avg', alpha=0.85)
    ax.legend(handles=[orange_patch, blue_patch],
              loc='upper right', frameon=False, fontsize=9)
    
    plt.tight_layout()
    
    return fig
def generate_posture_gauge(removal_rate, oss_rate, expulsion_count, posture):
    """
    Generates matplotlib figure showing discipline posture gauge.
    
    Args:
        removal_rate (float): Overall removal percentage (0-100)
        oss_rate (float): OSS percentage (0-100)
        expulsion_count (int): Total expulsions
        posture (str): Calculated posture (STABLE/CALIBRATE/INTERVENE/ESCALATE)
        
    Returns:
        matplotlib.figure.Figure: Gauge visualization, or None if data invalid
    """
    
    # Validation
    if removal_rate is None or posture not in ['STABLE', 'CALIBRATE', 'INTERVENE', 'ESCALATE']:
        return None
    
    # Create figure
    fig, ax = plt.subplots(figsize=(10, 2.5), dpi=150)
    fig.patch.set_facecolor('white')
    
    # Color palette (locked)
    colors = {
        'STABLE': '#2E7D32',      # Dark green
        'CALIBRATE': '#FBC02D',   # Yellow
        'INTERVENE': '#FF6F00',   # Bright orange
        'ESCALATE': '#B71C1C'     # Deep red
    }
    
    # Zone boundaries with gaps
    zones = [
        {'name': 'STABLE', 'start': 0, 'end': 35, 'color': colors['STABLE']},
        {'name': 'CALIBRATE', 'start': 35.05, 'end': 45, 'color': colors['CALIBRATE']},
        {'name': 'INTERVENE', 'start': 45.05, 'end': 60, 'color': colors['INTERVENE']},
        {'name': 'ESCALATE', 'start': 60.05, 'end': 100, 'color': colors['ESCALATE']}
    ]
    
    # Draw zones
    for zone in zones:
        rect = mpatches.Rectangle(
            (zone['start'], 0), 
            zone['end'] - zone['start'], 
            1,
            facecolor=zone['color'],
            edgecolor='black',
            linewidth=2
        )
        ax.add_patch(rect)
        
        # Add zone label
        mid_point = (zone['start'] + zone['end']) / 2
        ax.text(
            mid_point, 
            0.5, 
            zone['name'],
            ha='center',
            va='center',
            fontsize=11,
            fontweight='bold',
            color='white'
        )
    # Draw threshold lines
    for threshold in [35, 45, 60]:
        ax.axvline(x=threshold, color='gray', linestyle='--', linewidth=1, alpha=0.7)
    
    # Draw pointer (triangle pointing to current position)
    pointer_x = removal_rate
    pointer_y = 1.05
    triangle = mpatches.Polygon(
        [[pointer_x - 1.5, pointer_y + 0.15], 
         [pointer_x + 1.5, pointer_y + 0.15], 
         [pointer_x, pointer_y]],
        closed=True,
        facecolor='black',
        edgecolor='black',
        linewidth=2
    )
    ax.add_patch(triangle)
    
    # Add percentage marker at pointer
    ax.text(
        pointer_x,
        pointer_y + 0.25,
        f'{removal_rate:.1f}%',
        ha='center',
        va='bottom',
        fontsize=10,
        fontweight='bold'
    )
    
    # Calculate distance to next threshold
    if removal_rate < 35:
        distance = 35 - removal_rate
        next_threshold = "CALIBRATE (35%)"
    elif removal_rate < 45:
        distance = 45 - removal_rate
        next_threshold = "INTERVENE (45%)"
    elif removal_rate < 60:
        distance = 60 - removal_rate
        next_threshold = "ESCALATE (60%)"
    else:
        distance = None
        next_threshold = "Maximum threshold"
    
    # Add status text below gauge
    status_text = f"Current Status: {posture} | Removal Rate: {removal_rate:.1f}%"
    if distance:
        status_text += f" | Distance to {next_threshold}: {distance:.1f} points"
    
    ax.text(
        50,
        -0.3,
        status_text,
        ha='center',
        va='top',
        fontsize=10
    )
    
    # Configure axes
    ax.set_xlim(-2, 102)
    ax.set_ylim(-0.5, 1.5)
    ax.set_xticks([0, 35, 45, 60, 100])
    ax.set_xticklabels(['0%', '35%', '45%', '60%', '100%'])
    ax.set_yticks([])
    
    # Remove spines
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.spines['left'].set_visible(False)
    
    ax.set_title('DISCIPLINE SYSTEM POSTURE', fontsize=12, fontweight='bold', pad=20)
    
    plt.tight_layout()
    
    return fig

