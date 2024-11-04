# Simple Sonarr and Radarr script created by Matt (MattDGTL) Pomales to clean out stalled downloads.
# Coulnd't find a python script to do this job so I figured why not give it a try.

import os
from dotenv import load_dotenv
import asyncio
import requests
from requests.exceptions import RequestException
import logging
import datetime

# Set up logging to write to a file
logging.basicConfig(
    format='%(asctime)s [%(levelname)s]: %(message)s',
    level=logging.INFO,
    handlers=[
        logging.FileHandler("app.log"),  # Specify the log file
        logging.StreamHandler()  # Optional: StreamHandler for when running with python
    ]
)

# Radarr API endpoint and key
RADARR_API_URL = "http://localhost:7878/api/v3"
load_dotenv()
RADARR_API_KEY = os.getenv('RADARR_API_KEY')
API_TIMEOUT = 3600

# Function to make API requests with error handling
async def make_api_request(url, api_key, params=None):
    try:
        headers = {'X-Api-Key': api_key}
        response = await asyncio.get_event_loop().run_in_executor(None, lambda: requests.get(url, params=params, headers=headers))
        response.raise_for_status()
        return response.json()
    except RequestException as e:
        logging.error(f'Error making API request to {url}: {e}')
        return None
    except ValueError as e:
        logging.error(f'Error parsing JSON response from {url}: {e}')
        return None

# Function to make API delete with error handling
async def make_api_delete(url, api_key, params=None):
    logging.info(f'Deleting {url}')
    # try:
    #     headers = {'X-Api-Key': api_key}
    #     response = await asyncio.get_event_loop().run_in_executor(None, lambda: requests.delete(url, params=params, headers=headers))
    #     response.raise_for_status()
    #     return response.json()
    # except RequestException as e:
    #     logging.error(f'Error making API request to {url}: {e}')
    #     return None
    # except ValueError as e:
    #     logging.error(f'Error parsing JSON response from {url}: {e}')
    #     return None

def parse_timeleft(timeleft):
    days, rest = timeleft.split('.', 1)
    hours, rest = rest.split(':', 1)
    minutes, seconds = rest.split(':', 1)
    return datetime.timedelta(days=int(days), hours=int(hours), minutes=int(minutes), seconds=int(seconds))

stalled_downloads = {}

async def remove_stalled_radarr_downloads():
    global stalled_downloads
    logging.info('Checking radarr queue...')
    radarr_url = f'{RADARR_API_URL}/queue'
    radarr_queue = await make_api_request(radarr_url, RADARR_API_KEY, {'page': '1', 'pageSize': await count_records(RADARR_API_URL,RADARR_API_KEY)})
    if radarr_queue is not None and 'records' in radarr_queue:
        logging.info('Processing Radarr queue...')
        for item in radarr_queue['records']:
            logging.info('')
            logging.info(f'{item["title"]}')
            logging.info(f'is being checked')
            if item['id'] not in stalled_downloads:
                create_default_record(item)
            
            current_stalled_status = download_is_stalled(item) or download_has_not_moved(item)
            logging.info(f'current stalled status: {current_stalled_status}')
            
            prev_stalled_status = stalled_downloads.get(item['id'], {}).get('prev_stalled_status')
            logging.info(f'previous stalled status: {prev_stalled_status}')
            
            was_stalled_on_last_check = stalled_downloads.get(item['id'], {}).get('was_stalled_on_last_check')
            logging.info(f'was stalled on last check: {was_stalled_on_last_check}')
            
            
            if current_stalled_status and prev_stalled_status and was_stalled_on_last_check:
                logging.info(f'has been stalled twice in a row')
                logging.info(f'would be deleted')
                # make_api_delete(f'{RADARR_API_URL}/queue/{item["id"]}', RADARR_API_KEY, {'removeFromClient': 'true', 'blocklist': 'true'})
            else:  
                stalled_downloads[item['id']] = {
                    'prev_stalled_status': current_stalled_status,
                    'was_stalled_on_last_check': prev_stalled_status,
                    'timedelta': parse_timeleft(item['timeleft']) if 'timeleft' in item else None
                }
          
    else:
        logging.warning('Radarr queue is None or missing "records" key')
        
def create_default_record(item):
    stalled_downloads[item['id']] = {'prev_timeleft': None, 'prev_stalled_status': False, 'was_stalled_on_last_check': False}   
        
def download_is_stalled(item):
    # logging.info(f'{item["title"]} for stalled status')
    logging.info(f'is being checked for stalled status')
    if item['status'] == 'warning' and item['errorMessage'] == 'The download is stalled with no connections':
        # logging.info(f'{item["title"]}')
        return True
    else:
        # logging.info(f'{item["title"]}')
        return False

def download_has_not_moved(item):
    # logging.info(f'{item["title"]}')
    logging.info(f'is being checked for movement')
    if 'timeleft' in item:
        # logging.info(f'{item["title"]}')
        # logging.info(f'timeleft is: {item["timeleft"]}')
        
        timedelta = parse_timeleft(item['timeleft'])
        
        # logging.info(f'{item["title"]}')
        
        # prev_timedelta = stalled_downloads[item['id']]['timedelta']
        prev_timedelta = stalled_downloads.get(item['id'], {}).get('timedelta')
        current_timedelta = timedelta
        logging.info(f'timedelta is: {timedelta}')
        logging.info(f'prev timedelta is: {prev_timedelta}')
        if prev_timedelta is None:
            # logging.info(f'{item["title"]}')
            logging.info(f'has no previous timedelta')
            return False
        if current_timedelta >= prev_timedelta:
            # logging.info(f'{item["title"]}')
            logging.info(f'ETA is going up or is stagnant')
            return True
        logging.info(f'ETA is going down')
        return False
    else:
        # logging.info(f'{item["title"]}')
        logging.info(f'does not have a timeleft key')
        return True
    pass
    
# Make a request to view and count items in queue and return the number.
async def count_records(API_URL, API_Key):
    the_url = f'{API_URL}/queue'
    the_queue = await make_api_request(the_url, API_Key)
    if the_queue is not None and 'records' in the_queue:
        return the_queue['totalRecords']

# Main function
async def main():
    while True:
        logging.info('\nRunning media-tools script')
        await remove_stalled_radarr_downloads()
        # logging.info(f'API_TIMEOUT is {API_TIMEOUT}')
        minutes = int(API_TIMEOUT / 60)
        logging.info(f'')
        logging.info(f'Finished running media-tools script. Sleeping for {minutes} minutes.')
        logging.info(f'')
        await asyncio.sleep(API_TIMEOUT)

if __name__ == '__main__':
    loop = asyncio.new_event_loop()  # Create a new event loop
    asyncio.set_event_loop(loop)     # Set it as the current event loop
    loop.run_until_complete(main())
