"""Storage layer.

On Streamlit Cloud the data lives in a Google Sheet (one tab per table), so it survives
restarts. This is used when `gcp_service_account` and `spreadsheet_url` are set in secrets.
Without those secrets (e.g. running on your own PC) data lives in data/school_data.xlsx.
"""
import hashlib
import os
import threading
import time
from io import BytesIO

import pandas as pd
import streamlit as st

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
DB_PATH = os.path.join(DATA_DIR, "school_data.xlsx")
_lock = threading.RLock()

SCHEMA = {
    "students": ["student_id", "name", "father_name", "class", "section", "gender", "dob",
                 "phone", "address", "admission_date", "monthly_fee", "status"],
    "teachers": ["teacher_id", "name", "phone", "cnic", "subject", "qualification",
                 "joining_date", "monthly_salary", "status"],
    "classes": ["class_name", "default_fee"],
    "fees": ["receipt_no", "student_id", "student_name", "class", "fee_type", "month",
             "amount_due", "discount", "fine", "amount_paid", "payment_date", "method", "remarks"],
    "salaries": ["slip_no", "teacher_id", "teacher_name", "month", "basic_salary", "bonus",
                 "deduction", "advance", "net_paid", "payment_date", "method", "remarks"],
    "expenses": ["expense_id", "date", "category", "description", "amount", "paid_to"],
    "attendance": ["date", "student_id", "student_name", "class", "status"],
    "settings": ["key", "value"],
}

NUMERIC = {"monthly_fee", "default_fee", "monthly_salary", "amount_due", "discount", "fine",
           "amount_paid", "basic_salary", "bonus", "deduction", "advance", "net_paid", "amount"}

DEFAULT_CLASSES = ["Playgroup", "Nursery", "Prep"] + ["Class %d" % i for i in range(1, 11)]


def hash_pw(pw):
    return hashlib.sha256(pw.encode("utf-8")).hexdigest()


DEFAULT_SETTINGS = {
    "school_name": "My School",
    "address": "",
    "phone": "",
    "currency": "Rs.",
    "country_code": "92",
    "admin_password_hash": hash_pw("admin123"),
}


def _use_sheets():
    try:
        return "gcp_service_account" in st.secrets and "spreadsheet_url" in st.secrets
    except Exception:  # no secrets file
        return False


def init_db():
    """Create empty tables with defaults on first run."""
    if _use_sheets():
        _sheets_init()
        return
    os.makedirs(DATA_DIR, exist_ok=True)
    if os.path.exists(DB_PATH):
        return
    _write_all(_default_tables())


def _default_tables():
    sheets = {name: pd.DataFrame(columns=cols) for name, cols in SCHEMA.items()}
    sheets["classes"] = pd.DataFrame({"class_name": DEFAULT_CLASSES, "default_fee": 0})
    sheets["settings"] = pd.DataFrame(list(DEFAULT_SETTINGS.items()), columns=["key", "value"])
    return sheets


def load_all():
    if _use_sheets():
        raw = _sheets_read_all()
    else:
        raw = _read_all(DB_PATH, os.stat(DB_PATH).st_mtime_ns)
    return {k: v.copy() for k, v in raw.items()}


def _write_all(sheets):
    if _use_sheets():
        for name, df in sheets.items():
            _sheets_write(name, df)
        return
    # Write to a temp file then swap, so a crash never leaves a half-written workbook.
    tmp = os.path.join(DATA_DIR, "school_data.tmp.xlsx")
    with pd.ExcelWriter(tmp, engine="openpyxl") as writer:
        for name, df in sheets.items():
            df.to_excel(writer, sheet_name=name, index=False)
    os.replace(tmp, DB_PATH)


def _write_table(name, df):
    if _use_sheets():
        _sheets_write(name, df)
    else:
        data = load_all()
        data[name] = df
        _write_all(data)


@st.cache_data(show_spinner=False)
def _read_all(path, mtime_ns):
    # mtime_ns is part of the cache key, so any write invalidates the cache.
    return pd.read_excel(path, sheet_name=None, dtype=object, engine="openpyxl")


# ---------- Google Sheets backend ----------

_CACHE_TTL = 30  # seconds; picks up edits made directly in the Google Sheet
_cache = {"data": None, "time": 0.0}
_initialized = False


@st.cache_resource(show_spinner=False)
def _spreadsheet():
    import gspread
    client = gspread.service_account_from_dict(dict(st.secrets["gcp_service_account"]))
    return client.open_by_url(st.secrets["spreadsheet_url"])


def _sheets_init():
    global _initialized
    if _initialized:
        return
    with _lock:
        sh = _spreadsheet()
        existing = [ws.title for ws in sh.worksheets()]
        for name, df in _default_tables().items():
            if name not in existing:
                sh.add_worksheet(title=name, rows=max(len(df) + 1, 2), cols=len(df.columns))
                _sheets_write(name, df)
        # Remove Google's empty starter tab once our tabs exist.
        if "Sheet1" in existing and "Sheet1" not in SCHEMA:
            try:
                sh.del_worksheet(sh.worksheet("Sheet1"))
            except Exception:
                pass
        _cache["data"] = None
        _initialized = True


