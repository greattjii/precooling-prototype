# Pre-Cooling Logic Prototype

A simple Streamlit prototype for the AltoTech hotel energy management assignment.

## What it demonstrates

This prototype simulates a rules-based pre-cooling decision support tool for hotel rooms.

It accepts the following main inputs:

* customer type
* age
* gender
* day type
* current temperature
* guest left at

It also uses:

* current time (auto-generated, with optional simulation override)

The system uses historical records from the dataset to produce:

* expected return time
* confidence level
* recommended action
* a short explanation of why the system made that recommendation

## How it works

The app looks for similar historical records using:

* customer type
* day type
* derived leave time band
* derived temperature band
* age range

If there are too few matching rows, it gradually relaxes the matching rule using a tiered approach.

The prototype then:

* estimates expected return time using the median historical time-away duration
* compares that estimate with the current room status
* recommends whether to wait, prepare for pre-cooling, pre-cool now, or verify whether the guest has already returned

## Run locally

```bash
pip install -r requirements.txt
streamlit run app.py
```

## Deploy free on Streamlit Community Cloud

Create a GitHub repository and upload these files:

* app.py
* requirements.txt
* precooling_historical_dataset_300rows_v2.csv

Then:

* go to Streamlit Community Cloud
* create a new app from your GitHub repo
* set the main file path to `app.py`

## Assumptions

* This is a simple rules / pattern prototype, not a production model
* Recommendation is based on historical matching and current room timing context
* Confidence is based on match quality, sample size, and spread of historical return duration
* Leave time band and temperature band are derived internally from user input

## Limitations

* Uses simplified matching and median-based logic
* Uses a static historical CSV dataset as the data source
* Not connected to live sensors, PMS, keycard systems, or HVAC systems
* Behavior patterns are approximations based on mock historical data
