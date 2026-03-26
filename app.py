import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime

# =========================
# Load data
# =========================
df = pd.read_csv("precooling_historical_dataset_300rows_v2.csv")

# =========================
# Helper functions
# =========================
def get_temp_band(temp):
    if temp >= 35:
        return "High"
    elif temp >= 32:
        return "Medium"
    return "Low"

def calculate_decision(remaining):
    if remaining <= 10:
        return "🔥 Pre-cool now"
    elif remaining <= 30:
        return "⚠️ Prepare"
    else:
        return "⏳ Wait"

# =========================
# UI
# =========================
st.title("🏨 Pre-cooling Prototype")

# -------- Guest Context --------
st.subheader("Guest Context")
customer_type = st.selectbox("Customer Type", ["Solo traveler", "Family"])
age = st.number_input("Age", min_value=30, max_value=40, value=35)
gender = st.selectbox("Gender", ["Male", "Female"])

# -------- Situation Context --------
st.subheader("Situation Context")
day_type = st.selectbox("Day Type", ["Weekday", "Weekend"])
special_event = st.selectbox("Special Event", ["No", "Yes"])
outside_temp = st.number_input("Outside Temperature (°C)", value=32.0)

# -------- Behavior Context --------
st.subheader("Behavior Context")
leave_time_band = st.selectbox(
    "Leave Time Band",
    ["Morning", "Afternoon", "Evening", "Night"]
)

# -------- Timing --------
st.subheader("Room Status")
vacant_since = st.time_input("Vacant Since", value=datetime.now().time())
current_time = st.time_input("Current Time", value=datetime.now().time())

# =========================
# RUN LOGIC
# =========================
if st.button("Run Prediction"):

    temp_band = get_temp_band(outside_temp)

    # =========================
    # Tiered Matching
    # =========================

    # Tier 1
    match = df[
        (df["customer_type"] == customer_type) &
        (df["day_type"] == day_type) &
        (df["leave_time_band"] == leave_time_band) &
        (df["temp_band"] == temp_band) &
        (df["gender"] == gender)
    ]

    tier = "Tier 1"

    # Tier 2 fallback
    if len(match) < 5:
        match = df[
            (df["customer_type"] == customer_type) &
            (df["day_type"] == day_type) &
            (df["leave_time_band"] == leave_time_band) &
            (df["temp_band"] == temp_band)
        ]
        tier = "Tier 2"

    # Tier 3 fallback
    if len(match) < 5:
        match = df[
            (df["customer_type"] == customer_type) &
            (df["day_type"] == day_type) &
            (df["leave_time_band"] == leave_time_band)
        ]
        tier = "Tier 3"

    # =========================
    # Handle no data
    # =========================
    if len(match) < 3:
        st.error("❗ Not enough data — manual review required")
    else:
        # =========================
        # Calculate metrics
        # =========================
        median = int(match["time_away_mins"].median())
        p25 = int(match["time_away_mins"].quantile(0.25))
        p75 = int(match["time_away_mins"].quantile(0.75))

        # =========================
        # Compute time
        # =========================
        vac = datetime.combine(datetime.today(), vacant_since)
        now = datetime.combine(datetime.today(), current_time)

        current_duration = int((now - vac).total_seconds() / 60)
        remaining = median - current_duration

        decision = calculate_decision(remaining)

        # =========================
        # Behavior distribution
        # =========================
        pattern = (
            match["scenario"]
            .value_counts(normalize=True)
            .head(3)
            .round(2)
        )

        # =========================
        # OUTPUT
        # =========================
        st.subheader("📊 Recommendation")

        st.markdown(f"## {decision}")

        st.write(f"**Expected Duration:** {median} mins")
        st.write(f"**Remaining Time:** {remaining} mins")
        st.write(f"**Confidence Level:** {'High' if len(match)>20 else 'Medium'}")

        st.divider()

        st.subheader("🧠 Reason")
        st.write(f"Based on {len(match)} similar cases ({tier})")
        st.write(f"{customer_type} · {day_type} · {leave_time_band} · {temp_band}")

        st.divider()

        st.subheader("📈 Distribution")
        st.write(f"P25: {p25} mins")
        st.write(f"Median: {median} mins")
        st.write(f"P75: {p75} mins")

        st.divider()

        st.subheader("🔥 Top Behavior Pattern")

        for i, (k, v) in enumerate(pattern.items()):
            st.write(f"{int(v*100)}% {k.replace('_',' ').title()}")
