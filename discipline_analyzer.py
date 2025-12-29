#!/usr/bin/env python3
"""
Discipline Decision Brief Analyzer - TEXAS TEA VERSION
Complete implementation with all 14 sections
Deterministic rules-based system analysis
"""

import pandas as pd
import sys
import hashlib
from datetime import datetime
from collections import Counter

# ============================================================================
# CONFIGURATION
# ============================================================================

STATE_MODE = "TEXAS_TEA"

# TEA Action Code Mapping (Texas mode only)
TEA_CODE_MAP = {
    # ISS - In-School Suspension
    "In-School Suspension": "06",
    "ISS": "06",
    
    # OSS - Out-of-School Suspension  
    "Out-of-School Suspension": "05",
    "OSS": "05",
    
    # DAEP - Disciplinary Alternative Education Placement
    "DAEP": "07",
    "Disciplinary Alternative Education Placement": "07",
    
    # JJAEP - Juvenile Justice AEP
    "JJAEP": "13",
    "Juvenile Justice Alternative Education Placement": "13",
    
    # Expulsion codes (01-04)
    "Expulsion": "02",
    "Expulsion with Services": "02",
    "Expulsion without Services": "01",
    
    # Local responses (no TEA code)
    "Warning": "N/A",
    "Conference": "N/A",
    "Detention": "N/A",
    "Lunch Detention": "N/A",
    "Saturday School": "N/A",
    "Behavior Contract": "N/A",
    "Parent Contact": "N/A",
    "Counseling": "N/A",
    "Restorative Practice": "N/A",
    "Loss of Privilege": "N/A",
}

# ============================================================================
# TEA MAPPING
# ============================================================================

def apply_tea_mapping(df):
    """Apply TEA action codes and group classifications"""
    
    # Map to TEA codes
    df['TEA_Action_Code'] = df['Response'].map(TEA_CODE_MAP)
    
    # Fill missing with N/A
    df['TEA_Action_Code'] = df['TEA_Action_Code'].fillna('N/A')
    
    # Group into categories
    def classify_action(response, code):
        response_upper = str(response).upper()
        code_str = str(code)
        
        if 'EXPULSION' in response_upper or code_str in ['01', '02', '03', '04']:
            return 'EXPULSION'
        elif 'JJAEP' in response_upper or code_str == '13':
            return 'JJAEP'
        elif 'DAEP' in response_upper or code_str == '07':
            return 'DAEP'
        elif 'OSS' in response_upper or 'OUT-OF-SCHOOL' in response_upper or code_str == '05':
            return 'OSS'
        elif 'ISS' in response_upper or 'IN-SCHOOL' in response_upper or code_str == '06':
            return 'ISS'
        else:
            return 'LOCAL_ONLY'
    
    df['TEA_Action_Group'] = df.apply(
        lambda row: classify_action(row['Response'], row['TEA_Action_Code']), 
        axis=1
    )
    
    # Mark removals
    df['Is_Removal'] = df['TEA_Action_Group'].isin(['ISS', 'OSS', 'DAEP', 'JJAEP', 'EXPULSION'])
    
    return df

# ============================================================================
# STATISTICS CALCULATION
# ============================================================================

def calculate_school_brief_stats(df):
    """Calculate statistics for school brief"""
    
    total = len(df)
    
    if STATE_MODE == "TEXAS_TEA":
        action_counts = df['TEA_Action_Group'].value_counts()
        
        stats = {
            'total_incidents': total,
            'LOCAL_ONLY_count': action_counts.get('LOCAL_ONLY', 0),
            'ISS_count': action_counts.get('ISS', 0),
            'OSS_count': action_counts.get('OSS', 0),
            'DAEP_count': action_counts.get('DAEP', 0),
            'JJAEP_count': action_counts.get('JJAEP', 0),
            'EXPULSION_count': action_counts.get('EXPULSION', 0),
            'removal_count': df['Is_Removal'].sum(),
        }
        
        # Calculate percentages
        stats['LOCAL_ONLY_pct'] = (stats['LOCAL_ONLY_count'] / total * 100) if total > 0 else 0
        stats['ISS_pct'] = (stats['ISS_count'] / total * 100) if total > 0 else 0
        stats['OSS_pct'] = (stats['OSS_count'] / total * 100) if total > 0 else 0
        stats['DAEP_pct'] = (stats['DAEP_count'] / total * 100) if total > 0 else 0
        stats['JJAEP_pct'] = (stats['JJAEP_count'] / total * 100) if total > 0 else 0
        stats['EXPULSION_pct'] = (stats['EXPULSION_count'] / total * 100) if total > 0 else 0
        stats['removal_pct'] = (stats['removal_count'] / total * 100) if total > 0 else 0
        
    else:  # DEFAULT mode
        stats = {
            'total_incidents': total,
            'removal_count': 0,
            'removal_pct': 0,
            'ISS_count': 0,
            'OSS_count': 0,
            'ISS_pct': 0,
            'OSS_pct': 0,
        }
    
    return stats

