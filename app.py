import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import re

# Page config
st.set_page_config(
    page_title="Shift Leader Dashboard",
    page_icon="📋",
    layout="wide"
)

# Google Sheet ID
SHEET_ID = "1dlEsHDCB5doCrnli2QD3tjNdcMKfqxHchekYrEa4_uc"

@st.cache_data(ttl=60)
def load_data():
    url = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv"
    df = pd.read_csv(url)
    
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
        return ('no', None)
    elif value.upper() == 'N/A' or value.upper() == 'NA':
        return ('na', None)
    else:
        # Might be a staff name directly or other value
        return ('completed', value) if value else ('missing', None)

def get_status_icon(status):
    """Return emoji icon for status"""
    icons = {
        'completed': '✅',
        'no': '❌',
        'na': '➖',
        'missing': '⚠️'
    }
    return icons.get(status, '❓')

# Main app
st.title("📋 Shift Leader Dashboard")
st.caption("Children's Shelter - Daily Checklist Tracking")

# Load data
try:
    df = load_data()
except Exception as e:
    st.error(f"Error loading data: {e}")
    st.info("Make sure the Google Sheet is set to 'Anyone with the link can view'")
    st.stop()

if len(df) == 0:
    st.warning("No submissions yet. Data will appear here once shift leaders submit checklists.")
    st.stop()

# Tabs for different views
tab1, tab2, tab3 = st.tabs(["🔄 Shift Handoff", "📊 Summary", "📈 Trends"])

# =============================================================================
# TAB 1: SHIFT HANDOFF VIEW
# =============================================================================
with tab1:
    st.subheader("Last Completed Shift")
    
    # Get the most recent submission
    last_shift = df.iloc[0]
    
    # Header card
    shift_leader = f"{last_shift.get('Shift Leader Name - First Name', '')} {last_shift.get('Shift Leader Name - Last Name', '')}".strip()
    shift_date = last_shift['Submission Date'].strftime('%B %d, %Y at %I:%M %p') if pd.notna(last_shift['Submission Date']) else 'Unknown'
    shift_type = last_shift.get('Shift', 'Unknown')
    reviewed_prior = last_shift.get('Did You Review the Last Shift Checklist at the Beginning of your Shift?', 'Unknown')
    
    st.markdown(f"**{shift_type} Shift** — {shift_date}")
    st.markdown(f"Shift Leader: **{shift_leader}**")
    st.markdown(f"Reviewed prior checklist: **{reviewed_prior}**")
    
    st.divider()
    
    # Task sections
    def display_task_section(title, tasks, row):
        with st.expander(title, expanded=True):
            for task in tasks:
                if task in row:
                    status, staff = parse_task_status(row[task])
                    icon = get_status_icon(status)
                    
                    col1, col2 = st.columns([4, 1])
                    with col1:
                        st.markdown(f"{icon} {task}")
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
# TAB 2: SUMMARY
# =============================================================================
with tab2:
    st.subheader("Overview")
    
    # Today's shifts
    today = datetime.now().date()
    today_df = df[df['Submission Date'].dt.date == today] if len(df) > 0 else pd.DataFrame()
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.metric("Total Submissions", len(df))
    
    with col2:
        st.metric("Today's Submissions", len(today_df))
    
    st.divider()
    
    # Shift type breakdown
    st.subheader("Submissions by Shift Type")
    
    if len(df) > 0:
        shift_stats = []
        for shift_type in ['AM', 'PM', 'Overnight']:
            shift_df = df[df['Shift'] == shift_type]
            if len(shift_df) > 0:
                shift_stats.append({
                    'Shift': shift_type,
                    'Total Submissions': len(shift_df)
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
        
        display_df = recent[['Date', 'Shift Leader', 'Shift']]
        st.dataframe(display_df, hide_index=True, use_container_width=True)

# =============================================================================
# TAB 3: TRENDS
# =============================================================================
with tab3:
    st.subheader("Trends")
    
    if len(df) < 2:
        st.info("Need more submissions to show trends. Data will appear as more checklists are submitted.")
        st.stop()
    
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
            col1, col2 = st.columns(2)
            with col1:
                st.metric("Reviewed Prior Checklist", f"{reviewed_yes} of {total} shifts")
            with col2:
                if reviewed_no > 0:
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
