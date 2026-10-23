import pandas as pd
import streamlit as st

import db
from utils import class_default_fee, class_list, download_excel, form_fields, person_label, today_str


def _fields():
    return [
        ("name", "Student name *", "text", None),
        ("father_name", "Father / guardian name", "text", None),
        ("class", "Class", "select", class_list()),
        ("section", "Section", "text", None),
        ("gender", "Gender", "select", ["Male", "Female"]),
        ("dob", "Date of birth", "date", None),
        ("phone", "Guardian phone (WhatsApp)", "text", None),
        ("admission_date", "Admission date", "date", None),
        ("monthly_fee", "Monthly fee (0 = class default)", "number", None),
        ("status", "Status", "select", ["Active", "Left"]),
        ("address", "Address", "textarea", None),
    ]


def render():
    st.title("👨‍🎓 Students")
    df = db.load("students")
    tab_list, tab_add, tab_edit, tab_import = st.tabs(["📋 All Students", "➕ Add Student",
                                                       "✏️ Edit / Remove", "📥 Import from Excel"])

    with tab_list:
        c1, c2, c3 = st.columns([2, 1, 1])
        q = c1.text_input("🔍 Search by name, father name, ID or phone")
        cls = c2.selectbox("Class", ["All"] + class_list())
        status = c3.selectbox("Status", ["Active", "Left", "All"])
        view = df.copy()
        if cls != "All":
            view = view[view["class"] == cls]
        if status != "All":
            view = view[view["status"] == status]
        if q:
            mask = view.apply(lambda r: q.lower() in " ".join(r.astype(str)).lower(), axis=1)
            view = view[mask]
        st.caption("%d students" % len(view))
        st.dataframe(view, use_container_width=True, hide_index=True)
        download_excel({"students": view}, "students.xlsx", key="dl_students")

    with tab_add:
        with st.form("add_student", clear_on_submit=True):
            vals = form_fields(_fields(), {"admission_date": today_str(), "status": "Active"}, key="add_st")
            if st.form_submit_button("Save student", type="primary"):
                if not vals["name"]:
                    st.error("Student name is required.")
                else:
                    if not vals["monthly_fee"]:
                        vals["monthly_fee"] = class_default_fee(vals["class"])
                    vals["student_id"] = db.next_id("students", "student_id", "S")
                    db.append("students", vals)
                    st.success("Saved %s — ID %s" % (vals["name"], vals["student_id"]))

    with tab_edit:
        if df.empty:
            st.info("No students yet.")
        else:
            labels = person_label(df, "student_id")
            sid = st.selectbox("Select student", list(labels), format_func=labels.get)
            row = df[df["student_id"] == sid].iloc[0].to_dict()
            with st.form("edit_student"):
                vals = form_fields(_fields(), row, key="edit_" + sid)
                if st.form_submit_button("Update", type="primary"):
                    for k, v in vals.items():
                        df.loc[df["student_id"] == sid, k] = v
                    db.save("students", df)
                    st.success("Updated.")
                    st.rerun()
            st.caption("Tip: for a student who leaves, set Status to **Left** instead of deleting, "
                       "so their fee history stays intact.")
            with st.expander("🗑️ Delete permanently"):
                if st.checkbox("I understand this cannot be undone", key="del_chk_" + sid):
                    if st.button("Delete student", type="secondary"):
                        db.save("students", df[df["student_id"] != sid])
                        st.success("Deleted.")
                        st.rerun()

    with tab_import:
        st.write("Move your register to the system in one go: download the template, "
                 "fill one student per row in Excel, then upload it.")
        template = pd.DataFrame(columns=[c for c in db.SCHEMA["students"] if c != "student_id"])
        download_excel({"students": template}, "student_template.xlsx", "⬇️ Download template",
                       key="dl_tpl")
        up = st.file_uploader("Upload filled template", type=["xlsx"])
        if up is not None:
            new = pd.read_excel(up, dtype=object)
            new = new[new["name"].notna()] if "name" in new.columns else new.iloc[0:0]
            st.dataframe(new, use_container_width=True, hide_index=True)
            if len(new) and st.button("Import %d students" % len(new), type="primary"):
                new = db._normalize("students", new)
                start = int(db.next_id("students", "student_id", "S")[1:])
                new["student_id"] = ["S%04d" % (start + i) for i in range(len(new))]
                new.loc[new["status"] == "", "status"] = "Active"
                new.loc[new["admission_date"] == "", "admission_date"] = today_str()
                for i, r in new.iterrows():
                    if not r["monthly_fee"]:
                        new.at[i, "monthly_fee"] = class_default_fee(r["class"])
                db.save("students", pd.concat([df, new], ignore_index=True))
                st.success("Imported %d students." % len(new))
