import streamlit as st

import db
from utils import (PAYMENT_METHODS, download_excel, money, month_label, month_select, person_label,
                   receipt_html)


def _slip(rec):
    rows = [("Name", rec["teacher_name"]), ("Staff ID", rec["teacher_id"]),
            ("Salary month", month_label(rec["month"])), ("Basic salary", money(rec["basic_salary"])),
            ("Bonus / Allowance", money(rec["bonus"])), ("Deductions (leave etc.)", money(rec["deduction"])),
            ("Advance adjusted", money(rec["advance"])), ("Payment method", rec["method"]),
            ("Date", rec["payment_date"])]
    return receipt_html("SALARY SLIP", rec["slip_no"], rows, "Net Paid", money(rec["net_paid"]),
                        rec.get("remarks", ""))


def salary_status(month, teachers=None, sal=None):
    teachers = db.load("teachers") if teachers is None else teachers
    sal = db.load("salaries") if sal is None else sal
    t = teachers[(teachers["status"] == "Active") & (teachers["joining_date"].str[:7] <= month)]
    paid = sal[sal["month"] == month].groupby("teacher_id")["net_paid"].sum()
    t = t[["teacher_id", "name", "subject", "phone", "monthly_salary"]].copy()
    t["paid"] = t["teacher_id"].map(paid).fillna(0)
    t["status"] = ["Paid" if p > 0 else "Unpaid" for p in t["paid"]]
    return t


def render():
    st.title("💵 Teacher Salaries")
    teachers, sal = db.load("teachers"), db.load("salaries")
    tabs = st.tabs(["💸 Pay Salary", "📋 Monthly Status", "🧾 Salary History"])

    with tabs[0]:
        active = teachers[teachers["status"] == "Active"]
        if active.empty:
            st.info("Add teachers first.")
        else:
            c1, c2 = st.columns(2)
            labels = person_label(active, "teacher_id")
            tid = c1.selectbox("Teacher", list(labels), format_func=labels.get)
            with c2:
                month = month_select("Salary month", key="sal_month")
            t = active[active["teacher_id"] == tid].iloc[0]
            already = sal[(sal["teacher_id"] == tid) & (sal["month"] == month)]
            if len(already):
                st.warning("Already paid %s for %s." % (money(already["net_paid"].sum()), month_label(month)))

            k = tid + month
            with st.form("pay_" + k):
                a, b = st.columns(2)
                basic = a.number_input("Basic salary", min_value=0.0, step=500.0,
                                       value=float(t["monthly_salary"]), key="b" + k)
                bonus = b.number_input("Bonus / allowance", min_value=0.0, step=100.0, key="bo" + k)
                a, b = st.columns(2)
                ded = a.number_input("Deductions (leaves, late)", min_value=0.0, step=100.0, key="de" + k)
                adv = b.number_input("Advance to adjust", min_value=0.0, step=100.0, key="ad" + k)
                a, b = st.columns(2)
                method = a.selectbox("Method", PAYMENT_METHODS, key="me" + k)
                pdate = b.date_input("Payment date", key="pd" + k)
                remarks = st.text_input("Remarks", key="re" + k)
                net = basic + bonus - ded - adv
                if st.form_submit_button("💾 Save salary payment", type="primary"):
                    rec = {"slip_no": db.next_id("salaries", "slip_no", "P"), "teacher_id": tid,
                           "teacher_name": t["name"], "month": month, "basic_salary": basic, "bonus": bonus,
                           "deduction": ded, "advance": adv, "net_paid": net, "payment_date": str(pdate),
                           "method": method, "remarks": remarks}
                    db.append("salaries", rec)
                    st.session_state["last_slip"] = (rec["slip_no"], _slip(rec), net)
                    st.rerun()
            if "last_slip" in st.session_state:
                no, page, net = st.session_state["last_slip"]
                st.success("Saved slip #%s — net paid %s" % (no, money(net)))
                st.download_button("🖨️ Download salary slip", page, file_name="salary_slip_%s.html" % no,
                                   mime="text/html")

    with tabs[1]:
        month = month_select("Month", key="sal_status_month")
        s = salary_status(month, teachers, sal)
        c1, c2, c3 = st.columns(3)
        c1.metric("Salary bill", money(s["monthly_salary"].sum()))
        c2.metric("Paid", money(s["paid"].sum()))
        c3.metric("Unpaid staff", int((s["status"] == "Unpaid").sum()))
        st.dataframe(s, use_container_width=True, hide_index=True)

    with tabs[2]:
        months = sorted(sal["month"].unique(), reverse=True)
        m = st.selectbox("Salary month", ["All"] + months, format_func=month_label)
        h = sal if m == "All" else sal[sal["month"] == m]
        st.metric("Total paid", money(h["net_paid"].sum()))
        st.dataframe(h.iloc[::-1], use_container_width=True, hide_index=True)
        download_excel({"salaries": h}, "salaries.xlsx", key="dl_sal")
        if len(sal):
            st.subheader("Reprint or cancel a slip")
            no = st.selectbox("Slip no.", sal["slip_no"].iloc[::-1].tolist())
            rec = sal[sal["slip_no"] == no].iloc[0].to_dict()
            c1, c2 = st.columns(2)
            c1.download_button("🖨️ Reprint", _slip(rec), file_name="salary_slip_%s.html" % no, mime="text/html")
            if c2.checkbox("Confirm cancel slip %s" % no):
                if c2.button("❌ Cancel slip"):
                    db.save("salaries", sal[sal["slip_no"] != no])
                    st.session_state.pop("last_slip", None)
                    st.rerun()
