import streamlit as st

import db


def render():
    st.title("⚙️ Settings")
    tabs = st.tabs(["🏫 School Info", "🏷️ Classes & Fees", "🔑 Password", "💾 Backup & Restore"])

    with tabs[0]:
        with st.form("school_info"):
            name = st.text_input("School name", db.get_setting("school_name"))
            addr = st.text_input("Address", db.get_setting("address"))
            phone = st.text_input("Phone", db.get_setting("phone"))
            c1, c2 = st.columns(2)
            cur = c1.text_input("Currency symbol", db.get_setting("currency"))
            cc = c2.text_input("Country dialing code (for WhatsApp links)", db.get_setting("country_code"))
            if st.form_submit_button("Save", type="primary"):
                db.set_settings({"school_name": name, "address": addr, "phone": phone,
                                 "currency": cur, "country_code": cc.strip().lstrip("+")})
                st.success("Saved.")
                st.rerun()

    with tabs[1]:
        st.write("Add, rename or remove classes and set each class's default monthly fee. "
                 "New students get this fee automatically when their fee is left at 0.")
        classes = db.load("classes")
        edited = st.data_editor(classes, num_rows="dynamic", hide_index=True, use_container_width=True,
                                column_config={"class_name": "Class", "default_fee": st.column_config.NumberColumn(
                                    "Default monthly fee", min_value=0, step=100)})
        if st.button("Save classes", type="primary"):
            edited = edited[edited["class_name"].astype(str).str.strip() != ""].dropna(subset=["class_name"])
            db.save("classes", edited)
            st.success("Classes saved.")
        with st.expander("Apply a class fee to all its existing students"):
            cls = st.selectbox("Class", classes["class_name"].tolist())
            fee = float(classes.loc[classes["class_name"] == cls, "default_fee"].iloc[0]) if len(classes) else 0
            st.caption("Sets monthly fee of every active student in %s to %s." % (cls, "{:,.0f}".format(fee)))
            if st.button("Apply"):
                s = db.load("students")
                s.loc[(s["class"] == cls) & (s["status"] == "Active"), "monthly_fee"] = fee
                db.save("students", s)
                st.success("Updated.")

    with tabs[2]:
        with st.form("pw", clear_on_submit=True):
            old = st.text_input("Current password", type="password")
            new = st.text_input("New password", type="password")
            new2 = st.text_input("Repeat new password", type="password")
            if st.form_submit_button("Change password", type="primary"):
                if db.hash_pw(old) != db.get_setting("admin_password_hash"):
                    st.error("Current password is wrong.")
                elif len(new) < 6 or new != new2:
                    st.error("New passwords must match and be at least 6 characters.")
                else:
                    db.set_settings({"admin_password_hash": db.hash_pw(new)})
                    st.success("Password changed.")
        st.caption("If ADMIN_PASSWORD is set in Streamlit secrets, that password is used instead.")

    with tabs[3]:
        st.write("All your data is one Excel file. Download it to keep a safe copy, "
                 "or open it in Excel for printing.")
        st.download_button("💾 Download backup", db.export_bytes(), file_name="school_backup.xlsx", type="primary",
                           mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        st.divider()
        st.warning("Restoring replaces ALL current data with the uploaded backup.")
        up = st.file_uploader("Upload a backup file (.xlsx)", type=["xlsx"])
        if up is not None and st.checkbox("Yes, replace all current data"):
            if st.button("Restore now"):
                try:
                    db.restore(up.getvalue())
                    st.success("Data restored.")
                except Exception as e:
                    st.error(str(e))
