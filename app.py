import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime, timedelta
import re

# Page config
st.set_page_config(
    page_title="Shift Leader Dashboard",
    page_icon="📋",
    layout="wide"
)

# Google Sheets connection
@st.cache_resource
def get_google_client():
    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]
    creds = Credentials.from_service_account_info(
        st.secrets["gcp_service_account"],
        scopes=scopes
    )
    return gspread.authorize(creds)

@st.cache_data(ttl=60)
def load_data():
    client = get_google_client()
    sheet = client.open_by_key("1dlEsHDCB5doCrnli2QD3tjNdcMKfqxHchekYrEa4_uc")
    worksheet = sheet.sheet1
    data = worksheet.get_all_records()
    df = pd.DataFrame(data)
    
    if len(df) > 0 and 'Submission Date' in df.columns:
        df['Submission Date'] = pd.to_datetime(df['Submission Date'])
        df = df.sort_values('Submission Date', ascending=False)
    
    return df

# Task categories and their columns
GENERAL_TASKS = [
    'Meds Given',
    'Unannounced Rounds Every 2 Hours in Apricot',
    'Conduct Fire Drill If Scheduled',
    'Youth Taken to Appointments (Logbook / Whiteboard)',
    'Shift Report Completed in Apricot',
    'Informational or Behavioral Notes Submitted',
    'Verbal Review to Next Shift'
]

KITCHEN_TASKS = [
    'Prepare Breakfast',
    'Prepare Lunch',
    'Prepare DInner',
    'Clean Kitchen',
    'Defrost Food',
    'Date Food',
    'Dispose of Any Expired Food',
    'Fill Out Refrigerator Temperature Log',
    'Take Out Trash'
]

FACILITY_TASKS = [
    'Clean and Tidy Common Area/Dining Room',
    'Clean and Tidy 2nd Floor Lounge',
    'Check & Restock House Paper Products / Soap, etc.',
    'Bring In and Put Away Deliveries',
    'All Youth Chores Completed',
    'Tidy Youth Worker Office Area',
    'Seasonal Snow Clean Up Assistance',
    'Seasonal Water Plants and Clean Up Outside Area'
]

CHECKBOX_TASKS = [
    'All Keys Available',
    'Dishwasher (check all that apply)',
    'Laundry (Clothes, Bedding/Towels, Kitchen Clothes) Check All That Apply'
]

ALL_TASKS = GENERAL_TASKS + KITCHEN_TASKS + FACILITY_TASKS

def parse_task_status(value):
    """Parse task value and return (status, staff_name)"""
    if pd.isna(value) or value == '' or value is None:
        return ('missing', None)
    
    value = str(value).strip()
    
    if value.upper().startswith('YES'):
        # Extract staff name after "YES - "
        match = re.match(r'YES\s*-?\s*(.+)', value, re.IGNORECASE)
        staff = match.group(1).strip() if match and match.group(1).strip() else None
        return ('completed', staff)
    elif value.upper().startswith('NO'):
        return ('missed', None)
    elif value.upper() == 'N/A' or value.upper() == 'NA':
        return ('na', None)
    else:
        # Might be a staff name directly or other value
        return ('completed', value) if value else ('missing', None)

def get_status_icon(status):
    """Return emoji icon for status"""
    icons = {
        'completed': '✅',
        'missed': '❌',
        'na': '➖',
        'missing': '⚠️'
    }
    return icons.get(status, '❓')

def get_status_color(status):
    """Return color for status"""
    colors = {
        'completed': '#10b981',
        'missed': '#ef4444',
        'na': '#9ca3af',
        'missing': '#f59e0b'
    }
    return colors.get(status, '#6b7280')

def calculate_completion_stats(row, task_list):
    """Calculate completion stats for a list of tasks"""
    completed = 0
    missed = 0
    na = 0
    missing = 0
    
    for task in task_list:
        if task in row:
            status, _ = parse_task_status(row[task])
            if status == 'completed':
                completed += 1
            elif status == 'missed':
                missed += 1
            elif status == 'na':
                na += 1
            else:
                missing += 1
    
    applicable = completed + missed + missing
    rate = (completed / applicable * 100) if applicable > 0 else 0
    
    return {
        'completed': completed,
        'missed': missed,
        'na': na,
        'missing': missing,
        'applicable': applicable,
        'rate': rate
    }

