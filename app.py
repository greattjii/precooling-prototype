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
leave_time_band = st.selectbox(
    "Leave Time Band",
    ["Morning", "Afternoon", "Evening", "Night"]
)
current_temp = st.number_input("Current Temperature (°C)", 18.0, 40.0, 30.0)

st.subheader("Room Status")
vacant_since_str = st.time_input("Vacant Since")
current_time_str = st.time_input("Current Time", value=datetime.now().time())

run = st.button("Run Prediction")

# -----------------------
# HELPER FUNCTIONS
# -----------------------
def map_temp_band(temp: float) -> str:
    # aligned to dataset: Low < 32, Medium 32-34.9, High >= 35
    if temp >= 35:
        return "High"
    elif temp >= 32:
        return "Medium"
    return "Low"

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

def safe_ampm(dt_obj) -> str:
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

    # If current elapsed time already exceeds typical return duration,
    # avoid surfacing misleading short-return patterns like quick_nap.
    if elapsed > median:
        return (
            "Historical cohort was dominated by shorter-return behavior, "
            "but the current room has already been vacant longer than the typical return duration."
        )

    # Additional plausibility rule: if room has already been vacant for a long time,
    # suppress obviously short-return labels from becoming the main explanation.
    short_patterns = {"quick_nap", "quick_return", "park_pool_break"}
    filtered = pattern[~pattern.index.isin(short_patterns)] if elapsed > 180 else pattern

    if len(filtered) == 0:
        filtered = pattern

    formatted = [f"{int(v * 100)}% {k.replace('_', ' ').title()}" for k, v in filtered.items()]
    return "Top behavior patterns: " + " · ".join(formatted)

# -----------------------
# MAIN LOGIC
# -----------------------
if run:
    temp_band = map_temp_band(current_temp)

    vac = datetime.combine(datetime.today(), vacant_since_str)
    now = datetime.combine(datetime.today(), current_time_str)

    # Handle overnight case
    if now < vac:
        st.warning("Current Time is earlier than Vacant Since, so the app assumes Current Time is on the next day.")
        now = now + pd.Timedelta(days=1)

    # -----------------------
    # MATCHING (tiered)
    # -----------------------
    # Tier 1: exact operational match
    match = df[
        (df["customer_type"] == customer_type) &
        (df["day_type"] == day_type) &
        (df["leave_time_band"] == leave_time_band) &
        (df["temp_band"] == temp_band) &
        (df["age"].between(30, 40))
    ]
    tier = "Tier 1"

    # Tier 2: relax temperature band
    if len(match) < 5:
        match = df[
            (df["customer_type"] == customer_type) &
            (df["day_type"] == day_type) &
            (df["leave_time_band"] == leave_time_band) &
            (df["age"].between(30, 40))
        ]
        tier = "Tier 2"

    # Tier 3: broad pattern
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
        # CALCULATIONS
        # -----------------------
        median = int(match["time_away_mins"].median())
        p25 = int(match["time_away_mins"].quantile(0.25))
        p75 = int(match["time_away_mins"].quantile(0.75))

        elapsed = int((now - vac).total_seconds() / 60)
        remaining = median - elapsed  # allow negative for overdue logic

        expected_return_dt = vac + pd.Timedelta(minutes=median)
        expected_return_time = safe_ampm(expected_return_dt)
        p25_time = safe_ampm(vac + pd.Timedelta(minutes=p25))
        p75_time = safe_ampm(vac + pd.Timedelta(minutes=p75))
        current_time_display = safe_ampm(now)

        decision = calculate_decision(elapsed, remaining)

        spread = p75 - p25
        if tier == "Tier 1" and len(match) >= 15 and spread <= 180:
            confidence = "High"
        elif len(match) >= 8 and spread <= 300:
            confidence = "Medium"
        else:
            confidence = "Low"

        tier_label = get_tier_label(tier)
        behavior_explanation = get_behavior_explanation(match, elapsed, median)

        # -----------------------
        # OUTPUT
        # -----------------------
        st.subheader("📊 Output")
        st.write(f"**Expected Return Time:** {expected_return_time}")
        st.write(f"**Confidence Level:** {confidence}")
        st.write(f"**Recommended Action:** {decision}")

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
        st.write(f"Expected return time: **{expected_return_time}**")
        st.write(f"Current time: **{current_time_display}**")

        st.write("Typical return window:")
        st.write(f"- 25% of guests return before **{p25_time}**")
        st.write(f"- 75% of guests return before **{p75_time}**")

        if remaining < 0:
            st.write(
                "Interpretation: The expected return window has already passed. "
                "This suggests the room may already be occupied or the current case is behaving differently "
                "from the matched historical pattern, so manual review is recommended."
            )
        elif remaining <= 10:
            st.write(
                "Interpretation: The expected return window is very close, so pre-cooling should start now "
                "to reduce the risk of a warm-room experience."
            )
        elif remaining <= 30:
            st.write(
                "Interpretation: The guest is likely to return soon, so the room should be prepared for pre-cooling."
            )
        else:
            st.write(
                "Interpretation: The expected return window is still far enough away that immediate pre-cooling "
                "is not yet necessary."
            )

        st.write(behavior_explanation)
