# 🏫 School Management System (Streamlit + Excel)

A lightweight system to replace the paper fee & salary register. All data is stored
in one Excel file: `data/school_data.xlsx` (created automatically on first run).

## Features
| Module | What it does |
|---|---|
| 🏠 Dashboard | Students, staff, fee received/outstanding, salaries, expenses, net balance |
| 👨‍🎓 Students | Add / edit / search / mark as Left, bulk import from Excel template |
| 💰 Fee Collection | Collect monthly / admission / exam fees, discounts & fines, partial payments, printable receipts, defaulter list with one-click WhatsApp reminders, student ledger with arrears |
| 👩‍🏫 Teachers | Staff records and salary |
| 💵 Salaries | Pay salary with bonus / deductions / advance, printable salary slips, unpaid staff list |
| 🧾 Expenses | Rent, bills, stationery etc. by category |
| ✅ Attendance | Daily class attendance, monthly attendance % report |
| 📊 Reports | Monthly profit/loss, class-wise collection, 12-month trend, full Excel export |
| ⚙️ Settings | School name, classes & default fees, password, backup & restore |

## Run on your computer (recommended for daily use)
```bash
pip install -r requirements.txt
streamlit run app.py
```
Open http://localhost:8501 — default password **admin123** (change it in Settings).

## Deploy on Streamlit Community Cloud (free)
1. Create a **private** GitHub repository and upload this folder.
2. Go to https://share.streamlit.io → *New app* → pick the repo, main file `app.py`.
3. In *Advanced settings → Secrets* add: `ADMIN_PASSWORD = "your-strong-password"`.
4. Deploy. On first open, go to Settings → Backup & Restore to upload your data if you have a backup.

> ⚠️ **Important:** Streamlit Cloud does not keep files permanently. When the app restarts
> (after updates or inactivity) the Excel file is reset. Click **💾 Backup all data** in the
> sidebar at the end of each day, and use **Restore** after a restart. For permanent cloud
> storage, upgrade the storage layer to Google Sheets (only `db.py` needs to change).

## Daily workflow
1. Parent pays → **Fee Collection → Collect Fee** → select student → Save → print receipt.
2. Month end → **Monthly Status & Defaulters** → send WhatsApp reminders.
3. Pay teachers → **Salaries → Pay Salary** → print slip.
4. Record bills in **Expenses**. Check **Reports** for profit/loss.
5. Download a backup.
