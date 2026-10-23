"""Excel-backed storage.

All data lives in a single workbook (data/school_data.xlsx), one sheet per table.
You can open that file in Excel at any time to view or print your records.
"""
import hashlib
import os
import threading
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


def init_db():
    """Create the workbook with empty sheets on first run."""
    os.makedirs(DATA_DIR, exist_ok=True)
    if os.path.exists(DB_PATH):
        return
    sheets = {name: pd.DataFrame(columns=cols) for name, cols in SCHEMA.items()}
    sheets["classes"] = pd.DataFrame({"class_name": DEFAULT_CLASSES, "default_fee": 0})
    sheets["settings"] = pd.DataFrame(list(DEFAULT_SETTINGS.items()), columns=["key", "value"])
    _write_all(sheets)


def _write_all(sheets):
    # Write to a temp file then swap, so a crash never leaves a half-written workbook.
    tmp = os.path.join(DATA_DIR, "school_data.tmp.xlsx")
    with pd.ExcelWriter(tmp, engine="openpyxl") as writer:
        for name, df in sheets.items():
            df.to_excel(writer, sheet_name=name, index=False)
    os.replace(tmp, DB_PATH)


@st.cache_data(show_spinner=False)
def _read_all(path, mtime_ns):
    # mtime_ns is part of the cache key, so any write invalidates the cache.
    return pd.read_excel(path, sheet_name=None, dtype=object, engine="openpyxl")


def load_all():
    raw = _read_all(DB_PATH, os.stat(DB_PATH).st_mtime_ns)
    return {k: v.copy() for k, v in raw.items()}


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
        data = load_all()
        data[name] = _normalize(name, df.copy())
        _write_all(data)


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
    with open(DB_PATH, "rb") as f:
        return f.read()


def restore(file_bytes):
    sheets = pd.read_excel(BytesIO(file_bytes), sheet_name=None, dtype=object, engine="openpyxl")
    missing = [s for s in ("students", "teachers", "fees", "settings") if s not in sheets]
    if missing:
        raise ValueError("This is not a valid backup file. Missing sheets: " + ", ".join(missing))
    with _lock:
        _write_all(sheets)
