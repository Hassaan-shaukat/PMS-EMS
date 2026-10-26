# 🏫 School Management System (Streamlit + Google Sheets / Excel)

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
4. Deploy. On first open, go to Settings → Backup & Restore to upload your data if you ## Permanent storage with Google Sheets (free, required on Streamlit Cloud)
Streamlit Cloud wipes local files whenever the app sleeps or restarts. With Google Sheets set up,
all data is saved in a Google Sheet (one tab per table) and is never lost. You can also open
that sheet any time to view or print records.

1. **Create the sheet:** go to https://sheets.google.com → *Blank spreadsheet* → name it
   `School Data`. Copy its URL from the browser address bar.
2. **Create a Google Cloud project:** go to https://console.cloud.google.com → top bar project
   picker → *New Project* → name `school-app` → *Create*. Make sure it is selected.
3. **Enable the APIs:** open https://console.cloud.google.com/apis/library/sheets.googleapis.com → *Enable*.
   Then https://console.cloud.google.com/apis/library/drive.googleapis.com → *Enable*.
4. **Create a service account (a robot user):** go to *IAM & Admin → Service Accounts* →
   *Create service account* → name `school-app` → *Create and continue* → *Done*.
5. **Download its key:** click the new service account → *Keys* tab → *Add key → Create new key*
   → *JSON* → *Create*. A `.json` file downloads. Keep it private and never upload it to GitHub.
6. **Share the sheet with the robot:** open the JSON file in Notepad, copy the `client_email`
   value (ends with `iam.gserviceaccount.com`). In your Google Sheet click *Share*, paste that
   email, choose **Editor**, untick *Notify*, click *Share*.
7. **Add secrets in Streamlit:** share.streamlit.io → your app → ⋮ → *Settings → Secrets*, paste:
   ```toml
   ADMIN_PASSWORD = "your-strong-password"
   spreadsheet_url = "PASTE THE SHEET URL HERE"

   [gcp_service_account]
   # copy each field from the JSON file, in the form  name = "value"
   type = "service_account"
   project_id = "..."
   private_key_id = "..."
   private_key = "-----BEGIN PRIVATE KEY-----\n...\n-----END PRIVATE KEY-----\n"
   client_email = "..."
   client_id = "..."
   auth_uri = "https://accounts.google.com/o/oauth2/auth"
   token_uri = "https://oauth2.googleapis.com/token"
   auth_provider_x509_cert_url = "https://www.googleapis.com/oauth2/v1/certs"
   client_x509_cert_url = "..."
   ```
   Click *Save*. The app restarts and creates its tabs in the sheet automatically.
8. If you have an old backup `.xlsx`, upload it in **Settings → Backup & Restore**.

Without these secrets (e.g. on your own PC) the app uses `data/school_data.xlsx` as before.

ds to change).

## Daily workflow
1. Parent pays → **Fee Collection → Collect Fee** → select student → Save → print receipt.
2. Month end → **Monthly Status & Defaulters** → send WhatsApp reminders.
3. Pay teachers → **Salaries → Pay Salary** → print slip.
4. Record bills in **Expenses**. Check **Reports** for profit/loss.
5. Download a backup.
# PMS-EMS
