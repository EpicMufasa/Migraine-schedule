import streamlit as st
import pandas as pd
from datetime import datetime, time

st.title("Pharmacy Shift Scheduler")

# Month selector
year_month = st.selectbox("Select month:", ["2025-07", "2025-08"])
year, month = map(int, year_month.split('-'))
start = datetime(year, month, 1)
end = datetime(year + (month // 12), (month % 12) + 1, 1)
dates = pd.date_range(start, end, freq='B')

def parse_time_entry(val):
    s = str(val).strip().lower().replace(' ', '')
    # Handle empty
    if not s or s in ['nan']:
        return None
    # Split if contains '-'
    parts = s.split('-')
    def to_time(tstr):
        # Remove am/pm
        pm = 'pm' in tstr
        tstr = tstr.replace('am', '').replace('pm', '')
        if ':' in tstr:
            h, m = map(int, tstr.split(':'))
        else:
            if len(tstr) <= 2:
                h, m = int(tstr), 0
            else:
                h = int(tstr[:-2]); m = int(tstr[-2:])
        if pm and h < 12:
            h += 12
        return time(h, m)
    try:
        if len(parts) == 2:
            return to_time(parts[0]), to_time(parts[1])
    except:
        return None
    return None

# Pharmacist management
if 'pharmacists' not in st.session_state:
    st.session_state.pharmacists = []
new = st.text_input("Add pharmacist")
if st.button("Add") and new:
    st.session_state.pharmacists.append(new)
rem = st.selectbox("Remove pharmacist", [None] + st.session_state.pharmacists)
if st.button("Remove") and rem:
    st.session_state.pharmacists.remove(rem)

# Initialize schedule
if 'schedule' not in st.session_state:
    st.session_state.schedule = {}
for p in st.session_state.pharmacists:
    st.session_state.schedule.setdefault(p, {})

# Build DataFrame
cols = [d.strftime('%Y-%m-%d') for d in dates]
data = {}
for p in st.session_state.pharmacists:
    row = []
    for c in cols:
        rec = st.session_state.schedule[p].get(c)
        if rec:
            row.append(rec['start'].strftime('%I:%M %p') + '-' + rec['end'].strftime('%I:%M %p'))
        else:
            row.append('')
    data[p] = row
df = pd.DataFrame(data, index=cols)

# Editable
try:
    ed = st.data_editor(df, use_container_width=True)
except AttributeError:
    st.dataframe(df, use_container_width=True)
    ed = df

# Parse edits back
def normalize_schedule(df_ed):
    for date_str in df_ed.index:
        for p in df_ed.columns:
            val = df_ed.at[date_str, p]
            parsed = parse_time_entry(val)
            if parsed:
                st.session_state.schedule[p][date_str] = {'start': parsed[0], 'end': parsed[1]}
normalize_schedule(ed)

# Coverage status vertical
status = []
for d in dates:
    ds = []
    for p in st.session_state.pharmacists:
        rec = st.session_state.schedule[p].get(d.strftime('%Y-%m-%d'))
        if rec:
            ds.append((rec['start'], rec['end']))
    # rules
    if ds and min(s for s,_ in ds) <= time(7,45) and max(e for _,e in ds) >= time(17,0) and any(s<=time(12,0)<=e for s,e in ds):
        status.append({'Date': d.strftime('%b %d'), 'Status': 'OK'})
    else:
        status.append({'Date': d.strftime('%b %d'), 'Status': 'MISSING'})
st.dataframe(pd.DataFrame(status).set_index('Date').style.applymap(
    lambda v: 'background-color: lightgreen' if v=='OK' else 'background-color: lightcoral', subset=['Status']
), use_container_width=True)

# Download
if st.button("Download CSV"):
    out = pd.DataFrame({p: {d: f"{st.session_state.schedule[p][d]['start'].strftime('%H:%M')}-{st.session_state.schedule[p][d]['end'].strftime('%H:%M')}"
                              for d in cols if d in st.session_state.schedule[p]}
                       for p in st.session_state.pharmacists})
    st.download_button("Download", out.to_csv(), file_name=f"sched_{year_month}.csv")
