import streamlit as st
import pandas as pd
from datetime import datetime, time

# Title
st.title("Pharmacy Shift Scheduler")

# 1. Initialize month selection
month = st.selectbox("Select month:", ["2025-07", "2025-08"])
year, month_num = map(int, month.split('-'))

# 2. Generate list of weekdays for the month
start_date = datetime(year, month_num, 1)
end_date = datetime(year, month_num + 1, 1) if month_num < 12 else datetime(year + 1, 1, 1)
dates = pd.date_range(start_date, end_date, freq='D')
dates = [d for d in dates if d.weekday() < 5]

# 3. Manage pharmacist list
if 'pharmacists' not in st.session_state:
    st.session_state.pharmacists = []

new_name = st.text_input("Add pharmacist:")
if st.button("Add"):  
    if new_name and new_name not in st.session_state.pharmacists:
        st.session_state.pharmacists.append(new_name)
        st.success(f"Added {new_name}")

# Remove
remove = st.selectbox("Remove pharmacist:", [None] + st.session_state.pharmacists)
if st.button("Remove") and remove:
    st.session_state.pharmacists.remove(remove)
    st.success(f"Removed {remove}")

# 4. Initialize schedule in session_state
if 'schedule' not in st.session_state:
    # dict: {name: {date: (start, end)}}
    st.session_state.schedule = {name: {} for name in st.session_state.pharmacists}

# keep schedule table updated when pharmacists change
for name in st.session_state.pharmacists:
    if name not in st.session_state.schedule:
        st.session_state.schedule[name] = {}
for name in list(st.session_state.schedule.keys()):
    if name not in st.session_state.pharmacists:
        del st.session_state.schedule[name]

# 5. Input shifts
st.header("Enter shifts")

# Build editable schedule DataFrame
pharmacists = st.session_state.pharmacists
cols = [d.strftime('%Y-%m-%d') for d in dates]
# Initialize DataFrame with existing or default shift strings
data = {}
for d in cols:
    data[d] = []
    for name in pharmacists:
        rec = st.session_state.schedule.get(name, {}).get(d, {})
        start = rec.get('start', time(8,0)).strftime('%H:%M')
        end = rec.get('end', time(17,0)).strftime('%H:%M')
        data[d].append(f"{start}-{end}")

df = pd.DataFrame(data, index=pharmacists)

# Editable grid (requires Streamlit >=1.21)
try:
    edited = st.data_editor(df, use_container_width=True)
except AttributeError:
    st.warning("Your Streamlit version does not support data_editor. Displaying read-only table.")
    st.dataframe(df, use_container_width=True)
    edited = df

# Parse back into session_state.schedule into session_state.schedule
for name in edited.index:
    for date_str in edited.columns:
        val = edited.at[name, date_str]
        try:
            start_str, end_str = val.split('-')
            start = datetime.strptime(start_str, '%H:%M').time()
            end = datetime.strptime(end_str, '%H:%M').time()
            st.session_state.schedule.setdefault(name, {})[date_str] = {'start': start, 'end': end}
        except ValueError:
            # skip invalid entries
            pass

# 6. Validation rules Validation rules
def validate_day(shifts):
    """
    Check that for a given day's shifts:
      - There's an opener (earliest start ≤ 7:45 AM)
      - There's a closer (latest end ≥ 5:00 PM)
      - At least one shift covers noon (12:00 PM)
    """
    # Extract valid time entries
    opens = []
    closes = []
    covers_mid = False
    for s in shifts:
        start = s.get('start')
        end = s.get('end')
        if isinstance(start, time) and isinstance(end, time):
            opens.append(start)
            closes.append(end)
            if start <= time(12, 0) <= end:
                covers_mid = True
    # If no valid entries, fail
    if not opens or not closes:
        return False
    # Check opener and closer
    ok_open = min(opens) <= time(7, 45)
    ok_close = max(closes) >= time(17, 0)
    return ok_open and ok_close and covers_mid

# 7. Display daily status Display daily status
st.header("Coverage Status")
status_cols = st.columns(len(dates))
for i, date in enumerate(dates):
    with status_cols[i]:
        day_shifts = [st.session_state.schedule[name][str(date)] for name in st.session_state.pharmacists]
        valid = validate_day(day_shifts)
        color = "green" if valid else "red"
        st.markdown(f"<div style='background-color:{color};padding:10px;border-radius:5px;text-align:center;'>" + \
                    f"{date.strftime('%b %d')}<br>{'OK' if valid else 'MISSING'}" +
                    "</div>", unsafe_allow_html=True)

# 8. Download schedule
if st.button("Download CSV"):
    df = pd.DataFrame({name: {d.strftime('%Y-%m-%d'): f"{st.session_state.schedule[name][str(d)]['start'].strftime('%H:%M')}-{st.session_state.schedule[name][str(d)]['end'].strftime('%H:%M')}" for d in dates}
                        for name in st.session_state.pharmacists}).T
    csv = df.to_csv()
    st.download_button("Download", data=csv, file_name=f"schedule_{month}.csv")
