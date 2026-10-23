import numpy as np
import pandas as pd
import streamlit as st

import db
from utils import (PAYMENT_METHODS, class_list, download_excel, money, month_label, month_select,
                   months_between, person_label, receipt_html, this_month, today_str, whatsapp_link)

FEE_TYPES = ["Monthly", "Admission", "Annual / Exam", "Books & Uniform", "Other"]


def fee_status(month, students=None, fees=None):
    """Monthly-fee position of every active student for one month."""
    students = db.load("students") if students is None else students
    fees = db.load("fees") if fees is None else fees
    s = students[(students["status"] == "Active") & (students["admission_date"].str[:7] <= month)]
    f = fees[(fees["month"] == month) & (fees["fee_type"] == "Monthly")]
    agg = f.groupby("student_id")[["amount_paid", "discount", "fine"]].sum().reset_index()
    t = s[["student_id", "name", "father_name", "class", "phone", "monthly_fee"]].merge(
        agg, on="student_id", how="left").fillna({"amount_paid": 0, "discount": 0, "fine": 0})
    t["balance"] = (t["monthly_fee"] + t["fine"] - t["discount"] - t["amount_paid"]).clip(lower=0)
    t["status"] = np.where(t["balance"] <= 0, "Paid", np.where(t["amount_paid"] > 0, "Partial", "Unpaid"))
    return t


def ledger(student, fees):
    """Month-by-month monthly-fee ledger for one student, admission month to now."""
    f = fees[(fees["student_id"] == student["student_id"]) & (fees["fee_type"] == "Monthly")]
    start = (student["admission_date"] or this_month())[:7]
    if len(f):
        start = min(start, f["month"].min())
    rows = []
    for m in months_between(start, this_month()):
        fm = f[f["month"] == m]
        paid, disc, fine = fm["amount_paid"].sum(), fm["discount"].sum(), fm["fine"].sum()
        bal = max(student["monthly_fee"] + fine - disc - paid, 0)
        rows.append({"month": m, "Month": month_label(m), "Fee": student["monthly_fee"], "Discount": disc,
                     "Fine": fine, "Paid": paid, "Balance": bal})
    return pd.DataFrame(rows)


def _receipt(rec, balance):
    rows = [("Student", rec["student_name"]), ("Student ID", rec["student_id"]), ("Class", rec["class"]),
            ("Fee type", rec["fee_type"]), ("Fee month", month_label(rec["month"])),
            ("Fee amount", money(rec["amount_due"])), ("Discount", money(rec["discount"])),
            ("Fine", money(rec["fine"])), ("Payment method", rec["method"]),
            ("Date", rec["payment_date"])]
    note = "Remaining balance for this month: %s" % money(balance) if rec["fee_type"] == "Monthly" else ""
    if rec.get("remarks"):
        note += "  Remarks: " + rec["remarks"]
    return receipt_html("FEE RECEIPT", rec["receipt_no"], rows, "Amount Paid", money(rec["amount_paid"]), note)


