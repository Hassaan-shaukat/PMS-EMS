"""School Management System — run with:  streamlit run app.py"""
from datetime import date

import streamlit as st

st.set_page_config(page_title="School Manager", page_icon="🏫", layout="wide")

import db  # noqa: E402
import utils  # noqa: E402
from modules import (attendance, dashboard, expenses, fees, reports,  # noqa: E402
                     salaries, settings, students, teachers)

db.init_db()
if not utils.check_login():
    st.stop()

PAGES = {
    "🏠 Dashboard": dashboard,
    "👨‍🎓 Students": students,
    "💰 Fee Collection": fees,
    "👩‍🏫 Teachers": teachers,
    "💵 Salaries": salaries,
    "🧾 Expenses": expenses,
    "✅ Attendance": attendance,
    "📊 Reports": reports,
    "⚙️ Settings": settings,
}

with st.sidebar:
    st.markdown("## 🏫 " + db.get_setting("school_name"))
    st.caption(date.today().strftime("%A, %d %B %Y"))
    choice = st.radio("Menu", list(PAGES), label_visibility="collapsed")
    st.divider()
    st.download_button("💾 Backup all data", db.export_bytes(), use_container_width=True,
                       file_name="school_backup_%s.xlsx" % utils.today_str(),
                       mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    st.caption("Download a backup at the end of every day.")
    if st.button("🚪 Logout", use_container_width=True):
        st.session_state.clear()
        st.rerun()

PAGES[choice].render()
