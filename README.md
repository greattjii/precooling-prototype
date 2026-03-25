# Pre-Cooling Logic Prototype

A simple Streamlit prototype for the AltoTech hotel energy management assignment.

## What it demonstrates
- Accepts the same main inputs shown on the Prototype sheet:
  - customer type
  - outside temperature
  - gender
  - age
- Uses historical records from the `Record` sheet
- Produces:
  - most likely comeback time
  - confidence level
  - recommended option
- Shows a short explanation of why the system made that recommendation

## How it works
The app looks for similar historical records using:
1. customer type
2. temperature band
3. age band
4. gender

If there are too few matching rows, it gradually relaxes the matching rule.
Then it calculates a simple median comeback clock time from the matched rows.

## Run locally
```bash
pip install -r requirements.txt
streamlit run app.py
```

## Deploy free on Streamlit Community Cloud
1. Create a GitHub repository
2. Upload these files:
   - `app.py`
   - `requirements.txt`
   - `Prototype (1).xlsx`
3. Go to Streamlit Community Cloud
4. Create a new app from your GitHub repo
5. Set the main file path to `app.py`

## Assumptions
- This is a simple rules / pattern prototype, not a production model
- Recommendation is based on the predicted comeback time versus current time
- Confidence is based on match quality and sample size

## Limitations
- Uses simplified matching and median logic
- Uses one workbook as the historical data source
- Not connected to live sensors, PMS, or HVAC systems