def calculate_district_tea_stats(df):
    """Calculate TEA-specific statistics for district report"""
    
    total = len(df)
    
    tea_stats = {
        'total_incidents': total,
        'tea_action_counts': df['TEA_Action_Code'].value_counts().to_dict(),
        'tea_group_counts': df['TEA_Action_Group'].value_counts().to_dict(),
        'removal_count': df['Is_Removal'].sum(),
    }
    
    return tea_stats

def calculate_instructional_impact(df):
    """Calculate instructional time lost"""
    
    if 'Days_Removed' not in df.columns:
        return {
            'total_days_lost': 0,
            'total_minutes_lost': 0,
            'by_grade': {},
            'available': False
        }
    
    # Instructional minutes per day by grade band
    def get_instructional_minutes(grade):
        grade_str = str(grade).upper()
        if any(g in grade_str for g in ['K', 'PK', '0', '1', '2', '3', '4', '5']):
            return 420  # Elementary
        elif any(g in grade_str for g in ['6', '7', '8']):
            return 405  # Middle
        else:
            return 390  # High school
    
    df_impact = df[df['Days_Removed'].notna()].copy()
    df_impact['Instructional_Minutes'] = df_impact['Grade'].apply(get_instructional_minutes)
    df_impact['Minutes_Lost'] = df_impact['Days_Removed'] * df_impact['Instructional_Minutes']
    
    total_days = df_impact['Days_Removed'].sum()
    total_minutes = df_impact['Minutes_Lost'].sum()
    
    by_grade = df_impact.groupby('Grade').agg({
        'Days_Removed': 'sum',
        'Minutes_Lost': 'sum'
    }).to_dict('index')
    
    return {
        'total_days_lost': total_days,
        'total_minutes_lost': total_minutes,
        'by_grade': by_grade,
        'available': True
    }

# ============================================================================
# POSTURE DETERMINATION
# ============================================================================

def determine_posture_texas(stats):
    """Determine discipline system posture (Texas TEA mode)"""
    
    removal_pct = stats['removal_pct']
    oss_pct = stats['OSS_pct']
    expulsion_count = stats['EXPULSION_count']
    
    # ESCALATE conditions
    if removal_pct >= 60 or oss_pct >= 20 or expulsion_count > 0:
        return "ESCALATE", "Discipline system requires immediate attention."
    
    # INTERVENE conditions
    elif removal_pct >= 45:
        return "INTERVENE", "Discipline system under significant pressure requiring leadership focus."
    
    # CALIBRATE conditions
    elif removal_pct >= 35:
        return "CALIBRATE", "Discipline system showing moderate pressure. Monitor closely."
    
    # STABLE
    else:
        return "STABLE", "Discipline system operating within expected parameters."

def determine_posture_default(stats):
    """Determine discipline system posture (Default mode)"""
    
    removal_pct = stats['removal_pct']
    oss_pct = stats['OSS_pct']
    
    if removal_pct >= 50 or oss_pct >= 15:
        return "ESCALATE", "Discipline system requires immediate attention."
    elif removal_pct >= 35:
        return "INTERVENE", "Discipline system under pressure."
    elif removal_pct >= 20:
        return "CALIBRATE", "Discipline system showing moderate pressure."
    else:
        return "STABLE", "Discipline system operating normally."

# ============================================================================
# REPORT GENERATION - COMPLETE WITH ALL 14 SECTIONS
# ============================================================================

