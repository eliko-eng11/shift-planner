
import streamlit as st
import pandas as pd
import numpy as np
from scipy.optimize import linear_sum_assignment

st.set_page_config(page_title="מערכת שיבוץ משמרות", layout="wide")

st.title("📅 מערכת שיבוץ משמרות לעובדים")

# --- קלט --- #
num_workers = st.number_input("כמה עובדים יש?", min_value=1, max_value=100, step=1)

ordered_days = ['ראשון', 'שני', 'שלישי', 'רביעי', 'חמישי', 'שישי', 'שבת']
full_shifts = ['משמרת בוקר', 'משמרת אחה״צ', 'משמרת לילה']
basic_days = ordered_days[:5]

work_friday = st.checkbox("עובדים ביום שישי?")
work_saturday = st.checkbox("עובדים ביום שבת?")

shifts_per_day_basic = st.slider("כמה משמרות ביום רגיל (א׳–ה׳)?", 1, 3, 2)
selected_shifts_basic = full_shifts[:shifts_per_day_basic]

shifts_per_day_friday = 0
shifts_per_day_saturday = 0
selected_shifts_friday = []
selected_shifts_saturday = []

if work_friday:
    shifts_per_day_friday = st.slider("כמה משמרות ביום שישי?", 1, 3, 1)
    selected_shifts_friday = full_shifts[:shifts_per_day_friday]

if work_saturday:
    shifts_per_day_saturday = st.slider("כמה משמרות ביום שבת?", 1, 3, 1)
    selected_shifts_saturday = full_shifts[:shifts_per_day_saturday]

active_days = basic_days.copy()
if work_friday:
    active_days.append('שישי')
if work_saturday:
    active_days.append('שבת')

workers = []
st.subheader("שמות העובדים")
for i in range(num_workers):
    name = st.text_input(f"שם עובד #{i+1}", key=f"worker_{i}")
    if name:
        workers.append(name)

st.subheader("דרישת עובדים בכל משמרת")
required_workers = {}
shift_slots = []
for d in active_days:
    if d in basic_days:
        shifts_today = selected_shifts_basic
    elif d == 'שישי':
        shifts_today = selected_shifts_friday
    else:
        shifts_today = selected_shifts_saturday

    for s in shifts_today:
        req = st.number_input(f"{d} {s} - כמה עובדים צריך?", min_value=0, max_value=20, step=1, key=f"{d}_{s}")
        required_workers[(d, s)] = req
        for i in range(req):
            shift_slots.append((d, s, i))

preferences = {}
if len(workers) > 0:
    st.subheader("העדפות עובדים")
    for w in workers:
        for d in active_days:
            if d in basic_days:
                shifts_today = selected_shifts_basic
            elif d == 'שישי':
                shifts_today = selected_shifts_friday
            else:
                shifts_today = selected_shifts_saturday

            for s in shifts_today:
                val = st.slider(f"{w} - {d} {s}", -1, 3, 2, key=f"{w}_{d}_{s}")
                preferences[(w, d, s)] = val

if st.button("בצע שיבוץ") and len(workers) > 0:
    # שיבוץ
    worker_copies = []
    worker_origin = []
    for w in workers:
        for d in active_days:
            if d in basic_days:
                shifts_today = selected_shifts_basic
            elif d == 'שישי':
                shifts_today = selected_shifts_friday
            else:
                shifts_today = selected_shifts_saturday

            for s in shifts_today:
                if preferences[(w, d, s)] >= 0:
                    worker_copies.append((w, d, s))
                    worker_origin.append(w)

    cost_matrix = []
    for wc in worker_copies:
        w, d, s = wc
        row = []
        for sd, ss, _ in shift_slots:
            if (d, s) == (sd, ss):
                row.append(4 - preferences[(w, d, s)])
            else:
                row.append(1e6)
        cost_matrix.append(row)

    cost_matrix = np.array(cost_matrix)
    row_ind, col_ind = linear_sum_assignment(cost_matrix)

    assignments = []
    used_workers_in_shift = set()
    used_slots = set()
    worker_shift_count = {w: 0 for w in workers}

    for r, c in zip(row_ind, col_ind):
        worker, day, shift = worker_copies[r]
        slot = shift_slots[c]
        shift_key = (worker, slot[0], slot[1])

        if (
            cost_matrix[r][c] < 1e6 and
            shift_key not in used_workers_in_shift and
            slot not in used_slots and
            worker_shift_count[worker] < 7
        ):
            used_workers_in_shift.add(shift_key)
            used_slots.add(slot)
            assignments.append({'יום': slot[0], 'משמרת': slot[1], 'עובד': worker})
            worker_shift_count[worker] += 1

    df = pd.DataFrame(assignments)
    df['יום_מספר'] = df['יום'].apply(lambda x: ordered_days.index(x))
    df = df.sort_values(by=['יום_מספר', 'משמרת', 'עובד'])
    df = df[['יום', 'משמרת', 'עובד']]

    st.subheader("📅 טבלת שיבוץ")
    st.dataframe(df, use_container_width=True)

    st.subheader("📊 ניתוח העדפות")
    high_pref_count = sum(preferences.get((a['עובד'], a['יום'], a['משמרת']), 0) == 3 for a in assignments)
    total_assigned = len(assignments)
    percentage = (high_pref_count / total_assigned) * 100 if total_assigned > 0 else 0
    st.write(f"{high_pref_count} מתוך {total_assigned} שיבוצים (כ-{percentage:.1f}%) בוצעו לפי העדפה הגבוהה (3)")
