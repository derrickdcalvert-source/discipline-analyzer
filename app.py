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
    layout="wide"
)

# Header
st.title("📊 Discipline Decision Brief Analyzer")
st.markdown("**Texas TEA Compliance Mode** | Deterministic Rules-Based Analysis")
st.markdown("---")

# Sidebar info
with st.sidebar:
    st.header("About This Tool")
    st.markdown("""
    This analyzer provides:
    - **School Brief** (Principal-facing)
    - **District TEA Report** (Compliance)
    
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
    st.markdown("www.empower52.com")

# Main content
st.header("Upload Your Discipline Data")
st.markdown("Upload a CSV or Excel file containing your discipline incident data.")

# File uploader
uploaded_file = st.file_uploader(
    "Choose a file",
    type=['csv', 'xlsx', 'xls'],
    help="Upload CSV or Excel file with discipline data"
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
        
        # Show data preview
        st.success(f"✅ File loaded successfully! Found {len(df)} incidents.")
        
        with st.expander("Preview Data (first 10 rows)"):
            st.dataframe(df.head(10))
        
        # Run analysis button
        if st.button("🚀 Generate Reports", type="primary"):
            
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
                
            # Display results
            st.success("✅ Analysis Complete!")
            
            # Show key metrics
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.metric("Decision Posture", posture)
            
            with col2:
                st.metric("Total Incidents", school_stats['total_incidents'])
            
            with col3:
                removal_pct = school_stats['ISS_pct'] + school_stats['OSS_pct']
                if STATE_MODE == "TEXAS_TEA":
                    removal_pct += school_stats['DAEP_pct'] + school_stats['JJAEP_pct']
                st.metric("Removal Rate", f"{removal_pct:.1f}%")
            
            # Tabs for reports
            tab1, tab2 = st.tabs(["📄 School Brief", "📋 District TEA Report"])
            
            with tab1:
                st.text_area(
                    "School Brief (Principal-Facing)",
                    school_brief,
                    height=400
                )
                
                # Download button
                st.download_button(
                    label="📥 Download School Brief",
                    data=school_brief,
                    file_name=f"{uploaded_file.name.split('.')[0]}_SCHOOL_BRIEF.txt",
                    mime="text/plain"
                )
            
            with tab2:
                if STATE_MODE == "TEXAS_TEA":
                    st.text_area(
                        "District TEA Report (Compliance)",
                        district_report,
                        height=400
                    )
                    
                    # Download button
                    st.download_button(
                        label="📥 Download District Report",
                        data=district_report,
                        file_name=f"{uploaded_file.name.split('.')[0]}_DISTRICT_TEA_REPORT.txt",
                        mime="text/plain"
                    )
                else:
                    st.info("District TEA Report only available in Texas mode")
        
    except Exception as e:
        st.error(f"❌ Error processing file: {str(e)}")
        st.exception(e)

else:
    # Show demo data info
    st.info("👆 Upload your discipline data file to get started")
    
    st.markdown("---")
    st.header("Demo Datasets")
    st.markdown("Download sample datasets to test the analyzer:")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("**📗 STABLE Campus**")
        st.markdown("- 68 incidents")
        st.markdown("- Elementary school profile")
        st.markdown("- 92.6% non-removal responses")
        
        st.markdown("**📙 CALIBRATE Campus**")
        st.markdown("- 90 incidents")
        st.markdown("- Middle school profile")
        st.markdown("- Moderate ISS usage")
    
    with col2:
        st.markdown("**📘 INTERVENE Campus**")
        st.markdown("- 108 incidents")
        st.markdown("- Middle school profile")
        st.markdown("- High ISS usage")
        
        st.markdown("**📕 ESCALATE Campus**")
        st.markdown("- 136 incidents")
        st.markdown("- High school profile")
        st.markdown("- High removal rates + expulsions")