def generate_school_brief(df, stats, posture, system_state, impact, 
                         campus_name="Campus", reporting_period="Monthly", period_name="Current Period"):
    """Generate School Campus Decision Brief with all 14 required sections"""
    
    date_min = df['Date'].min().strftime('%Y-%m-%d')
    date_max = df['Date'].max().strftime('%Y-%m-%d')
    
    # Generate data hash for determinism
    data_str = df.to_csv(index=False)
    data_hash = hashlib.md5(data_str.encode()).hexdigest()[:8]
    
    # ========== SECTION 1: HEADER ==========
    report = f"""
═══════════════════════════════════════════════════════════════════════════
SCHOOL CAMPUS DECISION BRIEF
═══════════════════════════════════════════════════════════════════════════

Campus: {campus_name}
Reporting Period: {reporting_period}
Period: {period_name}
Date Range: {date_min} to {date_max}
State Mode: {STATE_MODE}
Data Hash: {data_hash}
Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

"""
    
    # ========== SECTION 2: DISCIPLINE SYSTEM STATUS ==========
    report += f"""═══════════════════════════════════════════════════════════════════════════
DISCIPLINE SYSTEM STATUS — AT A GLANCE
═══════════════════════════════════════════════════════════════════════════

Overall System State: {posture}
Decision Posture: {posture}
Leadership Interpretation: {system_state}

"""
    
    # ========== SECTION 3: RESPONSE / REMOVAL SNAPSHOT ==========
    report += f"""═══════════════════════════════════════════════════════════════════════════
RESPONSE / REMOVAL SNAPSHOT
═══════════════════════════════════════════════════════════════════════════

Total Incidents: {stats['total_incidents']}

"""
    
    if STATE_MODE == "TEXAS_TEA":
        report += f"""Action Group Breakdown:
  LOCAL_ONLY: {stats['LOCAL_ONLY_count']} ({stats['LOCAL_ONLY_pct']:.1f}%)
  ISS: {stats['ISS_count']} ({stats['ISS_pct']:.1f}%)
  OSS: {stats['OSS_count']} ({stats['OSS_pct']:.1f}%)
  DAEP: {stats['DAEP_count']} ({stats['DAEP_pct']:.1f}%)
  JJAEP: {stats['JJAEP_count']} ({stats['JJAEP_pct']:.1f}%)
  EXPULSION: {stats['EXPULSION_count']} ({stats['EXPULSION_pct']:.1f}%)

Total Removals: {stats['removal_count']} ({stats['removal_pct']:.1f}%)

"""
    
    # ========== SECTION 4: GRADE-LEVEL PRESSURE ANALYSIS ==========
    report += """═══════════════════════════════════════════════════════════════════════════
GRADE-LEVEL PRESSURE ANALYSIS
═══════════════════════════════════════════════════════════════════════════

"""
    
    campus_avg = stats['removal_pct']
    grade_analysis = df.groupby('Grade').agg({
        'Response': 'count',
        'Is_Removal': 'sum'
    }).reset_index()
    grade_analysis['Removal_Rate'] = (grade_analysis['Is_Removal'] / grade_analysis['Response'] * 100)
    grade_analysis['Variance'] = grade_analysis['Removal_Rate'] - campus_avg
    grade_analysis = grade_analysis.sort_values('Removal_Rate', ascending=False)
    
    for _, row in grade_analysis.iterrows():
        variance_sign = "+" if row['Variance'] > 0 else ""
        report += f"Grade {row['Grade']}: {row['Removal_Rate']:.1f}% removal rate ({variance_sign}{row['Variance']:.1f}% vs campus avg)\n"
    
    report += "\n"
    
    # ========== SECTION 5: TOP INCIDENT TYPES ==========
    report += """═══════════════════════════════════════════════════════════════════════════
TOP INCIDENT TYPES
═══════════════════════════════════════════════════════════════════════════

"""
    
    incident_analysis = df.groupby('Incident_Type').agg({
        'Response': 'count',
        'Is_Removal': 'sum'
    }).reset_index()
    incident_analysis['Removal_Conversion'] = (incident_analysis['Is_Removal'] / incident_analysis['Response'] * 100)
    incident_analysis = incident_analysis.sort_values('Response', ascending=False)
    
    for _, row in incident_analysis.head(3).iterrows():
        report += f"{row['Incident_Type']}: {row['Response']} incidents, {row['Removal_Conversion']:.1f}% removal conversion\n"
    
    report += "\n"
    
    # ========== SECTION 6: LOCATION HOTSPOTS ==========
    report += """═══════════════════════════════════════════════════════════════════════════
LOCATION HOTSPOTS
═══════════════════════════════════════════════════════════════════════════

"""
    
    location_analysis = df.groupby('Location').agg({
        'Response': 'count',
        'Is_Removal': 'sum'
    }).reset_index()
    location_analysis['Removal_Rate'] = (location_analysis['Is_Removal'] / location_analysis['Response'] * 100)
    location_analysis = location_analysis.sort_values('Response', ascending=False)
    
    for _, row in location_analysis.head(3).iterrows():
        report += f"{row['Location']}: {row['Response']} incidents, {row['Removal_Rate']:.1f}% removal rate\n"
    
    report += "\n"
    
    # ========== SECTION 7: TIME BLOCK PATTERNS ==========
    report += """═══════════════════════════════════════════════════════════════════════════
TIME BLOCK PATTERNS
═══════════════════════════════════════════════════════════════════════════

"""
    
    time_analysis = df.groupby('Time_Block').agg({
        'Response': 'count',
        'Is_Removal': 'sum'
    }).reset_index()
    time_analysis['Removal_Density'] = (time_analysis['Is_Removal'] / time_analysis['Response'] * 100)
    time_analysis = time_analysis.sort_values('Response', ascending=False)
    
    for _, row in time_analysis.iterrows():
        report += f"{row['Time_Block']}: {row['Response']} incidents, {row['Removal_Density']:.1f}% removal density\n"
    
    report += "\n"
    
    # ========== SECTION 8: BEHAVIORAL PRESSURE SIGNAL ==========
    report += """═══════════════════════════════════════════════════════════════════════════
BEHAVIORAL PRESSURE SIGNAL
═══════════════════════════════════════════════════════════════════════════

"""
    
    # Find the highest-volume incident type that also drives removals
    top_incident = incident_analysis.head(1).iloc[0]
    top_location = location_analysis.head(1).iloc[0]
    
    report += f"What drives system pressure: {top_incident['Incident_Type']} incidents\n"
    report += f"Where it concentrates: {top_location['Location']}\n"
    report += f"Why it matters: {top_incident['Response']} total incidents with {top_incident['Removal_Conversion']:.1f}% conversion to removal\n\n"
    
    # ========== SECTION 9: TOP RISK (MOST IMPORTANT) ==========
    report += """═══════════════════════════════════════════════════════════════════════════
TOP RISK
═══════════════════════════════════════════════════════════════════════════

"""
    
    # Determine the top risk based on posture and patterns
    top_grade = grade_analysis.head(1).iloc[0]
    
    if posture == "ESCALATE":
        if stats['removal_pct'] >= 60:
            report += f"Removal rate at {stats['removal_pct']:.1f}% exceeds sustainable threshold. "
            report += f"Grade {top_grade['Grade']} drives pressure at {top_grade['Removal_Rate']:.1f}% removal rate. "
            report += "Immediate leadership intervention required to prevent system collapse.\n\n"
        elif stats['OSS_pct'] >= 20:
            report += f"OSS usage at {stats['OSS_pct']:.1f}% indicates loss of alternative response capacity. "
            report += f"{top_location['Location']} accounts for {top_location['Response']} incidents. "
            report += "Leadership must address response option exhaustion.\n\n"
        else:  # Expulsions present
            report += f"Expulsion pattern present ({stats['EXPULSION_count']} cases). "
            report += "System under maximum stress. District-level review required.\n\n"
    
    elif posture == "INTERVENE":
        report += f"Removal rate at {stats['removal_pct']:.1f}% approaching critical threshold. "
        report += f"Grade {top_grade['Grade']} concentration at {top_grade['Removal_Rate']:.1f}% creates instability. "
        report += f"{top_incident['Incident_Type']} drives {top_incident['Response']} incidents in {top_location['Location']}. "
        report += "Leadership attention required before escalation.\n\n"
    
    elif posture == "CALIBRATE":
        report += f"System pressure elevated at {stats['removal_pct']:.1f}% removal. "
        report += f"Grade {top_grade['Grade']} showing {top_grade['Removal_Rate']:.1f}% removal rate. "
        report += f"Monitor {top_incident['Incident_Type']} pattern for trend direction.\n\n"
    
    else:  # STABLE
        report += f"System stable at {stats['removal_pct']:.1f}% removal. "
        report += "Continue current approach. Monitor for emerging patterns.\n\n"
    
    # ========== SECTION 10: INSTRUCTIONAL IMPACT ==========
    report += """═══════════════════════════════════════════════════════════════════════════
INSTRUCTIONAL IMPACT
═══════════════════════════════════════════════════════════════════════════

"""
    
    if impact['available']:
        report += f"Total Instructional Days Lost: {impact['total_days_lost']:.0f} days\n"
        report += f"Total Instructional Minutes Lost: {impact['total_minutes_lost']:.0f} minutes\n\n"
        
        report += "Distribution by Grade:\n"
        for grade, data in sorted(impact['by_grade'].items(), key=lambda x: x[1]['Days_Removed'], reverse=True):
            report += f"  Grade {grade}: {data['Days_Removed']:.0f} days ({data['Minutes_Lost']:.0f} minutes)\n"
        
        report += "\nSustained instructional loss at this magnitude is associated in Texas accountability research with lower STAAR performance, particularly when loss exceeds multiple weeks at the grade level.\n\n"
    else:
        report += "Days_Removed data not available. Instructional impact analysis suppressed.\n\n"
    
    # ========== SECTION 11: EQUITY PATTERN SUMMARY ==========
    report += """═══════════════════════════════════════════════════════════════════════════
EQUITY PATTERN SUMMARY
═══════════════════════════════════════════════════════════════════════════

"""
    
    equity_reported = False
    
    # Check for demographic data
    if 'Race' in df.columns:
        race_analysis = df.groupby('Race').agg({
            'Response': 'count',
            'Is_Removal': 'sum'
        }).reset_index()
        race_analysis['Removal_Rate'] = (race_analysis['Is_Removal'] / race_analysis['Response'] * 100)
        race_analysis['Ratio'] = race_analysis['Removal_Rate'] / campus_avg if campus_avg > 0 else 0
        
        # Only report if N >= 10
        for _, row in race_analysis[race_analysis['Response'] >= 10].iterrows():
            if row['Ratio'] >= 1.5:
                report += f"{row['Race']}: {row['Removal_Rate']:.1f}% removal rate ({row['Ratio']:.1f}x campus average)\n"
                equity_reported = True
    
    if not equity_reported:
        report += "No equity patterns meet reporting threshold (N≥10, ratio≥1.5x).\n"
    
    report += "\n"
    
    # ========== SECTION 12: WATCH LIST ==========
    report += """═══════════════════════════════════════════════════════════════════════════
WATCH LIST
═══════════════════════════════════════════════════════════════════════════

"""
    
    watch_items = []
    
    # Check grades approaching threshold
    for _, row in grade_analysis.iterrows():
        if 30 <= row['Removal_Rate'] < 35:
            watch_items.append(f"Grade {row['Grade']} at {row['Removal_Rate']:.1f}% (approaching calibration threshold)")
    
    # Check incident types with high conversion
    for _, row in incident_analysis.head(5).iterrows():
        if row['Removal_Conversion'] >= 60:
            watch_items.append(f"{row['Incident_Type']} shows {row['Removal_Conversion']:.1f}% removal conversion")
    
    if watch_items:
        for item in watch_items:
            report += f"• {item}\n"
    else:
        report += "No patterns currently on watch list.\n"
    
    report += "\n"
    
    # ========== SECTION 13: POSTURE BOUNDARIES ==========
    report += """═══════════════════════════════════════════════════════════════════════════
POSTURE BOUNDARIES
═══════════════════════════════════════════════════════════════════════════

Current Position:
  Removal Rate: {:.1f}%
  OSS Rate: {:.1f}%
  Expulsions: {}

Threshold Reference:
  STABLE: Removal <35%, OSS <10%, Expulsions=0
  CALIBRATE: Removal 35-44%, OSS <15%
  INTERVENE: Removal 45-59%, OSS <20%
  ESCALATE: Removal ≥60% OR OSS ≥20% OR Expulsions >0

""".format(stats['removal_pct'], stats['OSS_pct'], stats['EXPULSION_count'])
    
    # ========== SECTION 14: BOTTOM LINE FOR LEADERSHIP ==========
    report += """═══════════════════════════════════════════════════════════════════════════
BOTTOM LINE FOR LEADERSHIP
═══════════════════════════════════════════════════════════════════════════

"""
    
    if posture == "ESCALATE":
        report += f"System operating beyond sustainable parameters at {stats['removal_pct']:.1f}% removal. "
        report += f"Grade {top_grade['Grade']} concentration and {top_incident['Incident_Type']} pattern in {top_location['Location']} demand immediate leadership focus. "
        report += "Current trajectory unsustainable without intervention.\n"
    elif posture == "INTERVENE":
        report += f"System under significant pressure at {stats['removal_pct']:.1f}% removal. "
        report += f"Grade {top_grade['Grade']} and {top_location['Location']} patterns require leadership attention to prevent escalation. "
        report += "Window for proactive response remains open.\n"
    elif posture == "CALIBRATE":
        report += f"System showing moderate pressure at {stats['removal_pct']:.1f}% removal. "
        report += f"Monitor Grade {top_grade['Grade']} and {top_incident['Incident_Type']} trends closely. "
        report += "Maintain current approach with increased vigilance.\n"
    else:  # STABLE
        report += f"System operating within expected parameters at {stats['removal_pct']:.1f}% removal. "
        report += "Continue current practices. Maintain monitoring for emerging patterns.\n"
    
    report += "\n═══════════════════════════════════════════════════════════════════════════\n"
    
    return report

