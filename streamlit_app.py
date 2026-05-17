import streamlit as st
import pandas as pd
import numpy as np
from io import BytesIO
import sqlite3
import hashlib
import os
import hmac

# =============================
# CONFIG
# =============================
st.set_page_config(page_title="מערכת שיבוץ משמרות", layout="wide")

st.markdown("""
<style>
html, body {direction: rtl; text-align: right;}
</style>
""", unsafe_allow_html=True)

# =============================
# AUTH
# =============================
DB_PATH = "users.db"

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("""
    CREATE TABLE IF NOT EXISTS users (
        username TEXT PRIMARY KEY,
        password_hash TEXT,
        salt TEXT
    )
    """)
    conn.commit()
    conn.close()

def hash_password(password, salt):
    return hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 100000).hex()

def create_user(username, password):
    salt = os.urandom(16).hex()
    p_hash = hash_password(password, salt)
    try:
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        cur.execute("INSERT INTO users VALUES (?, ?, ?)", (username, p_hash, salt))
        conn.commit()
        conn.close()
        return True
    except:
        return False

def verify_user(username, password):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT password_hash, salt FROM users WHERE username=?", (username,))
    row = cur.fetchone()
    conn.close()
    if not row:
        return False
    return hmac.compare_digest(row[0], hash_password(password, row[1]))

def auth():
    init_db()

    if "logged_in" not in st.session_state:
        st.session_state.logged_in = False

    if st.session_state.logged_in:
        return

    st.title("🔐 התחברות")

    u = st.text_input("משתמש")
    p = st.text_input("סיסמה", type="password")

    if st.button("התחבר"):
        if verify_user(u, p):
            st.session_state.logged_in = True
            st.session_state.username = u
            st.rerun()
        else:
            st.error("שגיאה")

    st.subheader("הרשמה")
    nu = st.text_input("משתמש חדש")
    npw = st.text_input("סיסמה חדשה", type="password")

    if st.button("הרשם"):
        if create_user(nu, npw):
            st.success("נרשמת!")
        else:
            st.error("משתמש קיים")

    st.stop()

auth()

# =============================
# ALGORITHM
# =============================
def simple_assignment(cost_matrix):
    used_rows, used_cols = set(), set()
    result = []

    for _ in range(min(len(cost_matrix), len(cost_matrix[0]))):
        best = None
        best_cost = 1e9

        for i in range(len(cost_matrix)):
            if i in used_rows: continue
            for j in range(len(cost_matrix[0])):
                if j in used_cols: continue

                if cost_matrix[i][j] < best_cost:
                    best_cost = cost_matrix[i][j]
                    best = (i, j)

        if not best:
            break

        r, c = best
        result.append((r, c))
        used_rows.add(r)
        used_cols.add(c)

    return result

def build_schedule(workers_df, req_df, pref_df):
    workers = workers_df.iloc[:,0].tolist()

    slots = []
    for _, r in req_df.iterrows():
        for i in range(int(r[2])):
            slots.append((r[0], r[1]))

    pref_dict = {}
    for _, r in pref_df.iterrows():
        pref_dict[(r[0], r[1], r[2])] = r[3]

    cost = []
    for w in workers:
        row = []
        for d,s in slots:
            p = pref_dict.get((w,d,s), -1)
            if p == -1:
                row.append(1e6)
            elif p == 0:
                row.append(100)
            else:
                row.append(4-p)
        cost.append(row)

    assignments = simple_assignment(cost)

    result = []
    for r,c in assignments:
        w = workers[r]
        d,s = slots[c]
        result.append({"עובד":w,"יום":d,"משמרת":s})

    return pd.DataFrame(result)

# =============================
# UI
# =============================
st.title("📊 שיבוץ עובדים")

file = st.file_uploader("העלה קובץ Excel", type=["xlsx"])

if file:
    workers = pd.read_excel(file, sheet_name="workers")
    req = pd.read_excel(file, sheet_name="requirements")
    pref = pd.read_excel(file, sheet_name="preferences")

    if st.button("🚀 בצע שיבוץ"):
        df = build_schedule(workers, req, pref)
        st.dataframe(df)

        out = BytesIO()
        df.to_excel(out, index=False)
        st.download_button("⬇️ הורד תוצאה", out.getvalue(), "schedule.xlsx")
