import requests
import json

def fetch_financial_data():
    url = "https://api.stlouisfed.org/fred/series/observations"
    params = {
        "series_id": "GDP",
        "api_key": "your_api_key_here",
        "file_type": "json"
    }
    response = requests.get(url, params=params)
    if response.status_code == 200:
        with open("/tmp/gdp_data.json", "w") as f:
            json.dump(response.json(), f)
        print("Data fetched and saved.")
    else:
        print("Failed to fetch data")