def _sheets_read_all():
    with _lock:
        if _cache["data"] is not None and time.time() - _cache["time"] < _CACHE_TTL:
            return _cache["data"]
        sh = _spreadsheet()
        names = [ws.title for ws in sh.worksheets()]
        resp = sh.values_batch_get(["'%s'" % n for n in names],
                                   params={"valueRenderOption": "UNFORMATTED_VALUE"})
        data = {}
        for name, vr in zip(names, resp.get("valueRanges", [])):
            rows = vr.get("values", [])
            if not rows:
                data[name] = pd.DataFrame(columns=SCHEMA.get(name, []), dtype=object)
                continue
            header, body = rows[0], rows[1:]
            body = [r + [""] * (len(header) - len(r)) for r in body]
            data[name] = pd.DataFrame([r[:len(header)] for r in body], columns=header, dtype=object)
        _cache["data"], _cache["time"] = data, time.time()
        return data


def _cell(col, v):
    if col in NUMERIC:
        n = pd.to_numeric(v, errors="coerce")
        n = 0.0 if pd.isna(n) else float(n)
        return int(n) if n.is_integer() else n
    return _to_str(v)


def _sheets_write(name, df):
    with _lock:
        cols = list(df.columns)
        values = [cols] + [[_cell(c, v) for c, v in zip(cols, row)]
                           for row in df.itertuples(index=False, name=None)]
        sh = _spreadsheet()
        try:
            ws = sh.worksheet(name)
        except Exception:
            ws = sh.add_worksheet(title=name, rows=len(values), cols=len(cols))
        # Grow first, write, then shrink, so the data is never blank if a step fails.
        if ws.row_count < len(values) or ws.col_count < len(cols):
            ws.resize(rows=max(ws.row_count, len(values)), cols=max(ws.col_count, len(cols)))
        ws.update(values, "A1")
        if ws.row_count > len(values) or ws.col_count > len(cols):
            ws.resize(rows=max(len(values), 2), cols=len(cols))
            if len(values) == 1:
                ws.batch_clear(["A2:%s2" % _col_letter(len(cols))])
        if _cache["data"] is not None:
            _cache["data"][name] = pd.DataFrame(values[1:], columns=cols, dtype=object)


def _col_letter(n):
    s = ""
    while n:
        n, r = divmod(n - 1, 26)
        s = chr(65 + r) + s
    return s


def _to_str(v):
    if v is None:
        return ""
    try:
        if pd.isna(v):
            return ""
    except (TypeError, ValueError):
        pass
    if hasattr(v, "strftime"):
        return v.strftime("%Y-%m-%d")
    if isinstance(v, float) and v.is_integer():
        return str(int(v))
    return str(v).strip()


def _normalize(name, df):
    cols = SCHEMA.get(name, list(df.columns))
    for c in cols:
        if c not in df.columns:
            df[c] = None
    df = df[cols].copy()
    for c in cols:
        if c in NUMERIC:
            df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0.0).astype(float)
        else:
            df[c] = df[c].map(_to_str).astype(str)
    return df.reset_index(drop=True)


def load(name):
    data = load_all()
    df = data.get(name, pd.DataFrame(columns=SCHEMA[name]))
    return _normalize(name, df)


def save(name, df):
    with _lock:
        _write_table(name, _normalize(name, df.copy()))


def append(name, row):
    with _lock:
        df = load(name)
        new = pd.DataFrame([row])
        df = new if df.empty else pd.concat([df, new], ignore_index=True)
        save(name, df)


def next_id(name, col, prefix):
    df = load(name)
    nums = pd.to_numeric(df[col].str.replace(prefix, "", regex=False), errors="coerce").dropna()
    n = int(nums.max()) + 1 if len(nums) else 1
    return "%s%04d" % (prefix, n)


def get_setting(key):
    df = load("settings")
    match = df[df["key"] == key]
    if len(match) and match["value"].iloc[0] != "":
        return match["value"].iloc[0]
    return DEFAULT_SETTINGS.get(key, "")


def set_settings(values):
    df = load("settings")
    for k, v in values.items():
        if (df["key"] == k).any():
            df.loc[df["key"] == k, "value"] = str(v)
        else:
            df = pd.concat([df, pd.DataFrame([{"key": k, "value": str(v)}])], ignore_index=True)
    save("settings", df)


def export_bytes():
    if not _use_sheets():
        with open(DB_PATH, "rb") as f:
            return f.read()
    buf = BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as writer:
        for name, df in load_all().items():
            df = _normalize(name, df) if name in SCHEMA else df
            df.to_excel(writer, sheet_name=name, index=False)
    return buf.getvalue()


def restore(file_bytes):
    sheets = pd.read_excel(BytesIO(file_bytes), sheet_name=None, dtype=object, engine="openpyxl")
    missing = [s for s in ("students", "teachers", "fees", "settings") if s not in sheets]
    if missing:
        raise ValueError("This is not a valid backup file. Missing sheets: " + ", ".join(missing))
    with _lock:
        _write_all({name: _normalize(name, df) if name in SCHEMA else df.fillna("")
                    for name, df in sheets.items()})