# Main app
st.title("📋 Shift Leader Dashboard")
st.caption("Children's Shelter - Daily Checklist Tracking")

# Load data
try:
    df = load_data()
except Exception as e:
    st.error(f"Error connecting to Google Sheets: {e}")
    st.info("Make sure your secrets.toml file is configured with Google service account credentials.")
    st.stop()

if len(df) == 0:
    st.warning("No submissions yet. Data will appear here once shift leaders submit checklists.")
    st.stop()

# Tabs for different views
tab1, tab2, tab3 = st.tabs(["🔄 Shift Handoff", "📊 Completion Summary", "📈 Trends & Issues"])

# =============================================================================
# TAB 1: SHIFT HANDOFF VIEW
# =============================================================================
with tab1:
    st.subheader("Last Completed Shift")
    
    # Get the most recent submission
    last_shift = df.iloc[0]
    
    # Header card
    col1, col2 = st.columns([3, 1])
    
    with col1:
        shift_leader = f"{last_shift.get('Shift Leader Name - First Name', '')} {last_shift.get('Shift Leader Name - Last Name', '')}".strip()
        shift_date = last_shift['Submission Date'].strftime('%B %d, %Y at %I:%M %p') if pd.notna(last_shift['Submission Date']) else 'Unknown'
        shift_type = last_shift.get('Shift', 'Unknown')
        reviewed_prior = last_shift.get('Did You Review the Last Shift Checklist at the Beginning of your Shift?', 'Unknown')
        
        st.markdown(f"**{shift_type} Shift** — {shift_date}")
        st.markdown(f"Shift Leader: **{shift_leader}**")
        st.markdown(f"Reviewed prior checklist: **{reviewed_prior}**")
    
    with col2:
        stats = calculate_completion_stats(last_shift, ALL_TASKS)
        rate = stats['rate']
        color = '#10b981' if rate >= 90 else '#f59e0b' if rate >= 75 else '#ef4444'
        st.markdown(f"<h1 style='text-align: right; color: {color};'>{rate:.0f}%</h1>", unsafe_allow_html=True)
        st.markdown(f"<p style='text-align: right;'>{stats['completed']}/{stats['applicable']} tasks</p>", unsafe_allow_html=True)
    
    # Show missed tasks alert
    missed_tasks = []
    for task in ALL_TASKS:
        if task in last_shift:
            status, _ = parse_task_status(last_shift[task])
            if status == 'missed':
                missed_tasks.append(task)
    
    if missed_tasks:
        st.error(f"⚠️ **{len(missed_tasks)} task(s) incomplete:** {', '.join(missed_tasks)}")
    
    st.divider()
    
    # Task sections
    def display_task_section(title, tasks, row):
        with st.expander(title, expanded=True):
            section_stats = calculate_completion_stats(row, tasks)
            st.caption(f"{section_stats['completed']}/{section_stats['applicable']} completed")
            
            for task in tasks:
                if task in row:
                    status, staff = parse_task_status(row[task])
                    icon = get_status_icon(status)
                    color = get_status_color(status)
                    
                    col1, col2 = st.columns([4, 1])
                    with col1:
                        style = f"color: {color}; font-weight: bold;" if status == 'missed' else ""
                        st.markdown(f"{icon} <span style='{style}'>{task}</span>", unsafe_allow_html=True)
                    with col2:
                        st.caption(staff if staff else "—")
    
    col1, col2 = st.columns(2)
    
    with col1:
        display_task_section("General Duties", GENERAL_TASKS, last_shift)
        display_task_section("Kitchen", KITCHEN_TASKS, last_shift)
    
    with col2:
        display_task_section("Facility", FACILITY_TASKS, last_shift)
        
        # Keys section
        with st.expander("Keys & Equipment", expanded=True):
            keys = last_shift.get('All Keys Available', '')
            keys_staff = last_shift.get('Staff Reviewed Keys', '')
            st.markdown(f"**Keys Checked:** {keys if keys else 'Not recorded'}")
            st.caption(f"Staff: {keys_staff if keys_staff else '—'}")
            
            dishwasher = last_shift.get('Dishwasher (check all that apply)', '')
            dishwasher_staff = last_shift.get('Staff Managed Dishwasher', '')
            st.markdown(f"**Dishwasher:** {dishwasher.replace(chr(10), ', ') if dishwasher else 'Not recorded'}")
            st.caption(f"Staff: {dishwasher_staff if dishwasher_staff else '—'}")
            
            laundry = last_shift.get('Laundry (Clothes, Bedding/Towels, Kitchen Clothes) Check All That Apply', '')
            laundry_staff = last_shift.get('Staff Managed Laundry', '')
            st.markdown(f"**Laundry:** {laundry.replace(chr(10), ', ') if laundry else 'Not recorded'}")
            st.caption(f"Staff: {laundry_staff if laundry_staff else '—'}")
    
    # Narrative section
    narrative = last_shift.get('Narrative to Include Shift Issues/Comments and Info for Next Shift', '')
    if narrative:
        st.divider()
        st.subheader("📝 Shift Notes")
        st.info(narrative)

