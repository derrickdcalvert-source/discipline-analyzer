#!/usr/bin/env python3
"""
Discipline Decision Brief Analyzer v2.0
Supports STATE_MODE: DEFAULT and TEXAS_TEA
Deterministic rules-based system analysis
"""

import pandas as pd
import sys
from datetime import datetime
from collections import Counter

# ============================================================================
# CONFIGURATION
# ============================================================================

STATE_MODE = "TEXAS_TEA"  # Options: "DEFAULT" or "TEXAS_TEA"

# TEA Action Code Mapping (Texas mode only)
TEA_CODE_MAP = {
    "Teacher Conference": "LOCAL_ONLY",
    "Lunch Detention": "LOCAL_ONLY",
    "After School Detention": "LOCAL_ONLY",
    "ISS": "06",
    "OSS": "05",
    "Expulsion": "01"
}

# TEA Action Groups
TEA_ACTION_GROUPS = {
    "ISS": ["06", "26"],
    "OSS": ["05", "25"],
    "DAEP": ["07"],
    "JJAEP": ["13"],
    "Expulsion": ["01", "02", "03", "04", "50", "51", "52", "53"]
}

# ============================================================================
# DATA LOADING AND VALIDATION
# ============================================================================

def load_data(filepath):
    """Load discipline data from CSV or Excel"""
    if filepath.endswith('.csv'):
        df = pd.read_csv(filepath)
    else:
        df = pd.read_excel(filepath)
    
    # Required columns
    required = ['Date', 'Grade', 'Incident_Type', 'Location', 'Time_Block', 'Response']
    missing = [col for col in required if col not in df.columns]
    
    if missing:
        print(f"ERROR: Missing required columns: {missing}")
        sys.exit(1)
    
    # Convert Date to datetime
    df['Date'] = pd.to_datetime(df['Date'])
    
    return df

# ============================================================================
# TEXAS TEA MODE — CODE MAPPING AND GROUPING
# ============================================================================

def apply_tea_mapping(df):
    """Apply TEA code mapping in Texas mode"""
    
    # If TEA_Action_Code column exists, use it; otherwise map from Response
    if 'TEA_Action_Code' not in df.columns:
        df['TEA_Action_Code'] = df['Response'].map(TEA_CODE_MAP)
        # If mapping fails, keep original Response value
        df['TEA_Action_Code'] = df['TEA_Action_Code'].fillna(df['Response'])
    
    # Assign TEA Action Group
    def get_tea_group(code):
        if code == "LOCAL_ONLY":
            return "LOCAL_ONLY"
        for group, codes in TEA_ACTION_GROUPS.items():
            if str(code) in codes:
                return group
        return "UNKNOWN"
    
    df['TEA_Action_Group'] = df['TEA_Action_Code'].apply(get_tea_group)
    
    # Add Days_Removed if missing (default = 1 for removals, 0 for LOCAL_ONLY)
    if 'Days_Removed' not in df.columns:
        df['Days_Removed'] = df['TEA_Action_Group'].apply(
            lambda x: 0 if x == "LOCAL_ONLY" else 1
        )
    
    return df

# ============================================================================
# CALCULATION FUNCTIONS
# ============================================================================

