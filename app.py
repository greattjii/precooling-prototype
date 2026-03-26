import streamlit as st
import pandas as pd
from datetime import datetime

# -----------------------
# PAGE CONFIG
# -----------------------
st.set_page_config(page_title="Pre-cooling Decision Support", page_icon="🏨", layout="centered")

# -----------------------
# LOAD DATA
# -----------------------
df = pd.read_csv("precooling_historical_dataset_300rows_v2.csv")

# -----------------------
# TITLE
# -----------------------
st.title("🏨 Pre-cooling Decision Support")
st.caption("Rules-based prototype for estimating guest return timing and pre-cooling action.")

# -----------------------
# INPUTS
# -----------------------
st.subheader("Guest Context")

customer_type = st.selectbox("Customer Type", ["Solo traveler", "Family"])
age = st.number_input("Age", min_value=30, max_value=40, value=35)
gender = st.selectbox("Gender", ["Male", "Female"])
day_type = st.selectbox("Day Type", ["Weekday", "Weekend"])

st.subheader("Environment")
current_temp = st.number_input(
    "Current Temperature (°C)",
    min_value=18.0,
    max_value=40.0,
    value=30.0,
    step=0.5
)

st.subheader("Room Status")
guest_left_at = st.time_input("Guest Left At")

use_custom_time = st.checkbox("Adjust current time (for simulation)")

if use_custom_time:
    current_time_input = st.time_input("Set Current Time")
    current_time = datetime.combine(datetime.today(), current_time_input)
else:
    current_time = datetime.now()

st.write("**Current Time:**", current_time.strftime("%I:%M %p").lstrip("0"))
st.caption("Use simulation mode to test different time scenarios.")

run = st.button("Run Prediction")

# -----------------------
# HELPER FUNCTIONS
# -----------------------
def map_temp_band(temp: float) -> str:
    if temp >= 35:
        return "High"
    elif temp >= 32:
        return "Medium"
    return "Low"

def get_leave_time_band(dt_obj: datetime) -> str:
    hour = dt_obj.hour
    if 6 <= hour < 12:
        return "Morning"
    elif 12 <= hour < 17:
        return "Afternoon"
    elif 17 <= hour < 21:
        return "Evening"
    return "Night"

def get_tier_label(tier: str) -> str:
    if tier == "Tier 1":
        return "Exact match (high confidence)"
    elif tier == "Tier 2":
        return "Partial match (moderate confidence)"
    return "Broad pattern (lower confidence)"

def calculate_decision(remaining: int) -> str:
    if remaining < 0:
        return "Manual review"
    elif remaining <= 10:
        return "Pre-cool now"
    elif remaining <= 30:
        return "Prepare for pre-cooling"
    return "Wait"

def format_time(dt_obj: datetime) -> str:
    return dt_obj.strftime("%I:%M %p").lstrip("0")

def get_behavior_explanation(match_df: pd.DataFrame, elapsed: int, median: int) -> str:
    if "scenario" not in match_df.columns or len(match_df) == 0:
        return "Top behavior patterns: not available"

    pattern = (
        match_df["scenario"]
        .value_counts(normalize=True)
        .head(3)
        .round(2)
    )

    if len(pattern) == 0:
        return "Top behavior patterns: not available"

    if elapsed > median:
        return (
            "Historical data suggests shorter return patterns, but the current room has already "
            "been vacant longer than the typical return duration."
        )

    short_patterns = {"quick_nap", "quick_return"}

    if elapsed > 180:
        pattern = pattern[~pattern.index.isin(short_patterns)]

    if len(pattern) == 0:
        return "Top behavior patterns: mixed behavior observed"

    formatted = [f"{int(v * 100)}% {k.replace('_', ' ').title()}" for k, v in pattern.items()]
    return "Top behavior patterns: " + " · ".join(formatted)

