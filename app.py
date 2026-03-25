import math
from datetime import datetime, timedelta, time
from pathlib import Path

import openpyxl
import pandas as pd
import streamlit as st

st.set_page_config(page_title="Pre-Cooling Logic Prototype", page_icon="🏨", layout="centered")

APP_DIR = Path(__file__).resolve().parent
DEFAULT_XLSX = APP_DIR / "Prototype (1).xlsx"


def time_to_minutes(t):
    if pd.isna(t) or t is None:
        return None
    if isinstance(t, datetime):
        return t.hour * 60 + t.minute
    if isinstance(t, time):
        return t.hour * 60 + t.minute
    return None


def minutes_to_clock_str(m):
    m = int(round(m)) % (24 * 60)
    h = m // 60
    mins = m % 60
    return f"{h:02d}:{mins:02d}"


def circular_diff(a, b):
    """Difference between two clock times in minutes."""
    d = abs(a - b) % (24 * 60)
    return min(d, 24 * 60 - d)


def temp_band(temp):
    if temp >= 35:
        return "Very High"
    if temp >= 32:
        return "High"
    if temp >= 28:
        return "Medium"
    return "Low"


def age_band(age):
    if age < 30:
        return "Under 30"
    if age <= 45:
        return "30-45"
    return "46+"


def circular_median(values):
    # good enough for a simple prototype: choose existing value with lowest total circular distance
    best = None
    best_score = None
    for candidate in values:
        score = sum(circular_diff(candidate, v) for v in values)
        if best_score is None or score < best_score:
            best_score = score
            best = candidate
    return best


@st.cache_data
def load_record_data(xlsx_path: Path):
    wb = openpyxl.load_workbook(xlsx_path, data_only=True)
    ws = wb["Record"]
    rows = list(ws.values)
    headers = rows[0]
    df = pd.DataFrame(rows[1:], columns=headers)

    # Normalize columns used by the prototype
    df = df.rename(
        columns={
            "Customer type": "customer_type",
            "Gender": "gender",
            "Age": "age",
            "Return time": "return_time",
            "Return time Outside temperature": "outside_temp",
            "Leave time": "leave_time",
        }
    )

    df = df[["customer_type", "gender", "age", "return_time", "outside_temp", "leave_time"]].copy()
    df = df.dropna(subset=["customer_type", "gender", "age", "return_time", "outside_temp"])
    df["age_band"] = df["age"].apply(age_band)
    df["temp_band"] = df["outside_temp"].apply(temp_band)
    df["return_mins"] = df["return_time"].apply(time_to_minutes)
    df["leave_mins"] = df["leave_time"].apply(time_to_minutes)
    return df.dropna(subset=["return_mins"])


def find_matches(df, customer_type, outside_temp, gender, age):
    tb = temp_band(outside_temp)
    ab = age_band(age)

    # strict -> fallback hierarchy
    groups = [
        ("High", df[(df.customer_type == customer_type) & (df.gender == gender) & (df.age_band == ab) & (df.temp_band == tb)]),
        ("Medium", df[(df.customer_type == customer_type) & (df.age_band == ab) & (df.temp_band == tb)]),
        ("Medium", df[(df.customer_type == customer_type) & (df.temp_band == tb)]),
        ("Low", df[(df.customer_type == customer_type)]),
    ]
    for level, subset in groups:
        if len(subset) >= 3:
            return level, subset, tb, ab
    # fallback to all data from same temp band, then all rows
    subset = df[df.temp_band == tb]
    if len(subset) >= 3:
        return "Low", subset, tb, ab
    return "Low", df, tb, ab


def build_result(df, customer_type, outside_temp, gender, age, current_dt):
    confidence, matched, tb, ab = find_matches(df, customer_type, outside_temp, gender, age)
    values = matched["return_mins"].tolist()
    median_return = circular_median(values)

    # for recommendation, compare predicted comeback clock time vs current time
    now_mins = current_dt.hour * 60 + current_dt.minute
    delta = (median_return - now_mins) % (24 * 60)

    if confidence == "Low" and len(matched) < 5:
        recommendation = "Manual review"
    elif delta <= 10:
        recommendation = "Pre-cool now"
    elif delta <= 30:
        recommendation = "Prepare / monitor"
    else:
        recommendation = "Wait"

    reason = (
        f"Used {len(matched)} historical record(s) with a similar pattern. "
        f"Primary match: customer type = {customer_type}, temp band = {tb}. "
        f"Age band = {ab}, gender = {gender}."
    )

    return {
        "predicted_return": minutes_to_clock_str(median_return),
        "confidence": confidence,
        "recommendation": recommendation,
        "reason": reason,
        "sample_size": len(matched),
        "temp_band": tb,
        "age_band": ab,
        "matched": matched.sort_values(["return_mins"]).copy(),
    }


st.title("🏨 Pre-Cooling Logic Prototype")
st.caption("Simple prototype for AltoTech hotel engineer workflow")

with st.sidebar:
    st.header("Data source")
    uploaded = st.file_uploader("Upload Prototype (1).xlsx", type=["xlsx"])
    xlsx_path = None
    if uploaded is not None:
        temp_path = APP_DIR / "uploaded_prototype.xlsx"
        temp_path.write_bytes(uploaded.read())
        xlsx_path = temp_path
        st.success("Using uploaded workbook")
    elif DEFAULT_XLSX.exists():
        xlsx_path = DEFAULT_XLSX
        st.info("Using bundled sample workbook")
    else:
        st.error("Please upload the workbook first.")

if xlsx_path is None:
    st.stop()

record_df = load_record_data(xlsx_path)

st.subheader("Input")
col1, col2 = st.columns(2)
with col1:
    customer_type = st.selectbox(
        "Customer type",
        sorted(record_df["customer_type"].dropna().unique().tolist()),
    )
    outside_temp = st.number_input("Outside temperature (°C)", min_value=20.0, max_value=45.0, value=32.0, step=0.5)
with col2:
    gender = st.selectbox("Gender", sorted(record_df["gender"].dropna().unique().tolist()))
    age = st.number_input("Age", min_value=18, max_value=90, value=35, step=1)

current_time = st.time_input("Current time (used for recommendation)", value=datetime.now().time())

if st.button("Run prototype", use_container_width=True):
    current_dt = datetime.combine(datetime.today(), current_time)
    result = build_result(record_df, customer_type, outside_temp, gender, age, current_dt)

    st.subheader("Output")
    c1, c2, c3 = st.columns(3)
    c1.metric("Most likely comeback time", result["predicted_return"])
    c2.metric("Confidence level", result["confidence"])
    c3.metric("Recommend option", result["recommendation"])

    st.markdown("### Why this result")
    st.write(result["reason"])

    with st.expander("Show matched historical records"):
        show_cols = ["customer_type", "gender", "age", "age_band", "outside_temp", "temp_band", "leave_time", "return_time"]
        st.dataframe(result["matched"][show_cols], use_container_width=True)

st.markdown("---")
st.markdown(
    "This prototype uses the **Record** sheet as historical data and returns an estimated comeback time, confidence, and a simple pre-cooling recommendation."
)
