import streamlit as st

import db
from modules.fees import fee_status
from modules.salaries import salary_status
from utils import money, month_label, this_month, today_str


def render():
    month = this_month()
    st.title("🏠 Dashboard")
    st.caption("Overview for " + month_label(month))
    students, teachers = db.load("students"), db.load("teachers")
    fees, sal, exp, att = db.load("fees"), db.load("salaries"), db.load("expenses"), db.load("attendance")

    received = fees.loc[fees["payment_date"].str[:7] == month, "amount_paid"].sum()
    paid_sal = sal.loc[sal["payment_date"].str[:7] == month, "net_paid"].sum()
    spent = exp.loc[exp["date"].str[:7] == month, "amount"].sum()
    status = fee_status(month, students, fees)
    sstat = salary_status(month, teachers, sal)

    c = st.columns(4)
    c[0].metric("Active students", int((students["status"] == "Active").sum()))
    c[1].metric("Active staff", int((teachers["status"] == "Active").sum()))
    c[2].metric("Fee defaulters (this month)", int((status["status"] != "Paid").sum()))
    c[3].metric("Staff unpaid (this month)", int((sstat["status"] == "Unpaid").sum()))

    c = st.columns(4)
    c[0].metric("Fee received", money(received))
    c[1].metric("Fee outstanding", money(status["balance"].sum()))
    c[2].metric("Salaries + expenses", money(paid_sal + spent))
    c[3].metric("Net balance", money(received - paid_sal - spent))

    today = att[att["date"] == today_str()]
    if len(today):
        vc = today["status"].value_counts()
        st.info("Today's attendance — Present: %d · Absent: %d · Leave: %d"
                % (vc.get("Present", 0), vc.get("Absent", 0), vc.get("Leave", 0)))

    left, right = st.columns(2)
    with left:
        st.subheader("Students per class")
        active = students[students["status"] == "Active"]
        if len(active):
            st.bar_chart(active["class"].value_counts())
        else:
            st.caption("No students yet — start in 👨‍🎓 Students.")
    with right:
        st.subheader("Latest payments")
        st.dataframe(fees.iloc[::-1].head(8)[["receipt_no", "student_name", "class", "month", "amount_paid",
                                               "payment_date"]], hide_index=True, use_container_width=True)
