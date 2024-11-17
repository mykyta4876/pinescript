import requests
import time
from datetime import datetime
import pytz
from logger import logger, LOGGING_CONFIG

def request_back_end(url):
    headers = {"Content-Type": "application/json"}
    data = {"api_key": "1234567890"}

    try:
        response = requests.post(url, json=data, headers=headers)
        response.raise_for_status()
        response_json = response.json()

        logger.info(f"[-] request_back_end: result= {response_json}")
    except requests.exceptions.RequestException as e:
        logger.error(f"[-] request_back_end: error: {e}")


if __name__ == "__main__":
    while True:
        """
        now_time = datetime.now().astimezone(pytz.timezone('US/Eastern'))
        logger.info(f"now_time: {now_time}")
        
        if now_time.hour < 9:
            logger.info("[-] request_back_end: market not open yet")
            continue

        if now_time.hour == 9 and now_time.minute < 30:
            logger.info("[-] request_back_end: market not open yet")
            continue

        if now_time.hour > 15:
            logger.info("[-] request_back_end: market not open yet")
            continue
        
        if now_time.weekday() >= 5:
            logger.info("[-] request_back_end: market not open yet")
            continue
        """
        
        request_back_end("https://sapiogenics.com/call_thread_exit_orders")
        request_back_end("https://sapiogenic.com/call_thread_exit_orders")
        time.sleep(10)