def calculate_school_brief_stats(df):
    """Calculate stats for School Brief (includes LOCAL_ONLY)"""
    
    total_incidents = len(df)
    
    if STATE_MODE == "TEXAS_TEA":
        group_counts = df['TEA_Action_Group'].value_counts()
        
        stats = {
            'total_incidents': total_incidents,
            'LOCAL_ONLY': group_counts.get('LOCAL_ONLY', 0),
            'ISS': group_counts.get('ISS', 0),
            'OSS': group_counts.get('OSS', 0),
            'DAEP': group_counts.get('DAEP', 0),
            'JJAEP': group_counts.get('JJAEP', 0),
            'Expulsion': group_counts.get('Expulsion', 0)
        }
        
        # Calculate percentages
        for key in ['LOCAL_ONLY', 'ISS', 'OSS', 'DAEP', 'JJAEP', 'Expulsion']:
            stats[f'{key}_pct'] = round((stats[key] / total_incidents * 100), 1) if total_incidents > 0 else 0
        
    else:  # DEFAULT mode
        response_counts = df['Response'].value_counts()
        
        stats = {
            'total_incidents': total_incidents,
            'Teacher_Conference': response_counts.get('Teacher Conference', 0),
            'Lunch_Detention': response_counts.get('Lunch Detention', 0),
            'After_School_Detention': response_counts.get('After School Detention', 0),
            'ISS': response_counts.get('ISS', 0),
            'OSS': response_counts.get('OSS', 0),
            'Expulsion': response_counts.get('Expulsion', 0)
        }
        
        # Calculate percentages
        for key in stats.keys():
            if key != 'total_incidents':
                stats[f'{key}_pct'] = round((stats[key] / total_incidents * 100), 1) if total_incidents > 0 else 0
    
    return stats

def calculate_district_tea_stats(df):
    """Calculate stats for District TEA Report (excludes LOCAL_ONLY)"""
    
    # Filter out LOCAL_ONLY
    tea_df = df[df['TEA_Action_Group'] != 'LOCAL_ONLY'].copy()
    
    total_tea_actions = len(tea_df)
    
    # Group counts
    group_counts = tea_df['TEA_Action_Group'].value_counts()
    
    stats = {
        'total_tea_actions': total_tea_actions,
        'ISS': group_counts.get('ISS', 0),
        'OSS': group_counts.get('OSS', 0),
        'DAEP': group_counts.get('DAEP', 0),
        'JJAEP': group_counts.get('JJAEP', 0),
        'Expulsion': group_counts.get('Expulsion', 0)
    }
    
    # Calculate percentages
    for key in ['ISS', 'OSS', 'DAEP', 'JJAEP', 'Expulsion']:
        stats[f'{key}_pct'] = round((stats[key] / total_tea_actions * 100), 1) if total_tea_actions > 0 else 0
    
    # Code-level counts (if TEA_Action_Code is populated)
    code_counts = tea_df['TEA_Action_Code'].value_counts().to_dict()
    stats['code_counts'] = code_counts
    
    return stats

def calculate_instructional_impact(df):
    """Calculate instructional time lost (minutes)"""
    
    if STATE_MODE == "TEXAS_TEA":
        # LOCAL_ONLY = 0 minutes
        # ISS/OSS/DAEP/JJAEP/Expulsion = 360 minutes per day
        
        removal_df = df[df['TEA_Action_Group'] != 'LOCAL_ONLY'].copy()
        
        total_minutes = (removal_df['Days_Removed'] * 360).sum()
        
        # Potentially recoverable time (scenario-based)
        # Count repeat removals by student (if Student_ID exists)
        if 'Student_ID' in df.columns:
            repeat_students = removal_df['Student_ID'].value_counts()
            repeat_removals = repeat_students[repeat_students > 1].sum() - len(repeat_students[repeat_students > 1])
            recoverable_minutes = repeat_removals * 360
        else:
            recoverable_minutes = 0
        
    else:  # DEFAULT mode
        # Count removal responses
        removal_responses = ['ISS', 'OSS', 'Expulsion']
        removal_df = df[df['Response'].isin(removal_responses)].copy()
        
        total_minutes = len(removal_df) * 360
        
        if 'Student_ID' in df.columns:
            repeat_students = removal_df['Student_ID'].value_counts()
            repeat_removals = repeat_students[repeat_students > 1].sum() - len(repeat_students[repeat_students > 1])
            recoverable_minutes = repeat_removals * 360
        else:
            recoverable_minutes = 0
    
    return {
        'total_minutes': int(total_minutes),
        'total_days': round(total_minutes / 360, 1),
        'recoverable_minutes': int(recoverable_minutes),
        'recoverable_days': round(recoverable_minutes / 360, 1)
    }

