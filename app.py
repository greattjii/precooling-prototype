import streamlit as st
import pandas as pd
from datetime import datetime

# -----------------------
# LOAD DATA
# -----------------------
df = pd.read_csv("precooling_historical_dataset_300rows_v2.csv")

# -----------------------
# TITLE
# -----------------------
st.title("🏨 Pre-cooling Decision Support")

# -----------------------
# INPUTS
# -----------------------
st.subheader("Guest Context")

customer_type = st.selectbox("Customer Type", ["Solo traveler", "Family"])
age = st.number_input("Age", 30, 40, 35)
gender = st.selectbox("Gender", ["Male", "Female"])
day_type = st.selectbox("Day Type", ["Weekday", "Weekend"])

st.subheader("Environment")
current_temp = st.number_input("Current Temperature (°C)", 18.0, 40.0, 30.0)

st.subheader("Room Status")
vacant_since_str = st.time_input("Guest Left At")

# auto current time
current_time = datetime.now()
st.write("**Current Time:**", current_time.strftime("%I:%M %p"))

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

def get_leave_time_band(dt):
    hour = dt.hour
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

def calculate_decision(elapsed: int, remaining: int) -> str:
    if remaining < 0:
        return "Manual review"
    elif remaining <= 10:
        return "Pre-cool now"
    elif remaining <= 30:
        return "Prepare for pre-cooling"
    return "Wait"

def format_time(dt_obj):
    return dt_obj.strftime("%I:%M %p").lstrip("0")

def get_behavior_explanation(match_df, elapsed, median):
    if "scenario" not in match_df.columns:
        return "Top behavior patterns: not available"

    pattern = (
        match_df["scenario"]
        .value_counts(normalize=True)
        .head(3)
        .round(2)
    )

    if len(pattern) == 0:
        return "Top behavior patterns: not available"

    # If overdue → avoid misleading "quick nap"
    if elapsed > median:
        return (
            "Historical data suggests shorter return patterns, "
            "but the current room has already been vacant longer than expected."
        )

    short_patterns = {"quick_nap", "quick_return"}

    if elapsed > 180:
        pattern = pattern[~pattern.index.isin(short_patterns)]

    if len(pattern) == 0:
        return "Top behavior patterns: mixed behavior observed"

    formatted = [
        f"{int(v*100)}% {k.replace('_',' ').title()}"
        for k, v in pattern.items()
    ]

    return "Top behavior patterns: " + " · ".join(formatted)

# -----------------------
# MAIN LOGIC
# -----------------------
if run:

    vac = datetime.combine(datetime.today(), vacant_since_str)
    now = current_time

    # handle overnight
    if now < vac:
        st.warning("Assuming current time is next day.")
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
        st.error("No matching data found.")
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

        decision = calculate_decision(elapsed, remaining)

        spread = p75 - p25
        if tier == "Tier 1" and len(match) >= 15 and spread <= 180:
            confidence = "High"
        elif len(match) >= 8:
            confidence = "Medium"
        else:
            confidence = "Low"

        # -----------------------
        # OUTPUT
        # -----------------------
        st.subheader("📊 Output")

        st.write(f"**Expected Return Time:** {format_time(expected_return_dt)}")
        st.write(f"**Confidence Level:** {confidence}")
        st.write(f"**Recommended Action:** {decision}")

        # -----------------------
        # WHY
        # -----------------------
        st.divider()
        st.subheader("🧠 Why this result")

        st.write(f"Based on **{len(match)} similar cases**")
        st.write(f"Confidence basis: **{get_tier_label(tier)}**")

        st.write(
            f"Matched scenario: **{customer_type} · {day_type} · {leave_time_band} · {current_temp:.1f}°C ({temp_band})**"
        )

        st.write(f"Median return duration: **{median} mins**")
        st.write(f"Expected return time: **{format_time(expected_return_dt)}**")
        st.write(f"Current time: **{format_time(now)}**")

        st.write("Typical return window:")
        st.write(f"- 25% return before **{format_time(vac + pd.Timedelta(minutes=p25))}**")
        st.write(f"- 75% return before **{format_time(vac + pd.Timedelta(minutes=p75))}**")

        if remaining < 0:
            st.write(
                "Interpretation: The expected return time has already passed. "
                "This case may not follow the typical pattern, so manual review is recommended."
            )
        elif remaining <= 10:
            st.write("Interpretation: Guest likely returning very soon → start pre-cooling now.")
        elif remaining <= 30:
            st.write("Interpretation: Guest returning soon → prepare for pre-cooling.")
        else:
            st.write("Interpretation: Return is still far → no action needed yet.")

        st.write(get_behavior_explanation(match, elapsed, median))