# =============================================================================
# TAB 2: COMPLETION SUMMARY
# =============================================================================
with tab2:
    st.subheader("Completion Overview")
    
    # Today's shifts
    today = datetime.now().date()
    today_df = df[df['Submission Date'].dt.date == today] if len(df) > 0 else pd.DataFrame()
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("Total Submissions", len(df))
    
    with col2:
        st.metric("Today's Submissions", len(today_df))
    
    with col3:
        if len(df) > 0:
            avg_rate = df.apply(lambda row: calculate_completion_stats(row, ALL_TASKS)['rate'], axis=1).mean()
            st.metric("Avg Completion Rate", f"{avg_rate:.1f}%")
    
    st.divider()
    
    # Section completion rates (last 7 days)
    st.subheader("Section Completion (Last 7 Days)")
    
    week_ago = datetime.now() - timedelta(days=7)
    week_df = df[df['Submission Date'] >= week_ago] if len(df) > 0 else pd.DataFrame()
    
    if len(week_df) > 0:
        sections = [
            ("General Duties", GENERAL_TASKS),
            ("Kitchen", KITCHEN_TASKS),
            ("Facility", FACILITY_TASKS)
        ]
        
        for section_name, tasks in sections:
            rates = week_df.apply(lambda row: calculate_completion_stats(row, tasks)['rate'], axis=1)
            avg_rate = rates.mean()
            color = '#10b981' if avg_rate >= 90 else '#f59e0b' if avg_rate >= 75 else '#ef4444'
            
            col1, col2 = st.columns([3, 1])
            with col1:
                st.progress(avg_rate / 100)
            with col2:
                st.markdown(f"<span style='color: {color}; font-weight: bold;'>{section_name}: {avg_rate:.0f}%</span>", unsafe_allow_html=True)
    else:
        st.info("No data from the last 7 days.")
    
    st.divider()
    
    # Shift type breakdown
    st.subheader("Completion by Shift Type")
    
    if len(df) > 0:
        shift_stats = []
        for shift_type in ['AM', 'PM', 'Overnight']:
            shift_df = df[df['Shift'] == shift_type]
            if len(shift_df) > 0:
                rates = shift_df.apply(lambda row: calculate_completion_stats(row, ALL_TASKS)['rate'], axis=1)
                shift_stats.append({
                    'Shift': shift_type,
                    'Submissions': len(shift_df),
                    'Avg Completion': f"{rates.mean():.1f}%"
                })
        
        if shift_stats:
            st.dataframe(pd.DataFrame(shift_stats), hide_index=True, use_container_width=True)
    
    st.divider()
    
    # Recent submissions table
    st.subheader("Recent Submissions")
    
    if len(df) > 0:
        recent = df.head(10).copy()
        recent['Shift Leader'] = recent.apply(
            lambda r: f"{r.get('Shift Leader Name - First Name', '')} {r.get('Shift Leader Name - Last Name', '')}".strip(),
            axis=1
        )
        recent['Date'] = recent['Submission Date'].dt.strftime('%m/%d/%Y %I:%M %p')
        recent['Completion'] = recent.apply(
            lambda r: f"{calculate_completion_stats(r, ALL_TASKS)['rate']:.0f}%",
            axis=1
        )
        
        display_df = recent[['Date', 'Shift Leader', 'Shift', 'Completion']]
        st.dataframe(display_df, hide_index=True, use_container_width=True)