# ============================================================================
# DECISION POSTURE (TEXAS MODE)
# ============================================================================

def determine_posture_texas(stats):
    """Determine Decision Posture using Texas TEA rules"""
    
    total = stats['total_incidents']
    
    if total == 0:
        return "STABLE", "Stable"
    
    # Calculate removal percentages
    iss_daep_jjaep_pct = stats['ISS_pct'] + stats['DAEP_pct'] + stats['JJAEP_pct']
    oss_pct = stats['OSS_pct']
    expulsion_count = stats['Expulsion']
    
    # ESCALATE
    if iss_daep_jjaep_pct >= 60 or oss_pct >= 20 or expulsion_count > 0:
        return "ESCALATE", "Escalating"
    
    # INTERVENE
    if (iss_daep_jjaep_pct >= 45 and iss_daep_jjaep_pct < 60) or (oss_pct >= 15 and oss_pct < 20):
        return "INTERVENE", "Drifting → Early Escalation Pressure"
    
    # CALIBRATE
    if (iss_daep_jjaep_pct >= 35 and iss_daep_jjaep_pct < 45) or (oss_pct >= 10 and oss_pct < 15):
        return "CALIBRATE", "Drifting"
    
    # STABLE (default)
    return "STABLE", "Stable"

# ============================================================================
# DECISION POSTURE (DEFAULT MODE)
# ============================================================================

def determine_posture_default(stats):
    """Determine Decision Posture using default rules"""
    
    total = stats['total_incidents']
    
    if total == 0:
        return "STABLE", "Stable"
    
    # Calculate removal percentage
    removal_pct = stats['ISS_pct'] + stats['OSS_pct'] + stats['Expulsion_pct']
    
    # ESCALATE
    if removal_pct >= 60:
        return "ESCALATE", "Escalating"
    
    # INTERVENE
    if removal_pct >= 45 and removal_pct < 60:
        return "INTERVENE", "Drifting → Early Escalation Pressure"
    
    # CALIBRATE
    if removal_pct >= 35 and removal_pct < 45:
        return "CALIBRATE", "Drifting"
    
    # STABLE
    return "STABLE", "Stable"

# ============================================================================
# TEA COMPLIANCE ALERT
# ============================================================================

def generate_tea_compliance_alert(df):
    """Generate TEA compliance alert for District report"""
    
    alert = []
    
    alert.append("═══════════════════════════════════════════════════════════════")
    alert.append("TEA COMPLIANCE ALERT")
    alert.append("═══════════════════════════════════════════════════════════════")
    alert.append("")
    
    if 'TEA_Action_Reason_Code' in df.columns and not df['TEA_Action_Reason_Code'].isna().all():
        # Reason codes are present
        reason_counts = df['TEA_Action_Reason_Code'].value_counts()
        
        alert.append("Potential mandatory placement/expulsion triggers observed:")
        alert.append("")
        for code, count in reason_counts.items():
            alert.append(f"  Reason Code {code}: {count} incidents")
        alert.append("")
        alert.append("Action code alignment: Needs manual review against TEA Chapter 37")
        alert.append("and 'Chart for Determining Mandatory and Discretionary DAEP")
        alert.append("Placements and Expulsions.'")
        alert.append("")
        alert.append("IMPORTANT: The TEA chart represents required actions for districts")
        alert.append("and includes exceptions for charter schools (notably firearm")
        alert.append("provisions unless adopted).")
        
    else:
        # Reason codes missing
        alert.append("COMPLIANCE ALERT LIMITED:")
        alert.append("")
        alert.append("Action Reason Codes not provided. Cannot validate mandatory vs.")
        alert.append("discretionary placement rules.")
        alert.append("")
        alert.append("To enable compliance validation, include TEA_Action_Reason_Code")
        alert.append("in the dataset.")
    
    alert.append("")
    alert.append("═══════════════════════════════════════════════════════════════")
    
    return "\n".join(alert)