# -----------------------
# MAIN LOGIC
# -----------------------
if run:
    vac = datetime.combine(datetime.today(), guest_left_at)
    now = current_time

    if now < vac:
        st.warning("Assuming Current Time is on the next day.")
        now = now + pd.Timedelta(days=1)

    leave_time_band = get_leave_time_band(vac)
    temp_band = map_temp_band(current_temp)

    # -----------------------
    # MATCHING
    # -----------------------
    match = df[
        (df["customer_type"] == customer_type) &
        (df["day_type"] == day_type) &
        (df["leave_time_band"] == leave_time_band) &
        (df["temp_band"] == temp_band) &
        (df["age"].between(30, 40))
    ]
    tier = "Tier 1"

    if len(match) < 5:
        match = df[
            (df["customer_type"] == customer_type) &
            (df["day_type"] == day_type) &
            (df["leave_time_band"] == leave_time_band)
        ]
        tier = "Tier 2"

    if len(match) < 5:
        match = df[
            (df["customer_type"] == customer_type) &
            (df["day_type"] == day_type)
        ]
        tier = "Tier 3"

    if len(match) == 0:
        st.error("No matching historical data found.")
    else:
        # -----------------------
        # CALCULATION
        # -----------------------
        median = int(match["time_away_mins"].median())
        p25 = int(match["time_away_mins"].quantile(0.25))
        p75 = int(match["time_away_mins"].quantile(0.75))

        elapsed = int((now - vac).total_seconds() / 60)
        remaining = median - elapsed

        expected_return_dt = vac + pd.Timedelta(minutes=median)
        decision = calculate_decision(remaining)

        spread = p75 - p25
        if tier == "Tier 1" and len(match) >= 15 and spread <= 180:
            confidence = "High"
        elif len(match) >= 8:
            confidence = "Medium"
        else:
            confidence = "Low"

        tier_label = get_tier_label(tier)
        behavior_explanation = get_behavior_explanation(match, elapsed, median)

        # -----------------------
        # OUTPUT
        # -----------------------
        st.subheader("📊 Output")
        st.write(f"**Expected Return Time:** {format_time(expected_return_dt)}")
        st.write(f"**Confidence Level:** {confidence}")
        st.write(f"**Recommended Action:** {decision}")

        if remaining < 0:
            st.info(
                "Verify if the guest has returned (e.g., door sensor, keycard activity, or front desk). "
                "Do not trigger pre-cooling automatically."
            )

        # -----------------------
        # WHY THIS RESULT
        # -----------------------
        st.divider()
        st.subheader("🧠 Why this result")

        st.write(f"Based on **{len(match)} similar cases**")
        st.write(f"Confidence basis: **{tier_label}**")
        st.write(
            f"Matched scenario: **{customer_type} · {day_type} · {leave_time_band} · {current_temp:.1f}°C ({temp_band})**"
        )
        st.write(f"Median return duration: **{median} mins**")
        st.write(f"Expected return time: **{format_time(expected_return_dt)}**")
        st.write(f"Current time: **{format_time(now)}**")

        st.write("Typical return window:")
        st.write(f"- 25% of guests return before **{format_time(vac + pd.Timedelta(minutes=p25))}**")
        st.write(f"- 75% of guests return before **{format_time(vac + pd.Timedelta(minutes=p75))}**")

        if remaining < 0:
            st.write(
                "Interpretation: The expected return time has already passed. "
                "This case may not follow the typical historical pattern, so automatic pre-cooling is not recommended."
            )
        elif remaining <= 10:
            st.write(
                "Interpretation: The guest is likely to return very soon, so pre-cooling should start now."
            )
        elif remaining <= 30:
            st.write(
                "Interpretation: The guest is likely to return soon, so the room should be prepared for pre-cooling."
            )
        else:
            st.write(
                "Interpretation: The expected return window is still far enough away that immediate pre-cooling is not needed yet."
            )

        st.write(behavior_explanation)
