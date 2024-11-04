import requests
import os
from dotenv import load_dotenv
load_dotenv()
import logging

# Set up logging to write to a file
logging.basicConfig(
    format='%(asctime)s [%(levelname)s]: %(message)s',
    level=logging.INFO,
    handlers=[
        logging.FileHandler("test.log"),  # Specify the log file
        logging.StreamHandler()  # Optional: StreamHandler for when running with python
    ]
)

# Replace with your Radarr API key and URL
api_key = os.getenv('RADARR_API_KEY')
radarr_url = "http://localhost:7878"

# Set API endpoint and headers
endpoint = f"{radarr_url}/api/v3/queue"
headers = {"X-Api-Key": api_key}

# Send GET request to queue endpoint
response = requests.get(endpoint, headers=headers)

# Check if response was successful
if response.status_code == 200:
    # Get the records array from the response JSON
    records = response.json()["records"]
    
    # Safely extract timeleft only if it exists
    time_left_values = [record["timeleft"] for record in records if "timeleft" in record]

    # Alternatively, log records without timeleft to debug further if needed
    for record in records:
        if "timeleft" not in record:
            logging.warning(f"Record missing 'timeleft' attribute: {record["title"]}")
        else:
            time_left_values.append(record["timeleft"])

    # Print or log the timeLeft values
    print(time_left_values)
else:
    print(f"Error: {response.status_code}")