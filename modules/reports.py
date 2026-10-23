import pandas as pd
import streamlit as st

import db
from modules.fees import fee_status
from modules.salaries import salary_status
from utils import download_excel, money, month_label, month_options, month_select


def render():
    st.title("📊 Reports")
    students, teachers = db.load("students"), db.load("teachers")
    fees, sal, exp = db.load("fees"), db.load("salaries"), db.load("expenses")
    tab_month, tab_trend = st.tabs(["📅 Monthly Report", "📈 12-Month Trend"])

    with tab_month:
        month = month_select("Month", key="rep_month")
        f = fees[fees["payment_date"].str[:7] == month]
        s = sal[sal["payment_date"].str[:7] == month]
        e = exp[exp["date"].str[:7] == month]
        income, salaries, expenses = f["amount_paid"].sum(), s["net_paid"].sum(), e["amount"].sum()

        c = st.columns(4)
        c[0].metric("Income (fees received)", money(income))
        c[1].metric("Salaries paid", money(salaries))
        c[2].metric("Other expenses", money(expenses))
        c[3].metric("Profit / Loss", money(income - salaries - expenses))
        st.caption("Based on actual payment dates in %s (cash received / paid)." % month_label(month))

        status = fee_status(month, students, fees)
        st.subheader("Class-wise fee position for " + month_label(month))
        by_class = status.groupby("class").agg(Students=("student_id", "count"), Expected=("monthly_fee", "sum"),
                                               Collected=("amount_paid", "sum"), Outstanding=("balance", "sum"))
        st.dataframe(by_class, use_container_width=True)

        st.subheader("Income by fee type")
        st.dataframe(f.groupby("fee_type")["amount_paid"].sum().rename("Amount"), use_container_width=True)

        download_excel({
            "summary": pd.DataFrame([{"Month": month_label(month), "Income": income, "Salaries": salaries,
                                      "Expenses": expenses, "Net": income - salaries - expenses}]),
            "class_wise": by_class.reset_index(),
            "defaulters": status[status["status"] != "Paid"],
            "fees_received": f, "salaries_paid": s, "expenses": e,
            "salary_status": salary_status(month, teachers, sal),
        }, "monthly_report_%s.xlsx" % month, "⬇️ Download full monthly report (Excel)", key="dl_monthrep")

    with tab_trend:
        months = sorted(month_options(back=11, ahead=0))
        trend = pd.DataFrame({
            "Month": [month_label(m) for m in months],
            "Income": [fees.loc[fees["payment_date"].str[:7] == m, "amount_paid"].sum() for m in months],
            "Salaries": [sal.loc[sal["payment_date"].str[:7] == m, "net_paid"].sum() for m in months],
            "Expenses": [exp.loc[exp["date"].str[:7] == m, "amount"].sum() for m in months],
        })
        trend["Net"] = trend["Income"] - trend["Salaries"] - trend["Expenses"]
        st.bar_chart(trend.set_index("Month")[["Income", "Salaries", "Expenses"]], stack=False)
        st.dataframe(trend, use_container_width=True, hide_index=True)
        download_excel({"trend": trend}, "12_month_trend.xlsx", key="dl_trend")
