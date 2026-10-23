import streamlit as st

import db
from utils import download_excel, form_fields, person_label, today_str

FIELDS = [
    ("name", "Teacher name *", "text", None),
    ("phone", "Phone", "text", None),
    ("cnic", "CNIC / ID card no.", "text", None),
    ("subject", "Subject(s)", "text", None),
    ("qualification", "Qualification", "text", None),
    ("joining_date", "Joining date", "date", None),
    ("monthly_salary", "Monthly salary", "number", None),
    ("status", "Status", "select", ["Active", "Left"]),
]


def render():
    st.title("👩‍🏫 Teachers & Staff")
    df = db.load("teachers")
    tab_list, tab_add, tab_edit = st.tabs(["📋 All Staff", "➕ Add", "✏️ Edit / Remove"])

    with tab_list:
        status = st.selectbox("Status", ["Active", "Left", "All"], key="t_status")
        view = df if status == "All" else df[df["status"] == status]
        c1, c2 = st.columns(2)
        c1.metric("Staff", len(view))
        c2.metric("Monthly salary bill", "{:,.0f}".format(view["monthly_salary"].sum()))
        st.dataframe(view, use_container_width=True, hide_index=True)
        download_excel({"teachers": view}, "teachers.xlsx", key="dl_teachers")

    with tab_add:
        with st.form("add_teacher", clear_on_submit=True):
            vals = form_fields(FIELDS, {"joining_date": today_str(), "status": "Active"}, key="add_t")
            if st.form_submit_button("Save", type="primary"):
                if not vals["name"]:
                    st.error("Name is required.")
                else:
                    vals["teacher_id"] = db.next_id("teachers", "teacher_id", "T")
                    db.append("teachers", vals)
                    st.success("Saved %s — ID %s" % (vals["name"], vals["teacher_id"]))

    with tab_edit:
        if df.empty:
            st.info("No teachers yet.")
            return
        labels = person_label(df, "teacher_id")
        tid = st.selectbox("Select teacher", list(labels), format_func=labels.get)
        row = df[df["teacher_id"] == tid].iloc[0].to_dict()
        with st.form("edit_teacher"):
            vals = form_fields(FIELDS, row, key="edit_" + tid)
            if st.form_submit_button("Update", type="primary"):
                for k, v in vals.items():
                    df.loc[df["teacher_id"] == tid, k] = v
                db.save("teachers", df)
                st.success("Updated.")
                st.rerun()
        with st.expander("🗑️ Delete permanently"):
            if st.checkbox("I understand this cannot be undone", key="tdel_" + tid):
                if st.button("Delete teacher"):
                    db.save("teachers", df[df["teacher_id"] != tid])
                    st.rerun()