# ============================================================================
# REPORT GENERATION — SCHOOL BRIEF
# ============================================================================

def generate_school_brief(df, stats, posture, system_state, impact):
    """Generate School Brief (Principal-Facing)"""
    
    lines = []
    
    lines.append("═══════════════════════════════════════════════════════════════")
    lines.append("DISCIPLINE DECISION BRIEF — SCHOOL BRIEF (PRINCIPAL-FACING)")
    lines.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    if STATE_MODE == "TEXAS_TEA":
        lines.append("State Mode: TEXAS / TEA")
    lines.append("═══════════════════════════════════════════════════════════════")
    lines.append("")
    
    # 1. SYSTEM STATUS AT A GLANCE
    lines.append("───────────────────────────────────────────────────────────────")
    lines.append("DISCIPLINE SYSTEM STATUS — AT A GLANCE")
    lines.append("───────────────────────────────────────────────────────────────")
    lines.append("")
    lines.append(f"Overall System State:    {system_state}")
    lines.append(f"Decision Posture:        {posture}")
    lines.append("")
    
    # One-sentence interpretation
    if posture == "STABLE":
        interp = "System is operating within stable parameters. No immediate action required."
    elif posture == "CALIBRATE":
        interp = "System is drifting from stable baseline. Monitor for pattern changes."
    elif posture == "INTERVENE":
        interp = "System is showing early escalation pressure. Review removal patterns."
    else:  # ESCALATE
        interp = "System requires immediate leadership review of removal practices."
    
    lines.append(f"One-Sentence Interpretation: {interp}")
    lines.append("")
    
    # 2. RESPONSE / REMOVAL SNAPSHOT
    lines.append("───────────────────────────────────────────────────────────────")
    lines.append("RESPONSE / REMOVAL SNAPSHOT (QUICK READ)")
    lines.append("───────────────────────────────────────────────────────────────")
    lines.append("")
    lines.append(f"Total Incidents: {stats['total_incidents']}")
    lines.append("")
    
    if STATE_MODE == "TEXAS_TEA":
        lines.append(f"Non-Removal (LOCAL_ONLY):  {stats['LOCAL_ONLY']:3d} ({stats['LOCAL_ONLY_pct']:5.1f}%)")
        lines.append(f"ISS (TEA 06):              {stats['ISS']:3d} ({stats['ISS_pct']:5.1f}%)")
        lines.append(f"OSS (TEA 05):              {stats['OSS']:3d} ({stats['OSS_pct']:5.1f}%)")
        lines.append(f"DAEP (TEA 07):             {stats['DAEP']:3d} ({stats['DAEP_pct']:5.1f}%)")
        lines.append(f"JJAEP (TEA 13):            {stats['JJAEP']:3d} ({stats['JJAEP_pct']:5.1f}%)")
        lines.append(f"Expulsion (TEA 01-04):     {stats['Expulsion']:3d} ({stats['Expulsion_pct']:5.1f}%)")
    else:
        lines.append(f"Teacher Conference:        {stats['Teacher_Conference']:3d} ({stats['Teacher_Conference_pct']:5.1f}%)")
        lines.append(f"Lunch Detention:           {stats['Lunch_Detention']:3d} ({stats['Lunch_Detention_pct']:5.1f}%)")
        lines.append(f"After School Detention:    {stats['After_School_Detention']:3d} ({stats['After_School_Detention_pct']:5.1f}%)")
        lines.append(f"ISS:                       {stats['ISS']:3d} ({stats['ISS_pct']:5.1f}%)")
        lines.append(f"OSS:                       {stats['OSS']:3d} ({stats['OSS_pct']:5.1f}%)")
        lines.append(f"Expulsion:                 {stats['Expulsion']:3d} ({stats['Expulsion_pct']:5.1f}%)")
    
    lines.append("")
    
    # Leadership Interpretation
    lines.append("Leadership Interpretation:")
    lines.append("")
    if STATE_MODE == "TEXAS_TEA":
        removal_pct = stats['ISS_pct'] + stats['DAEP_pct'] + stats['JJAEP_pct'] + stats['OSS_pct']
        lines.append(f"Removal-based responses represent {removal_pct:.1f}% of total incidents.")
    else:
        removal_pct = stats['ISS_pct'] + stats['OSS_pct'] + stats['Expulsion_pct']
        lines.append(f"Removal-based responses represent {removal_pct:.1f}% of total incidents.")
    
    if posture in ["INTERVENE", "ESCALATE"]:
        lines.append("Removal is the primary system response. Pattern review recommended.")
    else:
        lines.append("Non-removal responses remain the dominant system approach.")
    lines.append("")
    
    # 3. BEHAVIORAL PRESSURE SIGNAL
    lines.append("───────────────────────────────────────────────────────────────")
    lines.append("BEHAVIORAL PRESSURE SIGNAL")
    lines.append("───────────────────────────────────────────────────────────────")
    lines.append("")
    lines.append("Behavioral Pressure Signal not displayed. Criteria not fully met.")
    lines.append("")
    
    # 4. TOP RISK
    lines.append("───────────────────────────────────────────────────────────────")
    lines.append("TOP RISK")
    lines.append("───────────────────────────────────────────────────────────────")
    lines.append("")
    
    if posture == "ESCALATE":
        lines.append("System-level pattern: Removal responses exceed stable operating")
        lines.append("thresholds. High removal rates create instructional continuity risk.")
    elif posture == "INTERVENE":
        lines.append("System-level pattern: Early escalation pressure observed. Monitor")
        lines.append("for sustained increase in removal-based responses.")
    else:
        lines.append("No system-level risk detected at this time.")
    lines.append("")
    
    # 5. INSTRUCTIONAL IMPACT
    lines.append("───────────────────────────────────────────────────────────────")
    lines.append("INSTRUCTIONAL IMPACT (INFORMATIONAL ONLY)")
    lines.append("───────────────────────────────────────────────────────────────")
    lines.append("")
    lines.append(f"Total Instructional Time Lost (Removal-Based):")
    lines.append(f"  {impact['total_minutes']:,} minutes ({impact['total_days']:.1f} days)")
    lines.append("")
    lines.append(f"Potentially Recoverable Time (Scenario-Based):")
    lines.append(f"  {impact['recoverable_minutes']:,} minutes ({impact['recoverable_days']:.1f} days)")
    lines.append("")
    lines.append("REQUIRED DISCLAIMER:")
    lines.append("Potentially recoverable instructional time is a scenario-based estimate")
    lines.append("derived from repeat removal patterns observed in this dataset. It does")
    lines.append("not predict outcomes, guarantee improvement, or assume the effectiveness")
    lines.append("of any intervention. This information is provided for planning and")
    lines.append("prioritization only.")
    lines.append("")
    
    # 6. WATCH LIST
    lines.append("───────────────────────────────────────────────────────────────")
    lines.append("WATCH LIST")
    lines.append("───────────────────────────────────────────────────────────────")
    lines.append("")
    lines.append("Patterns to monitor:")
    lines.append("  • Sustained increase in removal percentages")
    lines.append("  • Repeat removals for the same students")
    lines.append("  • Clustering of incidents by location or time block")
    lines.append("")
    
    # 7. STABILITY & POSTURE BOUNDARIES
    lines.append("───────────────────────────────────────────────────────────────")
    lines.append("STABILITY & POSTURE BOUNDARIES")
    lines.append("───────────────────────────────────────────────────────────────")
    lines.append("")
    
    if STATE_MODE == "TEXAS_TEA":
        lines.append("STABLE:    (ISS+DAEP+JJAEP) < 35%, OSS < 10%, Expulsion = 0")
        lines.append("CALIBRATE: (ISS+DAEP+JJAEP) 35-44%, OSS < 15%")
        lines.append("INTERVENE: (ISS+DAEP+JJAEP) 45-59%, OSS < 20%")
        lines.append("ESCALATE:  (ISS+DAEP+JJAEP) ≥ 60% OR OSS ≥ 20% OR expulsion patterns")
    else:
        lines.append("STABLE:    Removal < 35%")
        lines.append("CALIBRATE: Removal 35-44%")
        lines.append("INTERVENE: Removal 45-59%")
        lines.append("ESCALATE:  Removal ≥ 60%")
    
    lines.append("")
    
    # 8. BOTTOM LINE
    lines.append("───────────────────────────────────────────────────────────────")
    lines.append("BOTTOM LINE FOR LEADERSHIP")
    lines.append("───────────────────────────────────────────────────────────────")
    lines.append("")
    
    if posture == "STABLE":
        lines.append("System is operating within expected parameters. Continue monitoring.")
    elif posture == "CALIBRATE":
        lines.append("System is drifting from baseline. No immediate action required.")
    elif posture == "INTERVENE":
        lines.append("System shows early escalation signals. Review removal patterns.")
    else:  # ESCALATE
        lines.append("System requires immediate leadership attention. Review removal")
        lines.append("practices and consider system-level adjustments.")
    
    lines.append("")
    lines.append("═══════════════════════════════════════════════════════════════")
    lines.append("END OF SCHOOL BRIEF")
    lines.append("═══════════════════════════════════════════════════════════════")
    
    return "\n".join(lines)