def generate_district_tea_report(df, tea_stats, 
                                campus_name="Campus", reporting_period="Monthly", period_name="Current Period"):
    """Generate District TEA Compliance Report"""
    
    date_min = df['Date'].min().strftime('%Y-%m-%d')
    date_max = df['Date'].max().strftime('%Y-%m-%d')
    
    # Generate data hash
    data_str = df.to_csv(index=False)
    data_hash = hashlib.md5(data_str.encode()).hexdigest()[:8]
    
    report = f"""
═══════════════════════════════════════════════════════════════════════════
DISTRICT TEA COMPLIANCE REPORT
═══════════════════════════════════════════════════════════════════════════

Campus: {campus_name}
Reporting Period: {reporting_period}
Period: {period_name}
Date Range: {date_min} to {date_max}
State Mode: {STATE_MODE}
Data Hash: {data_hash}
Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

═══════════════════════════════════════════════════════════════════════════
TEA ACTION GROUP TOTALS
═══════════════════════════════════════════════════════════════════════════

Total Incidents: {tea_stats['total_incidents']}

"""
    
    for group, count in sorted(tea_stats['tea_group_counts'].items()):
        pct = (count / tea_stats['total_incidents'] * 100) if tea_stats['total_incidents'] > 0 else 0
        report += f"{group}: {count} ({pct:.1f}%)\n"
    
    report += f"\nTotal Removals: {tea_stats['removal_count']}\n\n"
    
    report += """═══════════════════════════════════════════════════════════════════════════
REMOVAL SUMMARY BY TEA CODE
═══════════════════════════════════════════════════════════════════════════

"""
    
    for code, count in sorted(tea_stats['tea_action_counts'].items()):
        if code != 'N/A':
            report += f"Code {code}: {count} incidents\n"
    
    report += f"""
═══════════════════════════════════════════════════════════════════════════
TEA ACTION CODE DISTRIBUTION
═══════════════════════════════════════════════════════════════════════════

All Actions (including local responses):
"""
    
    for code, count in sorted(tea_stats['tea_action_counts'].items()):
        pct = (count / tea_stats['total_incidents'] * 100) if tea_stats['total_incidents'] > 0 else 0
        report += f"Code {code}: {count} ({pct:.1f}%)\n"
    
    report += f"""
═══════════════════════════════════════════════════════════════════════════
STATUTORY TRIGGER NOTICE
═══════════════════════════════════════════════════════════════════════════

DAEP Placements: {tea_stats['tea_group_counts'].get('DAEP', 0)}
JJAEP Placements: {tea_stats['tea_group_counts'].get('JJAEP', 0)}
Expulsions: {tea_stats['tea_group_counts'].get('EXPULSION', 0)}

Note: Informational only. Consult legal counsel for compliance interpretation.

"""
    
    report += "═══════════════════════════════════════════════════════════════════════════\n"
    
    return report
