import streamlit as st

import db
from utils import download_excel, money, month_label

CATEGORIES = ["Rent", "Electricity", "Gas", "Water", "Internet / Phone", "Stationery", "Maintenance",
              "Cleaning", "Transport", "Events", "Furniture / Equipment", "Other"]


def render():
    st.title("🧾 Expenses")
    df = db.load("expenses")
    tab_add, tab_list = st.tabs(["➕ Add Expense", "📋 Expense Register"])

    with tab_add:
        with st.form("add_exp", clear_on_submit=True):
            c1, c2 = st.columns(2)
            d = c1.date_input("Date")
            cat = c2.selectbox("Category", CATEGORIES)
            amt = c1.number_input("Amount *", min_value=0.0, step=100.0)
            to = c2.text_input("Paid to")
            desc = st.text_input("Description")
            if st.form_submit_button("Save expense", type="primary"):
                if amt <= 0:
                    st.error("Enter an amount.")
                else:
                    db.append("expenses", {"expense_id": db.next_id("expenses", "expense_id", "E"),
                                           "date": str(d), "category": cat, "description": desc,
                                           "amount": amt, "paid_to": to})
                    st.success("Saved.")

    with tab_list:
        months = sorted(df["date"].str[:7].unique(), reverse=True)
        m = st.selectbox("Month", ["All"] + months, format_func=month_label)
        view = df if m == "All" else df[df["date"].str[:7] == m]
        st.metric("Total", money(view["amount"].sum()))
        if len(view):
            st.bar_chart(view.groupby("category")["amount"].sum())
        st.dataframe(view.sort_values("date", ascending=False), use_container_width=True, hide_index=True)
        download_excel({"expenses": view}, "expenses.xlsx", key="dl_exp")
        if len(df):
            with st.expander("🗑️ Delete an entry"):
                eid = st.selectbox("Expense", df["expense_id"].iloc[::-1].tolist(), format_func=lambda e: "%s - %s" % (
                    e, " | ".join(df.loc[df["expense_id"] == e, ["date", "category", "amount"]].astype(str).iloc[0])))
                if st.button("Delete"):
                    db.save("expenses", df[df["expense_id"] != eid])
                    st.rerun()