# ============================================================================
# REPORT GENERATION — DISTRICT TEA REPORT
# ============================================================================

def generate_district_tea_report(df, tea_stats):
    """Generate District TEA Report (Compliance/Reporting)"""
    
    lines = []
    
    lines.append("═══════════════════════════════════════════════════════════════")
    lines.append("DISCIPLINE DECISION BRIEF — DISTRICT TEA REPORT")
    lines.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append("State Mode: TEXAS / TEA")
    lines.append("═══════════════════════════════════════════════════════════════")
    lines.append("")
    
    # 1. TEA DISCIPLINE ACTION GROUP TOTALS
    lines.append("───────────────────────────────────────────────────────────────")
    lines.append("TEA DISCIPLINE ACTION GROUP TOTALS")
    lines.append("───────────────────────────────────────────────────────────────")
    lines.append("")
    lines.append(f"Total TEA Actions (excludes LOCAL_ONLY): {tea_stats['total_tea_actions']}")
    lines.append("")
    lines.append(f"ISS (TEA 06):          {tea_stats['ISS']:3d} ({tea_stats['ISS_pct']:5.1f}%)")
    lines.append(f"OSS (TEA 05):          {tea_stats['OSS']:3d} ({tea_stats['OSS_pct']:5.1f}%)")
    lines.append(f"DAEP (TEA 07):         {tea_stats['DAEP']:3d} ({tea_stats['DAEP_pct']:5.1f}%)")
    lines.append(f"JJAEP (TEA 13):        {tea_stats['JJAEP']:3d} ({tea_stats['JJAEP_pct']:5.1f}%)")
    lines.append(f"Expulsion (TEA 01-04): {tea_stats['Expulsion']:3d} ({tea_stats['Expulsion_pct']:5.1f}%)")
    lines.append("")
    
    # 2. TEA ACTION CODE COUNTS
    lines.append("───────────────────────────────────────────────────────────────")
    lines.append("TEA DISCIPLINARY ACTION CODE COUNTS")
    lines.append("───────────────────────────────────────────────────────────────")
    lines.append("")
    
    if tea_stats['code_counts']:
        for code, count in sorted(tea_stats['code_counts'].items()):
            lines.append(f"Code {code}: {count}")
    else:
        lines.append("Action codes not available in dataset.")
    
    lines.append("")
    
    # 3. TEA COMPLIANCE ALERT
    compliance_alert = generate_tea_compliance_alert(df)
    lines.append(compliance_alert)
    lines.append("")
    
    # 4. DATA QUALITY NOTES
    lines.append("───────────────────────────────────────────────────────────────")
    lines.append("DATA QUALITY NOTES")
    lines.append("───────────────────────────────────────────────────────────────")
    lines.append("")
    
    missing_fields = []
    if 'TEA_Action_Code' not in df.columns:
        missing_fields.append("TEA_Action_Code (mapped from Response)")
    if 'TEA_Action_Reason_Code' not in df.columns:
        missing_fields.append("TEA_Action_Reason_Code (limits compliance validation)")
    if 'Days_Removed' not in df.columns:
        missing_fields.append("Days_Removed (defaulted to 1 day per removal)")
    
    if missing_fields:
        lines.append("Missing or defaulted fields:")
        for field in missing_fields:
            lines.append(f"  • {field}")
    else:
        lines.append("All TEA reporting fields present.")
    
    lines.append("")
    
    # Check for unmapped responses
    if 'TEA_Action_Group' in df.columns:
        unknown = df[df['TEA_Action_Group'] == 'UNKNOWN']
        if len(unknown) > 0:
            lines.append(f"WARNING: {len(unknown)} incidents could not be mapped to TEA action groups.")
            lines.append("Review Response values for compliance.")
            lines.append("")
    
    lines.append("═══════════════════════════════════════════════════════════════")
    lines.append("END OF DISTRICT TEA REPORT")
    lines.append("═══════════════════════════════════════════════════════════════")
    
    return "\n".join(lines)

