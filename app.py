import streamlit as st
import pandas as pd
import sys
from io import StringIO
import tempfile
import os

# Import the analyzer functions
sys.path.append('/Users/derrickcalvert/Desktop')
from discipline_analyzer import (
    apply_tea_mapping,
    calculate_school_brief_stats,
    calculate_district_tea_stats,
    calculate_instructional_impact,
    determine_posture_texas,
    generate_school_brief,
    generate_district_tea_report,
    STATE_MODE
)

# Page config
st.set_page_config(
    page_title="Discipline Decision Brief Analyzer",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for professional styling
st.markdown("""
<style>
    /* Main color scheme */
    :root {
        --primary-color: #1e3a8a;
        --secondary-color: #3b82f6;
        --accent-color: #10b981;
        --text-dark: #1f2937;
        --text-light: #6b7280;
        --background-light: #f9fafb;
        --border-color: #e5e7eb;
    }
    
    /* Import better font */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
    
    /* Global font */
    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif;
    }
    
    /* Hide Streamlit branding */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    
    /* Main header styling */
    h1 {
        color: var(--primary-color);
        font-weight: 700;
        font-size: 2.5rem;
        margin-bottom: 0.5rem;
        letter-spacing: -0.02em;
    }
    
    /* Subtitle styling */
    .subtitle {
        color: var(--text-light);
        font-size: 1.1rem;
        font-weight: 500;
        margin-bottom: 2rem;
        padding-bottom: 1.5rem;
        border-bottom: 2px solid var(--border-color);
    }
    
    /* Section headers */
    h2 {
        color: var(--text-dark);
        font-weight: 600;
        font-size: 1.5rem;
        margin-top: 2rem;
        margin-bottom: 1rem;
    }
    
    h3 {
        color: var(--text-dark);
        font-weight: 600;
        font-size: 1.25rem;
        margin-top: 1.5rem;
        margin-bottom: 0.75rem;
    }
    
    /* Info boxes */
    .stAlert {
        border-radius: 0.5rem;
        border-left: 4px solid var(--secondary-color);
        background-color: #eff6ff;
        padding: 1rem 1.25rem;
    }
    
    /* Success messages */
    .success-box {
        background-color: #d1fae5;
        border-left: 4px solid var(--accent-color);
        border-radius: 0.5rem;
        padding: 1rem 1.25rem;
        margin: 1rem 0;
    }
    
    /* Metrics styling */
    [data-testid="stMetricValue"] {
        font-size: 2rem;
        font-weight: 700;
        color: var(--primary-color);
    }
    
    [data-testid="stMetricLabel"] {
        font-size: 0.875rem;
        font-weight: 600;
        color: var(--text-light);
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }
    
    /* Button styling */
    .stButton > button {
        background-color: var(--primary-color);
        color: white;
        border: none;
        border-radius: 0.5rem;
        padding: 0.75rem 2rem;
        font-weight: 600;
        font-size: 1rem;
        transition: all 0.2s;
        box-shadow: 0 1px 3px rgba(0,0,0,0.1);
    }
    
    .stButton > button:hover {
        background-color: #1e40af;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        transform: translateY(-1px);
    }
    
    /* Download button styling */
    .stDownloadButton > button {
        background-color: var(--accent-color);
        color: white;
        border: none;
        border-radius: 0.5rem;
        padding: 0.5rem 1.5rem;
        font-weight: 600;
        font-size: 0.875rem;
        transition: all 0.2s;
    }
    
    .stDownloadButton > button:hover {
        background-color: #059669;
        transform: translateY(-1px);
    }
    
    /* File uploader */
    [data-testid="stFileUploader"] {
        background-color: white;
        border: 2px dashed var(--border-color);
        border-radius: 0.75rem;
        padding: 2rem;
        transition: all 0.2s;
    }
    
    [data-testid="stFileUploader"]:hover {
        border-color: var(--secondary-color);
        background-color: var(--background-light);
    }
    
    /* Tabs */
    .stTabs [data-baseweb="tab-list"] {
        gap: 0.5rem;
        background-color: var(--background-light);
        padding: 0.5rem;
        border-radius: 0.5rem;
    }
    
    .stTabs [data-baseweb="tab"] {
        background-color: transparent;
        border-radius: 0.375rem;
        padding: 0.75rem 1.5rem;
        font-weight: 600;
        color: var(--text-light);
    }
    
    .stTabs [aria-selected="true"] {
        background-color: white;
        color: var(--primary-color);
        box-shadow: 0 1px 3px rgba(0,0,0,0.1);
    }
    
    /* Sidebar styling */
    [data-testid="stSidebar"] {
        background-color: var(--background-light);
        padding: 2rem 1rem;
    }
    
    [data-testid="stSidebar"] h2 {
        color: var(--primary-color);
        font-size: 1.25rem;
        margin-bottom: 1rem;
    }
    
    /* Expander */
    .streamlit-expanderHeader {
        background-color: var(--background-light);
        border-radius: 0.5rem;
        font-weight: 600;
        color: var(--text-dark);
    }
    
    /* Text area */
    .stTextArea textarea {
        border-radius: 0.5rem;
        border-color: var(--border-color);
        font-family: 'Monaco', 'Menlo', monospace;
        font-size: 0.875rem;
    }
    
    /* Cards/containers */
    .element-container {
        margin-bottom: 1rem;
    }
    
    /* Demo dataset cards */
    .demo-card {
        background-color: white;
        border: 1px solid var(--border-color);
        border-radius: 0.75rem;
        padding: 1.5rem;
        margin-bottom: 1rem;
        box-shadow: 0 1px 3px rgba(0,0,0,0.05);
    }
    
    .demo-card h4 {
        color: var(--primary-color);
        font-weight: 600;
        margin-bottom: 0.75rem;
    }
    
    .demo-card ul {
        color: var(--text-light);
        font-size: 0.9rem;
        line-height: 1.6;
    }
</style>
""", unsafe_allow_html=True)

# Header
st.markdown("# 📊 Discipline Decision Brief Analyzer")
st.markdown('<div class="subtitle">Texas TEA Compliance Mode | Deterministic Rules-Based Analysis</div>', unsafe_allow_html=True)

# Sidebar
with st.sidebar:
    st.markdown("## About This Tool")
    
    st.markdown("""
    **Provides:**
    - School Brief (Principal-facing)
    - District TEA Report (Compliance)
    
    **Required Columns:**
    - Date
    - Grade  
    - Incident_Type
    - Location
    - Time_Block
    - Response
    
    **Optional Columns:**
    - TEA_Action_Code
    - TEA_Action_Reason_Code
    - Days_Removed
    """)
    
    st.markdown("---")
    st.markdown("**Powered by Empower52**")
    st.markdown("[www.empower52.com](https://www.empower52.com)")

# Main content
st.markdown("## Upload Your Discipline Data")
st.markdown("Upload a CSV or Excel file containing your discipline incident data.")

# File uploader
uploaded_file = st.file_uploader(
    "Choose a file",
    type=['csv', 'xlsx', 'xls'],
    help="Upload CSV or Excel file with discipline data",
    label_visibility="collapsed"
)

if uploaded_file is not None:
    try:
        # Load the file
        if uploaded_file.name.endswith('.csv'):
            df = pd.read_csv(uploaded_file)
        else:
            df = pd.read_excel(uploaded_file)
        
        # Validate required columns
        required = ['Date', 'Grade', 'Incident_Type', 'Location', 'Time_Block', 'Response']
        missing = [col for col in required if col not in df.columns]
        
        if missing:
            st.error(f"❌ Missing required columns: {', '.join(missing)}")
            st.stop()
        
        # Convert Date to datetime
        df['Date'] = pd.to_datetime(df['Date'])
        
        # Show success message
        st.success(f"✅ File loaded successfully! Found **{len(df)} incidents**")
        
        # Show data preview
        with st.expander("📋 Preview Data (first 10 rows)", expanded=False):
            st.dataframe(df.head(10), use_container_width=True)
        
        # Generate reports button
        st.markdown("<br>", unsafe_allow_html=True)
        
        if st.button("🚀 Generate Reports", type="primary", use_container_width=True):
            
            with st.spinner("Analyzing discipline data..."):
                
                # Apply TEA mapping
                if STATE_MODE == "TEXAS_TEA":
                    df = apply_tea_mapping(df)
                
                # Calculate stats
                school_stats = calculate_school_brief_stats(df)
                
                # Determine posture
                if STATE_MODE == "TEXAS_TEA":
                    posture, system_state = determine_posture_texas(school_stats)
                else:
                    from discipline_analyzer import determine_posture_default
                    posture, system_state = determine_posture_default(school_stats)
                
                # Calculate impact
                impact = calculate_instructional_impact(df)
                
                # Generate reports
                school_brief = generate_school_brief(df, school_stats, posture, system_state, impact)
                
                if STATE_MODE == "TEXAS_TEA":
                    tea_stats = calculate_district_tea_stats(df)
                    district_report = generate_district_tea_report(df, tea_stats)
            
            # Success message
            st.markdown("<br>", unsafe_allow_html=True)
            st.success("✅ **Analysis Complete!**")
            
            # Key metrics
            st.markdown("### Key Findings")
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.metric("Decision Posture", posture)
            
            with col2:
                st.metric("Total Incidents", f"{school_stats['total_incidents']:,}")
            
            with col3:
                removal_pct = school_stats['ISS_pct'] + school_stats['OSS_pct']
                if STATE_MODE == "TEXAS_TEA":
                    removal_pct += school_stats['DAEP_pct'] + school_stats['JJAEP_pct']
                st.metric("Removal Rate", f"{removal_pct:.1f}%")
            
            # Reports tabs
            st.markdown("<br>", unsafe_allow_html=True)
            tab1, tab2 = st.tabs(["📄 School Brief", "📋 District TEA Report"])
            
            with tab1:
                # Parse and display School Brief beautifully
                st.markdown("### 📄 School Brief (Principal-Facing)")
                
                # Display formatted report
                lines = school_brief.split('\n')
                in_section = False
                section_content = []
                
                for line in lines:
                    # Skip decoration lines
                    if '═' in line or '─' in line:
                        continue
                    
                    # Section headers
                    if line.strip() and line.strip().isupper() and len(line.strip()) > 10:
                        if section_content:
                            st.markdown('<div style="background-color: white; padding: 1.5rem; border-radius: 0.5rem; margin-bottom: 1rem; border-left: 4px solid #3b82f6;">' + '<br>'.join(section_content) + '</div>', unsafe_allow_html=True)
                            section_content = []
                        st.markdown(f"#### {line.strip()}")
                        in_section = True
                    # Content lines
                    elif line.strip():
                        # Highlight key metrics
                        if 'Decision Posture:' in line or 'Overall System State:' in line:
                            parts = line.split(':')
                            if len(parts) == 2:
                                st.markdown(f"**{parts[0]}:** <span style='color: #1e3a8a; font-weight: 700; font-size: 1.1rem;'>{parts[1]}</span>", unsafe_allow_html=True)
                        elif line.startswith('Total Incidents:') or 'minutes' in line.lower() or 'days' in line.lower():
                            st.markdown(f"**{line}**")
                        else:
                            section_content.append(line.replace('  ', '&nbsp;&nbsp;'))
                
                # Flush remaining content
                if section_content:
                    st.markdown('<div style="background-color: white; padding: 1.5rem; border-radius: 0.5rem; margin-bottom: 1rem; border-left: 4px solid #3b82f6;">' + '<br>'.join(section_content) + '</div>', unsafe_allow_html=True)
                
                # Download button
                st.markdown("<br>", unsafe_allow_html=True)
                st.download_button(
                    label="📥 Download School Brief (Plain Text)",
                    data=school_brief,
                    file_name=f"{uploaded_file.name.split('.')[0]}_SCHOOL_BRIEF.txt",
                    mime="text/plain",
                    use_container_width=True
                )
            
            with tab2:
                if STATE_MODE == "TEXAS_TEA":
                    st.markdown("### 📋 District TEA Report (Compliance)")
                    
                    # Parse and display TEA Report
                    lines = district_report.split('\n')
                    section_content = []
                    
                    for line in lines:
                        # Skip decoration lines
                        if '═' in line or '─' in line:
                            continue
                        
                        # Section headers
                        if line.strip() and line.strip().isupper() and len(line.strip()) > 10:
                            if section_content:
                                st.markdown('<div style="background-color: white; padding: 1.5rem; border-radius: 0.5rem; margin-bottom: 1rem; border-left: 4px solid #10b981;">' + '<br>'.join(section_content) + '</div>', unsafe_allow_html=True)
                                section_content = []
                            st.markdown(f"#### {line.strip()}")
                        # Content lines
                        elif line.strip():
                            # Highlight TEA codes and percentages
                            if 'Code ' in line or '%' in line or 'Total TEA Actions' in line:
                                st.markdown(f"**{line}**")
                            else:
                                section_content.append(line.replace('  ', '&nbsp;&nbsp;'))
                    
                    # Flush remaining content
                    if section_content:
                        st.markdown('<div style="background-color: white; padding: 1.5rem; border-radius: 0.5rem; margin-bottom: 1rem; border-left: 4px solid #10b981;">' + '<br>'.join(section_content) + '</div>', unsafe_allow_html=True)
                    
                    # Download button
                    st.markdown("<br>", unsafe_allow_html=True)
                    st.download_button(
                        label="📥 Download District Report (Plain Text)",
                        data=district_report,
                        file_name=f"{uploaded_file.name.split('.')[0]}_DISTRICT_TEA_REPORT.txt",
                        mime="text/plain",
                        use_container_width=True
                    )
                else:
                    st.info("District TEA Report only available in Texas mode")
    except Exception as e:
        st.error(f"❌ Error processing file: {str(e)}")
        with st.expander("See error details"):
            st.exception(e)

else:
    # Show info when no file uploaded
    st.info("👆 Upload your discipline data file to get started")
    
    # Demo datasets section
    st.markdown("<br><br>", unsafe_allow_html=True)
    st.markdown("## Demo Datasets")
    st.markdown("Download sample datasets to test the analyzer:")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("""
        <div class="demo-card">
            <h4>📗 STABLE Campus</h4>
            <ul>
                <li>68 incidents</li>
                <li>Elementary school profile</li>
                <li>92.6% non-removal responses</li>
            </ul>
        </div>
        
        <div class="demo-card">
            <h4>📙 CALIBRATE Campus</h4>
            <ul>
                <li>90 incidents</li>
                <li>Middle school profile</li>
                <li>Moderate ISS usage</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown("""
        <div class="demo-card">
            <h4>📘 INTERVENE Campus</h4>
            <ul>
                <li>108 incidents</li>
                <li>Middle school profile</li>
                <li>High ISS usage</li>
            </ul>
        </div>
        
        <div class="demo-card">
            <h4>📕 ESCALATE Campus</h4>
            <ul>
                <li>136 incidents</li>
                <li>High school profile</li>
                <li>High removal rates + expulsions</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)
