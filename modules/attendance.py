import pandas as pd
import streamlit as st

import db
from utils import class_list, download_excel, month_label, month_select

STATUSES = ["Present", "Absent", "Leave"]


def render():
    st.title("✅ Student Attendance")
    students, att = db.load("students"), db.load("attendance")
    tab_mark, tab_report = st.tabs(["📝 Mark Attendance", "📊 Monthly Report"])

    with tab_mark:
        c1, c2 = st.columns(2)
        cls = c1.selectbox("Class", class_list(), key="att_cls")
        d = str(c2.date_input("Date", key="att_date"))
        roster = students[(students["class"] == cls) & (students["status"] == "Active")]
        if roster.empty:
            st.info("No active students in this class.")
        else:
            existing = att[(att["date"] == d) & (att["class"] == cls)].set_index("student_id")["status"]
            if len(existing):
                st.caption("Attendance already saved for this day — you can edit and save again.")
            sheet = pd.DataFrame({"student_id": roster["student_id"], "name": roster["name"],
                                  "status": roster["student_id"].map(existing).fillna("Present")})
            edited = st.data_editor(sheet, hide_index=True, use_container_width=True, key="att_%s_%s" % (cls, d),
                                    disabled=["student_id", "name"], column_config={
                                        "status": st.column_config.SelectboxColumn("Status", options=STATUSES,
                                                                                   required=True)})
            counts = edited["status"].value_counts()
            st.write(" · ".join("**%s**: %d" % (s, counts.get(s, 0)) for s in STATUSES))
            if st.button("💾 Save attendance", type="primary"):
                keep = att[~((att["date"] == d) & (att["class"] == cls))]
                new = pd.DataFrame({"date": d, "student_id": edited["student_id"],
                                    "student_name": edited["name"], "class": cls, "status": edited["status"]})
                db.save("attendance", pd.concat([keep, new], ignore_index=True))
                st.success("Attendance saved for %s, %s." % (cls, d))

    with tab_report:
        c1, c2 = st.columns(2)
        with c1:
            month = month_select("Month", key="att_rep_month")
        cls = c2.selectbox("Class", class_list(), key="att_rep_cls")
        a = att[(att["date"].str[:7] == month) & (att["class"] == cls)]
        if a.empty:
            st.info("No attendance recorded for %s in %s." % (cls, month_label(month)))
        else:
            rep = a.pivot_table(index=["student_id", "student_name"], columns="status", values="date",
                                aggfunc="count", fill_value=0).reset_index()
            for s in STATUSES:
                if s not in rep.columns:
                    rep[s] = 0
            rep["Days"] = rep[STATUSES].sum(axis=1)
            rep["Attendance %"] = (rep["Present"] / rep["Days"] * 100).round(1)
            st.dataframe(rep, use_container_width=True, hide_index=True)
            download_excel({"attendance": rep}, "attendance_%s_%s.xlsx" % (cls, month), key="dl_att")
