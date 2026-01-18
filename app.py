import streamlit as st
import pandas as pd
import sys
from io import StringIO, BytesIO
import tempfile
import os
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
from reportlab.lib.enums import TA_LEFT, TA_CENTER

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
    generate_district_consolidated_report,
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
    
    /* Mode detection box */
    .mode-box {
        background-color: #eff6ff;
        border: 2px solid var(--secondary-color);
        border-radius: 0.75rem;
        padding: 1.25rem;
        margin: 1.5rem 0;
    }
    
    .mode-box h4 {
        color: var(--primary-color);
        font-weight: 700;
        margin-bottom: 0.5rem;
    }
</style>
""", unsafe_allow_html=True)

# PDF Generation Functions
def generate_school_brief_pdf(school_brief_text, uploaded_filename, period_name):
    """Generate professional PDF for School Brief"""
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, topMargin=0.75*inch, bottomMargin=0.75*inch)
    story = []
    
    # Styles
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=24,
        textColor=colors.HexColor('#1e3a8a'),
        spaceAfter=6,
        alignment=TA_CENTER
    )
    subtitle_style = ParagraphStyle(
        'CustomSubtitle',
        parent=styles['Normal'],
        fontSize=11,
        textColor=colors.HexColor('#6b7280'),
        spaceAfter=20,
        alignment=TA_CENTER
    )
    heading_style = ParagraphStyle(
        'CustomHeading',
        parent=styles['Heading2'],
        fontSize=14,
        textColor=colors.HexColor('#1e3a8a'),
        spaceBefore=12,
        spaceAfter=8,
        bold=True
    )
    body_style = ParagraphStyle(
        'CustomBody',
        parent=styles['Normal'],
        fontSize=10,
        textColor=colors.HexColor('#1f2937'),
        spaceAfter=6,
        leading=14
    )
    
    # Posture icons
    posture_icons = {
        'STABLE': '✓',
        'CALIBRATE': '⚠',
        'INTERVENE': '⚡',
        'ESCALATE': '🚨'
    }
    icon = posture_icons.get(posture, '•')
    
    # Header
    story.append(Paragraph("📊 Discipline Decision Brief", title_style))
    story.append(Paragraph(f"School Brief — {period_name}", subtitle_style))
    story.append(Spacer(1, 0.2*inch))
    
    # Posture callout box
    posture_data = [[f"{icon} Decision Posture: {posture}"]]
    posture_table = Table(posture_data, colWidths=[6.5*inch])
    posture_color = {
        'STABLE': colors.HexColor('#d1fae5'),
        'CALIBRATE': colors.HexColor('#fef3c7'),
        'INTERVENE': colors.HexColor('#fed7aa'),
        'ESCALATE': colors.HexColor('#fecaca')
    }.get(posture, colors.HexColor('#f3f4f6'))
    
    posture_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), posture_color),
        ('TEXTCOLOR', (0, 0), (-1, -1), colors.HexColor('#1f2937')),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 14),
        ('TOPPADDING', (0, 0), (-1, -1), 12),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
        ('LEFTPADDING', (0, 0), (-1, -1), 12),
        ('RIGHTPADDING', (0, 0), (-1, -1), 12),
    ]))
    story.append(posture_table)
    story.append(Spacer(1, 0.3*inch))
    
    # Parse report sections
    lines = school_brief_text.split('\n')
    current_section = []
    
    for line in lines:
        line = line.strip()
        if not line or '═' in line or '─' in line:
            continue
        
        # Section headers (all caps, long)
        if line.isupper() and len(line) > 10:
            # Flush previous section
            if current_section:
                for content_line in current_section:
                    story.append(Paragraph(content_line, body_style))
                current_section = []
            story.append(Spacer(1, 0.15*inch))
            story.append(Paragraph(line, heading_style))
        else:
            # Regular content
            if 'Decision Posture:' in line or 'Overall System State:' in line:
                story.append(Paragraph(f"<b>{line}</b>", body_style))
            elif any(keyword in line for keyword in ['Total Incidents:', 'minutes', 'days', 'STABLE', 'CALIBRATE', 'INTERVENE', 'ESCALATE']):
                story.append(Paragraph(f"<b>{line}</b>", body_style))
            else:
                current_section.append(line)
    
    # Flush final section
    if current_section:
        for content_line in current_section:
            story.append(Paragraph(content_line, body_style))
    
    # Footer
    story.append(Spacer(1, 0.4*inch))
    footer_style = ParagraphStyle(
        'Footer',
        parent=styles['Normal'],
        fontSize=9,
        textColor=colors.HexColor('#9ca3af'),
        alignment=TA_CENTER
    )
    story.append(Paragraph("Powered by Empower52 | www.empower52.com", footer_style))
    
    # Build PDF
    doc.build(story)
    buffer.seek(0)
    return buffer

def generate_district_tea_pdf(district_report_text, uploaded_filename, period_name):
    """Generate professional PDF for District TEA Report"""
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, topMargin=0.75*inch, bottomMargin=0.75*inch)
    story = []
    
    # Styles
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=24,
        textColor=colors.HexColor('#1e3a8a'),
        spaceAfter=6,
        alignment=TA_CENTER
    )
    subtitle_style = ParagraphStyle(
        'CustomSubtitle',
        parent=styles['Normal'],
        fontSize=11,
        textColor=colors.HexColor('#6b7280'),
        spaceAfter=20,
        alignment=TA_CENTER
    )
    heading_style = ParagraphStyle(
        'CustomHeading',
        parent=styles['Heading2'],
        fontSize=14,
        textColor=colors.HexColor('#10b981'),
        spaceBefore=12,
        spaceAfter=8,
        bold=True
    )
    body_style = ParagraphStyle(
        'CustomBody',
        parent=styles['Normal'],
        fontSize=10,
        textColor=colors.HexColor('#1f2937'),
        spaceAfter=6,
        leading=14
    )
    
    # Header
    story.append(Paragraph("📋 District TEA Report", title_style))
    story.append(Paragraph(f"Texas Education Agency Compliance Report — {period_name}", subtitle_style))
    story.append(Spacer(1, 0.3*inch))
    
    # Parse report sections
    lines = district_report_text.split('\n')
    current_section = []
    
    for line in lines:
        line = line.strip()
        if not line or '═' in line or '─' in line:
            continue
        
        # Section headers
        if line.isupper() and len(line) > 10:
            # Flush previous section
            if current_section:
                for content_line in current_section:
                    story.append(Paragraph(content_line, body_style))
                current_section = []
            story.append(Spacer(1, 0.15*inch))
            story.append(Paragraph(line, heading_style))
        else:
            # Highlight codes and percentages
            if 'Code ' in line or '%' in line or 'Total TEA Actions' in line:
                story.append(Paragraph(f"<b>{line}</b>", body_style))
            else:
                current_section.append(line)
    
    # Flush final section
    if current_section:
        for content_line in current_section:
            story.append(Paragraph(content_line, body_style))
    
    # Footer
    story.append(Spacer(1, 0.4*inch))
    footer_style = ParagraphStyle(
        'Footer',
        parent=styles['Normal'],
        fontSize=9,
        textColor=colors.HexColor('#9ca3af'),
        alignment=TA_CENTER
    )
    story.append(Paragraph("Powered by Empower52 | www.empower52.com", footer_style))
    
    # Build PDF
    doc.build(story)
    buffer.seek(0)
    return buffer
def generate_district_consolidated_report_pdf(district_report_text, period_name):
    """Generate professional PDF for District Consolidated Report"""
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, topMargin=0.75*inch, bottomMargin=0.75*inch)
    story = []
    
    # Styles
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=24,
        textColor=colors.HexColor('#1e3a8a'),
        spaceAfter=6,
        alignment=TA_CENTER
    )
    subtitle_style = ParagraphStyle(
        'CustomSubtitle',
        parent=styles['Normal'],
        fontSize=11,
        textColor=colors.HexColor('#6b7280'),
        spaceAfter=20,
        alignment=TA_CENTER
    )
    heading_style = ParagraphStyle(
        'CustomHeading',
        parent=styles['Heading2'],
        fontSize=14,
        textColor=colors.HexColor('#1e3a8a'),
        spaceBefore=12,
        spaceAfter=8,
        bold=True
    )
    body_style = ParagraphStyle(
        'CustomBody',
        parent=styles['Normal'],
        fontSize=10,
        textColor=colors.HexColor('#1f2937'),
        spaceAfter=6,
        leading=14
    )
    
    # Header
    story.append(Paragraph("📊 District Consolidated Report", title_style))
    story.append(Paragraph(f"Multi-Campus Analysis — {period_name}", subtitle_style))
    story.append(Spacer(1, 0.3*inch))
    
    # Parse report sections
    lines = district_report_text.split('\n')
    
    for line in lines:
        line = line.strip()
        if not line or '═' in line or '─' in line:
            continue
        
        # Section headers (## markers)
        if line.startswith('## '):
            story.append(Spacer(1, 0.15*inch))
            story.append(Paragraph(line.replace('## ', ''), heading_style))
        # Bold items
        elif line.startswith('**') and line.endswith('**'):
            clean_line = line.replace('**', '')
            story.append(Paragraph(f"<b>{clean_line}</b>", body_style))
        # Key metrics
        elif any(keyword in line for keyword in ['ESCALATE', 'INTERVENE', 'CALIBRATE', 'STABLE', 'Total:', 'removal rate', '%']):
            story.append(Paragraph(f"<b>{line}</b>", body_style))
        # List items
        elif line.startswith('- '):
            story.append(Paragraph(f"• {line[2:]}", body_style))
        # Regular content
        else:
            story.append(Paragraph(line, body_style))
    
    # Footer
    story.append(Spacer(1, 0.4*inch))
    footer_style = ParagraphStyle(
        'Footer',
        parent=styles['Normal'],
        fontSize=9,
        textColor=colors.HexColor('#9ca3af'),
        alignment=TA_CENTER
    )
    story.append(Paragraph("Powered by Empower52 | www.empower52.com", footer_style))
    
    # Build PDF
    doc.build(story)
    buffer.seek(0)
    return buffer
# Header
st.markdown("# 📊 Discipline Decision Brief Analyzer")
st.markdown('<div class="subtitle">Texas TEA Compliance Mode | Deterministic Rules-Based Analysis | **Multi-File Support**</div>', unsafe_allow_html=True)

# Sidebar
with st.sidebar:
    st.markdown("## About This Tool")
    
    st.markdown("""
    **Provides:**
    - School Brief (Principal-facing)
    - District TEA Report (Compliance)
    
    **File Upload Modes:**
    - Single file: Standard analysis
    - Multiple files (same campus): Auto-consolidates
    - Multiple files (different campuses): District analysis
    
    **Required Columns:**
    - Date
    - Grade  
    - Incident_Type
    - Location
    - Time_Block
    - Response
    
    **Optional Columns:**
    - Campus (for multi-campus)
    - TEA_Action_Code
    - Days_Removed
    """)
    
    st.markdown("---")
    st.markdown("**Powered by Empower52**")
    st.markdown("[www.empower52.com](https://www.empower52.com)")

# Main content
st.markdown("## Configure Report Settings")

# Report configuration inputs
col1, col2, col3 = st.columns(3)

with col1:
    campus_name = st.text_input(
        "Campus/School Name",
        value="Campus",
        help="Enter the name of your campus or school"
    )

with col2:
    reporting_period = st.selectbox(
        "Reporting Period",
        options=["Monthly", "Weekly", "Bi-Weekly"],
        help="Select your reporting frequency"
    )

with col3:
    # Auto-suggest period name based on current date
    from datetime import datetime
    current_month = datetime.now().strftime("%B %Y")
    
    period_name = st.text_input(
        "Period Name",
        value=current_month if reporting_period == "Monthly" else "",
        placeholder="e.g., September 2024, Week 42",
        help="Enter the specific period (e.g., 'September 2024', 'Week 42, 2024')"
    )

st.markdown("<br>", unsafe_allow_html=True)
st.markdown("## Upload Your Discipline Data")
st.markdown("Upload one or more CSV/Excel files. System will automatically detect if files represent split data or multiple campuses.")

# MODIFIED: Multi-file uploader
uploaded_files = st.file_uploader(
    "Choose file(s)",
    type=['csv', 'xlsx', 'xls'],
    help="Upload one or more CSV/Excel files with discipline data",
    label_visibility="collapsed",
    accept_multiple_files=True
)

if uploaded_files is not None and len(uploaded_files) > 0:
    try:
        # STEP 1: Load all files
        st.markdown("### 🔍 File Detection")
        
        with st.spinner("Loading files..."):
            all_dfs = []
            file_info = []
            
            for uploaded_file in uploaded_files:
                if uploaded_file.name.endswith('.csv'):
                    df = pd.read_csv(uploaded_file)
                else:
                    df = pd.read_excel(uploaded_file)
                
                # Validate required columns
                required = ['Date', 'Grade', 'Incident_Type', 'Location', 'Time_Block', 'Response']
                missing = [col for col in required if col not in df.columns]
                
                if missing:
                    st.error(f"❌ **{uploaded_file.name}**: Missing required columns: {', '.join(missing)}")
                    st.stop()
                
                # Convert Date to datetime
                df['Date'] = pd.to_datetime(df['Date'])
                
                all_dfs.append(df)
                file_info.append({
                    'name': uploaded_file.name,
                    'rows': len(df),
                    'has_campus': 'Campus' in df.columns
                })
        
        # STEP 2: Detection Logic
        has_campus_column = any(info['has_campus'] for info in file_info)
        
        if len(uploaded_files) == 1:
            # Single file mode
            mode = "SINGLE-FILE"
            df = all_dfs[0]
            campus_identifier = campus_name
            
        elif has_campus_column:
            # Check unique campuses across all files
            all_campus_values = set()
            for df_temp in all_dfs:
                if 'Campus' in df_temp.columns:
                    all_campus_values.update(df_temp['Campus'].unique())
            
            if len(all_campus_values) == 1:
                mode = "SPLIT-CAMPUS"
                df = pd.concat(all_dfs, ignore_index=True)
                campus_identifier = list(all_campus_values)[0]
            else:
                mode = "MULTI-CAMPUS"
                df = pd.concat(all_dfs, ignore_index=True)
                campus_identifier = "Multiple Campuses"
                
        else:
            # No Campus column, assume split-campus
            mode = "SPLIT-CAMPUS"
            df = pd.concat(all_dfs, ignore_index=True)
            campus_identifier = campus_name
        
        # STEP 3: Display detection results
        if mode == "SINGLE-FILE":
            st.success(f"✅ **SINGLE-FILE MODE**: {len(df)} incidents loaded")
            
        elif mode == "SPLIT-CAMPUS":
            st.markdown(f"""
            <div class="mode-box">
                <h4>🔗 SPLIT-CAMPUS MODE DETECTED</h4>
                <p><strong>Detection:</strong> All files represent the same campus ({campus_identifier})</p>
                <p><strong>Action:</strong> Files automatically consolidated into single dataset</p>
                <p><strong>Files processed:</strong> {len(uploaded_files)}</p>
                <p><strong>Total incidents:</strong> {len(df):,}</p>
            </div>
            """, unsafe_allow_html=True)
            
        elif mode == "MULTI-CAMPUS":
            st.markdown(f"""
            <div class="mode-box">
                <h4>🏫 MULTI-CAMPUS MODE DETECTED</h4>
                <p><strong>Detection:</strong> Files contain different campus identifiers</p>
                <p><strong>Campuses found:</strong> {', '.join(sorted(all_campus_values))}</p>
                <p><strong>Files processed:</strong> {len(uploaded_files)}</p>
                <p><strong>Total incidents:</strong> {len(df):,}</p>
            </div>
            """, unsafe_allow_html=True)
        
        # Show file breakdown
        with st.expander("📂 File Details", expanded=False):
            for info in file_info:
                st.markdown(f"- **{info['name']}**: {info['rows']} rows, Campus column: {'Yes' if info['has_campus'] else 'No'}")
        
        # Show data preview
        with st.expander("📋 Preview Consolidated Data (first 10 rows)", expanded=False):
            st.dataframe(df.head(10), use_container_width=True)
        
        # Validate period name is provided
        if not period_name or period_name.strip() == "":
            st.warning("⚠️ Please enter a Period Name above before generating reports")
            st.stop()
        
        # Generate reports button
        st.markdown("<br>", unsafe_allow_html=True)
        
        if st.button("🚀 Generate Reports", type="primary", use_container_width=True):
            
            # MULTI-CAMPUS MODE: Generate per-campus reports
            if mode == "MULTI-CAMPUS":
                with st.spinner("Analyzing district data across multiple campuses..."):
                    
                    # Apply TEA mapping to full dataset
                    if STATE_MODE == "TEXAS_TEA":
                        df = apply_tea_mapping(df)
                    
                    # Store campus-level results
                    campus_results = {}
                    
                    # Process each campus
                    for campus in sorted(all_campus_values):
                        df_campus = df[df['Campus'] == campus].copy()
                        
                        # Calculate stats
                        stats = calculate_school_brief_stats(df_campus)
                        
                        # Determine posture
                        if STATE_MODE == "TEXAS_TEA":
                            posture, system_state = determine_posture_texas(stats)
                        else:
                            from discipline_analyzer import determine_posture_default
                            posture, system_state = determine_posture_default(stats)
                        
                        # Calculate impact
                        impact = calculate_instructional_impact(df_campus)
                        
                        # Generate reports
                        brief = generate_school_brief(
                            df_campus, 
                            campus_name=campus,
                        )
                        if STATE_MODE == "TEXAS_TEA":
                            tea_stats = calculate_district_tea_stats(df_campus)
                            tea_report = generate_district_tea_report(
                                df_campus,
                                campus_name=campus,
                            )
                        else:
                            tea_report = None
                        
                        campus_results[campus] = {
                            'df': df_campus,
                            'stats': stats,
                            'posture': posture,
                            'system_state': system_state,
                            'impact': impact,
                            'brief': brief,
                            'tea_report': tea_report
                        }
            
            # SINGLE-CAMPUS OR SPLIT-CAMPUS MODE: Generate one consolidated report
            else:
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
                    
                    # Generate reports with period information
                    school_brief = generate_school_brief(
                        df, 
                        campus_name=campus_identifier,
                    )
                    if STATE_MODE == "TEXAS_TEA":
                        tea_stats = calculate_district_tea_stats(df)
                        district_report = generate_district_tea_report(
                            df,
                            campus_name=f"District (All Campuses) - {campus_identifier}",
                        )
            
            # Success message
                st.markdown("<br>", unsafe_allow_html=True)
                st.success("✅ **Analysis Complete!**")
            
            # MULTI-CAMPUS DISPLAY
            if mode == "MULTI-CAMPUS":
                st.info(f"📅 **{reporting_period} Report:** {period_name} | **Mode:** MULTI-CAMPUS | **Campuses:** {len(campus_results)}")
                
                # District Summary
                st.markdown("### 🏫 District Summary")
                # Create tabs: District Summary + Individual Campuses
                all_tab_names = ["🏫 District Summary"] + sorted(campus_results.keys())
                all_tabs = st.tabs(all_tab_names)
                
                # ==========================================
                # TAB 0: DISTRICT SUMMARY
                # ==========================================
                with all_tabs[0]:
                    st.markdown("### District Overview")
                    
                    # Create summary table
                    summary_data = []
                    for campus_name, result in sorted(campus_results.items()):
                        summary_data.append({
                            'Campus': campus_name,
                            'Posture': result['posture'],
                            'Incidents': result['stats']['total_incidents'],
                            'Removal Rate': f"{result['stats']['removal_pct']:.1f}%",
                            'OSS Rate': f"{result['stats']['OSS_pct']:.1f}%"
                        })
                    
                    summary_df = pd.DataFrame(summary_data)
                    st.dataframe(summary_df, use_container_width=True, hide_index=True)
                    
                    # Watchlist
                    st.markdown("### ⚠️ District Watchlist")
                    watchlist_campuses = [
                        campus for campus, result in campus_results.items()
                        if result['posture'] in ['ESCALATE', 'INTERVENE']
                    ]
                    
                    if watchlist_campuses:
                        for campus in sorted(watchlist_campuses):
                            result = campus_results[campus]
                            st.warning(f"**{campus}**: {result['posture']} — {result['stats']['removal_pct']:.1f}% removal rate")
                    else:
                       st.success("No campuses requiring immediate attention")
                    
                # District TEA Report (formatted)
                if len(campus_results) > 1:
                    st.markdown("---")
                    st.markdown("### 📋 District TEA Compliance Report")
                    
                    district_df = pd.concat(
                        [result["df"] for result in campus_results.values()],
                        ignore_index=True
                    )
                    # Generate district report (ONCE, not twice)
                    district_report_text = generate_district_consolidated_report(
                        campus_results,
                        district_name="District (All Campuses)"
                    )
                    
                    # Format the report with same styling as campus briefs
                    lines = district_report_text.split('\n')
                    section_content = []
                    
                    for line in lines:
                        # Skip separator lines
                        if '═' in line or '─' in line or 'END OF' in line:
                            continue
                            
                        # Section headers (## style)
                        if line.strip().startswith('##'):
                            if section_content:
                                st.markdown(
                                    '<div style="background-color: #f8fafc; padding: 1.5rem; border-radius: 0.5rem; margin-bottom: 1rem; border-left: 4px solid #3b82f6;">' + 
                                    '<br>'.join(section_content) + 
                                    '</div>', 
                                    unsafe_allow_html=True
                                )
                                section_content = []
                            st.markdown(f"#### {line.replace('##', '').strip()}")
                            
                        # Content lines
                        elif line.strip():
                            # Bold metadata lines
                            if line.startswith('**') or ':' in line:
                                section_content.append(f"<strong>{line.replace('**', '')}</strong>")
                            else:
                                section_content.append(line.replace('  ', '&nbsp;&nbsp;'))
                    
                    # Flush final section (OUTSIDE the loop)
                    if section_content:
                        st.markdown(
                            '<div style="background-color: #f8fafc; padding: 1.5rem; border-radius: 0.5rem; margin-bottom: 1rem; border-left: 4px solid #3b82f6;">' + 
                            '<br>'.join(section_content) + 
                            '</div>', 
                            unsafe_allow_html=True
                        )
                    
                    # Download button (OUTSIDE the loop, with unique key)
                    st.download_button(
                        label="⬇️ Download District Report (TXT)",
                        data=district_report_text,
                        file_name="district_consolidated_report.txt",
                        mime="text/plain",
                        key="district_tea_report_download"
                    )
                    # PDF Download button
                    district_pdf = generate_district_consolidated_report_pdf(
                        district_report_text,
                        period_name
                    )
                    st.download_button(
                        label="⬇️ Download District Report (PDF)",
                        data=district_pdf,
                        file_name="district_consolidated_report.pdf",
                        mime="application/pdf",
                        key="district_consolidated_pdf_download"
                    )
                
                # ==========================================
                # TABS 1+: INDIVIDUAL CAMPUSES
                # ==========================================
                for idx, campus_name in enumerate(sorted(campus_results.keys())):
                    with all_tabs[idx + 1]:  # +1 because district is tab 0
                        result = campus_results[campus_name]
                    
                        # Campus metrics
                        col1, col2, col3 = st.columns(3)
                        with col1:
                            st.metric("Decision Posture", result['posture'])
                        with col2:
                            st.metric("Total Incidents", f"{result['stats']['total_incidents']:,}")
                        with col3:
                            removal_pct = result['stats']['ISS_pct'] + result['stats']['OSS_pct']
                            if STATE_MODE == "TEXAS_TEA":
                                removal_pct += result['stats']['DAEP_pct'] + result['stats']['JJAEP_pct']
                            st.metric("Removal Rate", f"{removal_pct:.1f}%")
                        # Reports sub-tabs
                        sub_tab1, sub_tab2 = st.tabs(["📄 School Brief", "📋 TEA Report"])
                        
                        with sub_tab1:
                            st.markdown(f"### 📄 {campus_name} — School Brief")
                            
                            # Display formatted report (same as before)
                            lines = result['brief'].split('\n')
                            section_content = []
                            
                            for line in lines:
                                if '═' in line or '─' in line:
                                    continue
                                if line.strip() and line.strip().isupper() and len(line.strip()) > 10:
                                    if section_content:
                                        st.markdown('<div style="background-color: white; padding: 1.5rem; border-radius: 0.5rem; margin-bottom: 1rem; border-left: 4px solid #3b82f6;">' + '<br>'.join(section_content) + '</div>', unsafe_allow_html=True)
                                        section_content = []
                                    st.markdown(f"#### {line.strip()}")
                                elif line.strip():
                                    if 'Decision Posture:' in line or 'Overall System State:' in line:
                                        parts = line.split(':')
                                        if len(parts) == 2:
                                            st.markdown(f"**{parts[0]}:** <span style='color: #1e3a8a; font-weight: 700; font-size: 1.1rem;'>{parts[1]}</span>", unsafe_allow_html=True)
                                    elif line.startswith('Total Incidents:') or 'minutes' in line.lower() or 'days' in line.lower():
                                        st.markdown(f"**{line}**")
                                    else:
                                        section_content.append(line.replace('  ', '&nbsp;&nbsp;'))
                            
                            if section_content:
                                st.markdown('<div style="background-color: white; padding: 1.5rem; border-radius: 0.5rem; margin-bottom: 1rem; border-left: 4px solid #3b82f6;">' + '<br>'.join(section_content) + '</div>', unsafe_allow_html=True)
                            
                            # Download button
                            st.markdown("<br>", unsafe_allow_html=True)
                            pdf_buffer = generate_school_brief_pdf(
                                result['brief'],
                                uploaded_filename=campus_name,
                                period_name=period_name,)
                            clean_period = period_name.replace(' ', '_').replace(',', '').replace('/', '-')
                            clean_campus = campus_name.replace(' ', '_')
                            filename = f"school_brief_{clean_campus}_{clean_period}.pdf"
                            st.download_button(
                                label=f"📥 Download {campus_name} Brief (PDF)",
                                data=pdf_buffer,
                                file_name=filename,
                                mime="application/pdf",
                                use_container_width=True,
                                key=f"campus_brief_{campus_name.replace(' ', '_')}_download"
                            )
                        
                        with sub_tab2:
                            if STATE_MODE == "TEXAS_TEA" and result['tea_report']:
                                st.markdown(f"### 📋 {campus_name} — TEA Report")
                                
                                # Display TEA report (same logic as before)
                                lines = result['tea_report'].split('\n')
                                section_content = []
                                
                                for line in lines:
                                    if '═' in line or '─' in line:
                                        continue
                                    if line.strip() and line.strip().isupper() and len(line.strip()) > 10:
                                        if section_content:
                                            st.markdown('<div style="background-color: white; padding: 1.5rem; border-radius: 0.5rem; margin-bottom: 1rem; border-left: 4px solid #10b981;">' + '<br>'.join(section_content) + '</div>', unsafe_allow_html=True)
                                            section_content = []
                                        st.markdown(f"#### {line.strip()}")
                                    elif line.strip():
                                        if 'Code ' in line or '%' in line or 'Total TEA Actions' in line:
                                            st.markdown(f"**{line}**")
                                        else:
                                            section_content.append(line.replace('  ', '&nbsp;&nbsp;'))
                                
                                if section_content:
                                    st.markdown('<div style="background-color: white; padding: 1.5rem; border-radius: 0.5rem; margin-bottom: 1rem; border-left: 4px solid #10b981;">' + '<br>'.join(section_content) + '</div>', unsafe_allow_html=True)
                                
                                # Download button
                                st.markdown("<br>", unsafe_allow_html=True)
                                pdf_buffer = generate_district_tea_pdf(result['tea_report'], campus_name, period_name)
                                clean_period = period_name.replace(' ', '_').replace(',', '').replace('/', '-')
                                clean_campus = campus_name.replace(' ', '_')
                                filename = f"district_tea_report_{clean_campus}_{clean_period}.pdf"
                                st.download_button(
                                    label=f"📥 Download {campus_name} TEA Report (PDF)",
                                    data=pdf_buffer,
                                    file_name=filename,
                                    mime="application/pdf",
                                    use_container_width=True,
                                    key=f"campus_tea_{campus_name.replace(' ', '_')}_download"
                                )
                            else:
                                st.info("District TEA Report only available in Texas mode")
            
            # SINGLE-CAMPUS OR SPLIT-CAMPUS DISPLAY
            else:
                # Show mode and period info
                st.info(f"📅 **{reporting_period} Report:** {period_name} | **Mode:** {mode}")
                
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
                    
                    # Download PDF button with period-based filename
                    st.markdown("<br>", unsafe_allow_html=True)
                    pdf_buffer = generate_school_brief_pdf(school_brief, uploaded_files[0].name, period_name)
                    
                    # Clean period name for filename
                    clean_period = period_name.replace(' ', '_').replace(',', '').replace('/', '-')
                    filename = f"school_brief_{clean_period}.pdf"
                    
                    st.download_button(
                        label="📥 Download School Brief (PDF)",
                        data=pdf_buffer,
                        file_name=filename,
                        mime="application/pdf",
                        use_container_width=True,
                        key=f"school_brief_{campus_name.replace(' ', '_')}_download"
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
                        
                        # Download PDF button with period-based filename
                        st.markdown("<br>", unsafe_allow_html=True)
                        pdf_buffer = generate_district_tea_pdf(district_report, uploaded_files[0].name, period_name)
                        
                        # Clean period name for filename
                        clean_period = period_name.replace(' ', '_').replace(',', '').replace('/', '-')
                        filename = f"district_tea_report_{clean_period}.pdf"
                        
                        st.download_button(
                            label="📥 Download District Report (PDF)",
                            data=pdf_buffer,
                            file_name=filename,
                            mime="application/pdf",
                            use_container_width=True,
                            key="district_report_pdf_download"
                        )
                    else:
                        st.info("District TEA Report only available in Texas mode")
        
    except Exception as e:
        st.error(f"❌ Error processing file: {str(e)}")
        with st.expander("See error details"):
            st.exception(e)

else:
    # Show info when no file uploaded
    st.info("👆 Configure settings and upload your discipline data file(s) to get started")
    
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
