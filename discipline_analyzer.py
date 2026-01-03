"""
ATLAS DISCIPLINE INTELLIGENCE — CORE ANALYSIS ENGINE
Texas TEA Compliance Mode
Version: 2.0 (Updated Jan 2026)

Changes in this version:
- Instructional Impact moved to Section 3
- Per-grade table format for instructional loss
- Chronic absenteeism context added
"""

import pandas as pd
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
    for grade in sorted(removal_df['Grade'].unique()):
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
    """
    Backward compatibility wrapper for analyze_instructional_impact
    """
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
    brief += f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
    brief += "─" * 80 + "\n\n"
    
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
        for grade in sorted(impact['grade_distribution'].keys()):
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
    grade_analysis = grade_analysis.sort_values('Removal_Rate', ascending=False)
    
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
