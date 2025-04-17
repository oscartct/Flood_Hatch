# src/fetch_readings.py

import os
import datetime
import pandas as pd
import requests
import io
import warnings
from requests.packages.urllib3.exceptions import InsecureRequestWarning

# Suppress only the single warning from urllib3 about unverified HTTPS requests
warnings.simplefilter('ignore', InsecureRequestWarning)

def fetch_readings(date_str: str) -> pd.DataFrame:
    """
    Fetch river telemetry readings for a given date from the Environment Agency Flood Monitoring API.
    Uses requests with SSL verification disabled if needed for self-signed certs.
    Returns a DataFrame of readings.
    """
    url = f"https://environment.data.gov.uk/flood-monitoring/data/readings.csv?date={date_str}"
    # Use requests to allow disabling SSL verification
    resp = requests.get(url, verify=False)
    resp.raise_for_status()

    # Read CSV from the response text
    df = pd.read_csv(io.StringIO(resp.text))
    return df


def main():
    # Use the FLOOD_DATE env var or default to today's date
    date_str = os.getenv("FLOOD_DATE", datetime.date.today().isoformat())
    print(f"Fetching telemetry readings for {date_str}...")
    df = fetch_readings(date_str)

    # Ensure raw data directory exists
    os.makedirs("data/raw", exist_ok=True)
    out_fp = os.path.join("data/raw", f"readings_{date_str}.csv")
    df.to_csv(out_fp, index=False)
    print(f"Saved {len(df)} readings to {out_fp}")


if __name__ == "__main__":
    main()

