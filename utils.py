"""Shared helpers: formatting, months, forms, login, receipts, downloads."""
import html
import re
from datetime import date, datetime
from io import BytesIO
from urllib.parse import quote

import pandas as pd
import streamlit as st

import db

PAYMENT_METHODS = ["Cash", "Bank Transfer", "Mobile Wallet", "Cheque"]


# ---------- formatting ----------
def currency():
    return db.get_setting("currency") or "Rs."


def money(x):
    return "%s %s" % (currency(), "{:,.0f}".format(float(x or 0)))


def today_str():
    return date.today().strftime("%Y-%m-%d")


def this_month():
    return date.today().strftime("%Y-%m")


def month_label(m):
    try:
        return datetime.strptime(m, "%Y-%m").strftime("%b %Y")
    except (TypeError, ValueError):
        return m


def month_options(back=12, ahead=2):
    t = date.today()
    out = []
    for i in range(-back, ahead + 1):
        y, m = divmod(t.month - 1 + i, 12)
        out.append("%d-%02d" % (t.year + y, m + 1))
    return out[::-1]  # newest first


def month_select(label, key, default=None):
    opts = month_options()
    default = default or this_month()
    idx = opts.index(default) if default in opts else 0
    return st.selectbox(label, opts, index=idx, format_func=month_label, key=key)


def months_between(start, end):
    """All 'YYYY-MM' strings from start to end inclusive."""
    out = []
    y, m = int(start[:4]), int(start[5:7])
    while "%d-%02d" % (y, m) <= end:
        out.append("%d-%02d" % (y, m))
        m += 1
        if m > 12:
            y, m = y + 1, 1
    return out


def parse_date(v, fallback=None):
    try:
        return datetime.strptime(str(v)[:10], "%Y-%m-%d").date()
    except ValueError:
        return fallback or date.today()


# ---------- generic form ----------
def form_fields(fields, values=None, key=""):
    """Render inputs in two columns. fields = [(column, label, kind, options)]."""
    values = values or {}
    out = {}
    cols = st.columns(2)
    for i, (name, label, kind, opts) in enumerate(fields):
        v = values.get(name)
        k = "%s_%s" % (key, name)
        with cols[i % 2]:
            if kind == "number":
                out[name] = st.number_input(label, min_value=0.0, step=100.0,
                                            value=float(v or 0), key=k)
            elif kind == "date":
                out[name] = str(st.date_input(label, value=parse_date(v), key=k,
                                              min_value=date(1950, 1, 1)))
            elif kind == "select":
                opts = list(opts)
                out[name] = st.selectbox(label, opts, index=opts.index(v) if v in opts else 0, key=k)
            elif kind == "textarea":
                out[name] = st.text_area(label, value=str(v or ""), key=k, height=80)
            else:
                out[name] = st.text_input(label, value=str(v or ""), key=k).strip()
    return out


# ---------- lookups ----------
def class_list():
    names = db.load("classes")["class_name"].tolist()
    return names or db.DEFAULT_CLASSES


def class_default_fee(class_name):
    c = db.load("classes")
    m = c[c["class_name"] == class_name]
    return float(m["default_fee"].iloc[0]) if len(m) else 0.0


def person_label(df, id_col):
    """Map id -> 'ID - Name (Class/Subject)' for selectboxes."""
    extra = "class" if "class" in df.columns else "subject"
    return {r[id_col]: "%s - %s (%s)" % (r[id_col], r["name"], r[extra]) for _, r in df.iterrows()}


def whatsapp_link(phone, text):
    digits = re.sub(r"\D", "", str(phone))
    if not digits:
        return None
    if digits.startswith("0"):
        digits = db.get_setting("country_code") + digits[1:]
    return "https://wa.me/%s?text=%s" % (digits, quote(text))


# ---------- downloads ----------
def excel_bytes(sheets):
    buf = BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as w:
        for name, df in sheets.items():
            df.to_excel(w, sheet_name=name[:31], index=False)
    return buf.getvalue()


def download_excel(sheets, filename, label="⬇️ Download Excel", key=None):
    st.download_button(label, excel_bytes(sheets), file_name=filename, key=key,
                       mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")


def receipt_html(title, number, rows, total_label, total_value, note=""):
    """A printable receipt/slip. rows = [(label, value)]."""
    school = html.escape(db.get_setting("school_name"))
    addr = html.escape("  |  ".join(x for x in [db.get_setting("address"), db.get_setting("phone")] if x))
    body = "".join("<tr><td>%s</td><td>%s</td></tr>" % (html.escape(str(a)), html.escape(str(b)))
                   for a, b in rows)
    return """<!doctype html><html><head><meta charset="utf-8"><title>%(title)s %(num)s</title>
<style>
body{font-family:Arial,sans-serif;max-width:520px;margin:24px auto;color:#222}
.box{border:2px solid #333;padding:20px;border-radius:8px}
h1{margin:0;font-size:22px;text-align:center} .addr{text-align:center;font-size:12px;color:#555}
h2{text-align:center;font-size:16px;background:#eee;padding:6px;margin:14px 0}
table{width:100%%;border-collapse:collapse} td{padding:6px;border-bottom:1px solid #ddd}
td:last-child{text-align:right} .total td{font-weight:bold;font-size:16px;border-top:2px solid #333}
.sig{margin-top:40px;display:flex;justify-content:space-between;font-size:12px}
.note{font-size:12px;color:#555;margin-top:10px}
@media print{button{display:none}}
</style></head><body><div class="box">
<h1>%(school)s</h1><div class="addr">%(addr)s</div>
<h2>%(title)s &nbsp;#%(num)s</h2>
<table>%(body)s<tr class="total"><td>%(tl)s</td><td>%(tv)s</td></tr></table>
<div class="note">%(note)s</div>
<div class="sig"><span>Received by: ____________</span><span>Signature: ____________</span></div>
</div><p style="text-align:center"><button onclick="window.print()">🖨️ Print</button></p>
</body></html>""" % {"title": html.escape(title), "num": html.escape(number), "school": school,
                     "addr": addr, "body": body, "tl": html.escape(total_label),
                     "tv": html.escape(total_value), "note": html.escape(note)}


# ---------- login ----------
def _secret_password():
    try:
        return st.secrets.get("ADMIN_PASSWORD")
    except Exception:  # no secrets file
        return None


def check_login():
    if st.session_state.get("auth"):
        return True
    st.markdown("<h1 style='text-align:center'>🏫 %s</h1>" % html.escape(db.get_setting("school_name")),
                unsafe_allow_html=True)
    _, mid, _ = st.columns([1, 1.2, 1])
    with mid:
        with st.form("login"):
            pw = st.text_input("Admin password", type="password")
            if st.form_submit_button("Login", use_container_width=True):
                secret = _secret_password()
                ok = (pw == secret) if secret else (db.hash_pw(pw) == db.get_setting("admin_password_hash"))
                if ok:
                    st.session_state.auth = True
                    st.rerun()
                st.error("Wrong password")
        if not _secret_password() and db.get_setting("admin_password_hash") == db.DEFAULT_SETTINGS["admin_password_hash"]:
            st.info("First time? Default password is **admin123** — change it in Settings.")
    return False
