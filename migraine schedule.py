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
for name in st.session_state.pharmacists:
    st.subheader(name)
    cols = st.columns(len(dates))
    for i, date in enumerate(dates):
        with cols[i]:
            st.write(date.strftime("%b %d"))
            default = st.session_state.schedule[name].get(str(date), {})
            start = st.time_input("Start", value=default.get('start', time(8,0)), key=f"{name}-{date}-start")
            end = st.time_input("End", value=default.get('end', time(17,0)), key=f"{name}-{date}-end")
            st.session_state.schedule[name][str(date)] = {'start': start, 'end': end}

# 6. Validation rules
def validate_day(shifts):
    # need earliest <=7:45, latest >=17:00, someone covering 12:00
    opens = [s['start'] for s in shifts]
    closes = [s['end'] for s in shifts]
    covers_mid = any(s['start'] <= time(12,0) <= s['end'] for s in shifts)
    ok_open = min(opens) <= time(7,45)
    ok_close = max(closes) >= time(17,0)
    return ok_open and ok_close and covers_mid

# 7. Display daily status
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