# ============================================================================
# MAIN EXECUTION
# ============================================================================

def main():
    if len(sys.argv) < 2:
        print("Usage: python discipline_analyzer.py <filepath>")
        sys.exit(1)
    
    filepath = sys.argv[1]
    
    # Load data
    print(f"Loading data from: {filepath}")
    df = load_data(filepath)
    print(f"Loaded {len(df)} incidents")
    print("")
    
    # Apply TEA mapping if in Texas mode
    if STATE_MODE == "TEXAS_TEA":
        print("Applying TEA code mapping...")
        df = apply_tea_mapping(df)
        print("")
    
    # Calculate School Brief stats (includes LOCAL_ONLY)
    print("Calculating School Brief statistics...")
    school_stats = calculate_school_brief_stats(df)
    
    # Determine posture
    if STATE_MODE == "TEXAS_TEA":
        posture, system_state = determine_posture_texas(school_stats)
    else:
        posture, system_state = determine_posture_default(school_stats)
    
    print(f"Decision Posture: {posture}")
    print(f"System State: {system_state}")
    print("")
    
    # Calculate instructional impact
    print("Calculating instructional impact...")
    impact = calculate_instructional_impact(df)
    print("")
    
    # Generate School Brief
    print("Generating School Brief...")
    school_brief = generate_school_brief(df, school_stats, posture, system_state, impact)
    
    # Save School Brief
    output_file_school = filepath.rsplit('.', 1)[0] + '_SCHOOL_BRIEF.txt'
    with open(output_file_school, 'w') as f:
        f.write(school_brief)
    print(f"School Brief saved: {output_file_school}")
    print("")
    
    # Generate District TEA Report (Texas mode only)
    if STATE_MODE == "TEXAS_TEA":
        print("Calculating District TEA statistics...")
        tea_stats = calculate_district_tea_stats(df)
        
        print("Generating District TEA Report...")
        district_report = generate_district_tea_report(df, tea_stats)
        
        # Save District Report
        output_file_district = filepath.rsplit('.', 1)[0] + '_DISTRICT_TEA_REPORT.txt'
        with open(output_file_district, 'w') as f:
            f.write(district_report)
        print(f"District TEA Report saved: {output_file_district}")
        print("")
    
    print("Analysis complete.")
    print(school_brief)
    
    if STATE_MODE == "TEXAS_TEA":
        print("")
        print(district_report)

if __name__ == "__main__":
    main()