# =============================================================================
# TAB 3: TRENDS & ISSUES
# =============================================================================
with tab3:
    st.subheader("Trends & Issues")
    
    if len(df) < 2:
        st.info("Need more submissions to show trends. Data will appear as more checklists are submitted.")
        st.stop()
    
    # Most missed tasks
    st.subheader("Most Missed Tasks (All Time)")
    
    task_misses = {}
    for task in ALL_TASKS:
        if task in df.columns:
            misses = df[task].apply(lambda x: 1 if parse_task_status(x)[0] == 'missed' else 0).sum()
            if misses > 0:
                task_misses[task] = misses
    
    if task_misses:
        sorted_misses = sorted(task_misses.items(), key=lambda x: x[1], reverse=True)[:10]
        
        for task, count in sorted_misses:
            col1, col2 = st.columns([4, 1])
            with col1:
                max_misses = sorted_misses[0][1] if sorted_misses else 1
                st.progress(count / max_misses)
            with col2:
                st.markdown(f"**{task}**: {count}x")
    else:
        st.success("No missed tasks recorded!")
    
    st.divider()
    
    # Staff task completion
    st.subheader("Staff Task Completion")
    
    staff_counts = {}
    for task in ALL_TASKS:
        if task in df.columns:
            for _, row in df.iterrows():
                status, staff = parse_task_status(row[task])
                if status == 'completed' and staff:
                    # Clean up staff name
                    staff_clean = staff.strip()
                    if staff_clean and staff_clean.upper() not in ['YES', 'NO', 'N/A']:
                        staff_counts[staff_clean] = staff_counts.get(staff_clean, 0) + 1
    
    if staff_counts:
        sorted_staff = sorted(staff_counts.items(), key=lambda x: x[1], reverse=True)[:10]
        
        staff_df = pd.DataFrame(sorted_staff, columns=['Staff Member', 'Tasks Completed'])
        st.dataframe(staff_df, hide_index=True, use_container_width=True)
    else:
        st.info("Staff completion data will appear as more checklists are submitted.")
    
    st.divider()
    
    # Reviewed prior checklist stats
    st.subheader("Shift Handoff Compliance")
    
    reviewed_col = 'Did You Review the Last Shift Checklist at the Beginning of your Shift?'
    if reviewed_col in df.columns:
        reviewed_yes = (df[reviewed_col].str.upper() == 'YES').sum()
        reviewed_no = (df[reviewed_col].str.upper() == 'NO').sum()
        total = reviewed_yes + reviewed_no
        
        if total > 0:
            rate = reviewed_yes / total * 100
            col1, col2 = st.columns(2)
            with col1:
                st.metric("Handoff Reviews Completed", f"{rate:.0f}%", f"{reviewed_yes}/{total} shifts")
            with col2:
                if rate < 100:
                    st.warning(f"{reviewed_no} shifts did not review the prior checklist")
                else:
                    st.success("All shifts reviewing prior checklists!")

# Footer
st.divider()
st.caption("Dashboard refreshes automatically every 60 seconds. Last loaded: " + datetime.now().strftime('%I:%M %p'))

# Refresh button
if st.button("🔄 Refresh Now"):
    st.cache_data.clear()
    st.rerun()
