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
st.subheader("User Input")

customer_type = st.selectbox("Customer Type", ["Solo traveler", "Family"])
age = st.number_input("Age", 30, 40, 35)
gender = st.selectbox("Gender", ["Male", "Female"])
day_type = st.selectbox("Day Type", ["Weekday", "Weekend"])
leave_time_band = st.selectbox("Leave Time", ["Morning", "Afternoon", "Evening", "Late night"])
temp_band = st.selectbox("Temperature Band", ["Low", "Medium", "High"])

st.subheader("Room Status")

vacant_since_str = st.time_input("Vacant Since")
current_time_str = st.time_input("Current Time")

run = st.button("Run Prediction")

# -----------------------
# HELPER FUNCTIONS
# -----------------------
def calculate_decision(remaining):
    if remaining <= 10:
        return "Pre-cool now"
    elif remaining <= 30:
        return "Prepare for pre-cooling"
    else:
        return "Wait"

def get_tier_label(tier):
    if tier == "Tier 1":
        return "Exact match (high confidence)"
    elif tier == "Tier 2":
        return "Partial match (moderate confidence)"
    else:
        return "Broad pattern (lower confidence)"

# -----------------------
# MAIN LOGIC
# -----------------------
if run:

    vac = datetime.combine(datetime.today(), vacant_since_str)
    now = datetime.combine(datetime.today(), current_time_str)

    # -----------------------
    # MATCHING (Tier logic)
    # -----------------------
    match = df[
        (df["customer_type"] == customer_type) &
        (df["day_type"] == day_type) &
        (df["leave_time_band"] == leave_time_band) &
        (df["temp_band"] == temp_band)
    ]
    tier = "Tier 1"

    if len(match) < 5:
        match = df[
            (df["customer_type"] == customer_type) &
            (df["day_type"] == day_type)
        ]
        tier = "Tier 2"

    if len(match) < 5:
        match = df
        tier = "Tier 3"

    # -----------------------
    # CALCULATIONS
    # -----------------------
    median = int(match["time_away_mins"].median())
    p25 = int(match["time_away_mins"].quantile(0.25))
    p75 = int(match["time_away_mins"].quantile(0.75))

    elapsed = int((now - vac).total_seconds() / 60)
    remaining = max(median - elapsed, 0)

    decision = calculate_decision(remaining)

    # Convert to HH:MM
    expected_return_dt = vac + pd.Timedelta(minutes=median)
    expected_return_time = expected_return_dt.strftime("%H:%M")

    p25_time = (vac + pd.Timedelta(minutes=p25)).strftime("%H:%M")
    p75_time = (vac + pd.Timedelta(minutes=p75)).strftime("%H:%M")

    # Confidence logic
    if len(match) > 20:
        confidence = "High"
    elif len(match) > 10:
        confidence = "Medium"
    else:
        confidence = "Low"

    tier_label = get_tier_label(tier)

    # -----------------------
    # OUTPUT (MAIN)
    # -----------------------
    st.subheader("📊 Output")

    st.write(f"**Expected Return Time:** {expected_return_time}")
    st.write(f"**Confidence Level:** {confidence}")
    st.write(f"**Recommended Action:** {decision}")

    # -----------------------
    # SUPPORTING EXPLANATION
    # -----------------------
    st.divider()

    st.subheader("🧠 Why this result")

    st.write(f"Based on **{len(match)} similar cases**")
    st.write(f"Confidence basis: **{tier_label}**")

    st.write(
        f"Matched scenario: **{customer_type} · {day_type} · {leave_time_band} · {temp_band}**"
    )

    st.write(f"Median return duration: **{median} mins**")

    st.write("Typical return window:")
    st.write(f"- 25% of guests return before **{p25_time}**")
    st.write(f"- 75% of guests return before **{p75_time}**")

    # -----------------------
    # BEHAVIOR PATTERN (SAFE)
    # -----------------------
    if "scenario" in match.columns:
        pattern = (
            match["scenario"]
            .value_counts(normalize=True)
            .head(3)
            .round(2)
        )

        if len(pattern) > 0:
            formatted = []
            for k, v in pattern.items():
                formatted.append(f"{int(v*100)}% {k.replace('_',' ').title()}")

            st.write("Top behavior patterns: " + " · ".join(formatted))
    else:
        st.write("Top behavior patterns: not available")