def render():
    st.title("💰 Fee Collection")
    students, fees = db.load("students"), db.load("fees")
    tabs = st.tabs(["💳 Collect Fee", "📋 Monthly Status & Defaulters", "📒 Student Ledger", "🧾 Fee History"])

    # ---------------- collect ----------------
    with tabs[0]:
        active = students[students["status"] == "Active"]
        if active.empty:
            st.info("Add students first.")
        else:
            labels = person_label(active, "student_id")
            sid = st.selectbox("Student (type to search)", list(labels), format_func=labels.get)
            stu = active[active["student_id"] == sid].iloc[0]

            led = ledger(stu, fees)
            pending = led[led["Balance"] > 0]
            if len(pending):
                st.warning("Pending months: " + ", ".join(
                    "%s (%s)" % (r["Month"], money(r["Balance"])) for _, r in pending.iterrows())
                    + "  —  **Total due %s**" % money(pending["Balance"].sum()))
            else:
                st.success("No pending monthly fee. ✅")

            c1, c2 = st.columns(2)
            ftype = c1.selectbox("Fee type", FEE_TYPES)
            default_month = pending["month"].iloc[0] if len(pending) else this_month()
            with c2:
                month = month_select("For month", key="fee_month_" + sid, default=default_month)
            if ftype == "Monthly":
                cur = led[led["month"] == month]
                balance = float(cur["Balance"].iloc[0]) if len(cur) else float(stu["monthly_fee"])
                st.info("Monthly fee **%s** · Balance for %s: **%s**"
                        % (money(stu["monthly_fee"]), month_label(month), money(balance)))

            k = "%s_%s_%s" % (sid, month, ftype)
            with st.form("collect_" + k):
                a, b, c = st.columns(3)
                if ftype == "Monthly":
                    due = float(stu["monthly_fee"])
                    a.number_input("Fee amount", value=due, disabled=True, key="due_" + k)
                else:
                    due = a.number_input("Fee amount", min_value=0.0, step=100.0, key="due_" + k)
                disc = b.number_input("Discount", min_value=0.0, step=50.0, key="disc_" + k)
                fine = c.number_input("Late fine", min_value=0.0, step=50.0, key="fine_" + k)
                a, b, c = st.columns(3)
                paid = a.number_input("Amount received *", min_value=0.0, step=100.0,
                                      value=balance if ftype == "Monthly" else 0.0, key="paid_" + k)
                method = b.selectbox("Method", PAYMENT_METHODS, key="m_" + k)
                pdate = c.date_input("Payment date", key="d_" + k)
                remarks = st.text_input("Remarks", key="r_" + k)
                if st.form_submit_button("💾 Save payment", type="primary"):
                    if paid <= 0 and disc <= 0:
                        st.error("Enter the amount received.")
                    else:
                        rec = {"receipt_no": db.next_id("fees", "receipt_no", "R"), "student_id": sid,
                               "student_name": stu["name"], "class": stu["class"], "fee_type": ftype,
                               "month": month, "amount_due": due, "discount": disc, "fine": fine,
                               "amount_paid": paid, "payment_date": str(pdate), "method": method,
                               "remarks": remarks}
                        db.append("fees", rec)
                        new_bal = max(balance + fine - disc - paid, 0) if ftype == "Monthly" else 0
                        st.session_state["last_receipt"] = (rec["receipt_no"], _receipt(rec, new_bal))
                        st.rerun()

            if "last_receipt" in st.session_state:
                no, page = st.session_state["last_receipt"]
                st.success("Payment saved. Receipt #%s" % no)
                st.download_button("🖨️ Download receipt (open & print)", page,
                                   file_name="receipt_%s.html" % no, mime="text/html")

    # ---------------- status / defaulters ----------------
    with tabs[1]:
        c1, c2 = st.columns(2)
        with c1:
            month = month_select("Month", key="status_month")
        cls = c2.selectbox("Class", ["All"] + class_list(), key="status_cls")
        t = fee_status(month, students, fees)
        if cls != "All":
            t = t[t["class"] == cls]
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Expected", money(t["monthly_fee"].sum()))
        m2.metric("Collected", money(t["amount_paid"].sum()))
        m3.metric("Outstanding", money(t["balance"].sum()))
        m4.metric("Defaulters", int((t["status"] != "Paid").sum()))

        only_def = st.toggle("Show defaulters only", value=True)
        view = t[t["status"] != "Paid"] if only_def else t
        school = db.get_setting("school_name")
        view = view.assign(WhatsApp=[
            whatsapp_link(r["phone"], "Dear Parent, the fee of %s (%s) for %s is pending: %s. Kindly pay "
                          "at the earliest. - %s" % (r["name"], r["class"], month_label(month),
                                                     money(r["balance"]), school))
            if r["status"] != "Paid" else None for _, r in view.iterrows()])
        st.dataframe(view, use_container_width=True, hide_index=True, column_config={
            "WhatsApp": st.column_config.LinkColumn("Reminder", display_text="📲 Send")})
        download_excel({"fee_status": view.drop(columns=["WhatsApp"])},
                       "fee_status_%s.xlsx" % month, key="dl_status")

    # ---------------- ledger ----------------
    with tabs[2]:
        if students.empty:
            st.info("No students yet.")
        else:
            labels = person_label(students, "student_id")
            sid = st.selectbox("Student", list(labels), format_func=labels.get, key="ledger_sid")
            stu = students[students["student_id"] == sid].iloc[0]
            led = ledger(stu, fees)
            c1, c2, c3 = st.columns(3)
            c1.metric("Monthly fee", money(stu["monthly_fee"]))
            c2.metric("Total paid", money(fees.loc[fees["student_id"] == sid, "amount_paid"].sum()))
            c3.metric("Total outstanding", money(led["Balance"].sum() if len(led) else 0))
            st.dataframe(led.drop(columns=["month"]), use_container_width=True, hide_index=True)
            st.caption("All payments (including admission/exam fees):")
            st.dataframe(fees[fees["student_id"] == sid], use_container_width=True, hide_index=True)

    # ---------------- history ----------------
    with tabs[3]:
        c1, c2 = st.columns(2)
        months = sorted(fees["payment_date"].str[:7].unique(), reverse=True)
        pm = c1.selectbox("Payments received in", ["All"] + months, format_func=month_label)
        q = c2.text_input("Search name / receipt / ID")
        h = fees if pm == "All" else fees[fees["payment_date"].str[:7] == pm]
        if q:
            h = h[h.apply(lambda r: q.lower() in " ".join(r.astype(str)).lower(), axis=1)]
        st.metric("Total received", money(h["amount_paid"].sum()))
        st.dataframe(h.iloc[::-1], use_container_width=True, hide_index=True)
        download_excel({"fees": h}, "fee_history.xlsx", key="dl_feehist")

        if len(fees):
            st.subheader("Reprint or cancel a receipt")
            rno = st.selectbox("Receipt no.", fees["receipt_no"].iloc[::-1].tolist())
            rec = fees[fees["receipt_no"] == rno].iloc[0].to_dict()
            c1, c2 = st.columns(2)
            bal = 0
            if rec["fee_type"] == "Monthly":
                bal = fee_status(rec["month"], students, fees).set_index("student_id")["balance"].get(rec["student_id"], 0)
            c1.download_button("🖨️ Reprint", _receipt(rec, bal), file_name="receipt_%s.html" % rno, mime="text/html")
            if c2.checkbox("Confirm cancel receipt %s" % rno):
                if c2.button("❌ Cancel receipt"):
                    db.save("fees", fees[fees["receipt_no"] != rno])
                    st.session_state.pop("last_receipt", None)
                    st.rerun()
