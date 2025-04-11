from flask import Flask, request, jsonify
import pytz
import requests
from logger import logger, LOGGING_CONFIG
import json
import time
import threading
import os
from datetime import datetime, timedelta
from collections import defaultdict
import pandas as pd

list_flag_exit2 = {}

# Initialize Flask app
app = Flask(__name__)

G_FIXED_MULTIPLE = 10

api_all_keys = {"a1b2c345-6def-789g-hijk-123456789lmn": "paper",    # execute the order on all paper accounts. 
                "z9y8x765-4wvu-321t-rqpo-987654321abc": "real"}     # execute the order on all real accounts.

api_keys = {
    "fb7c1234-25ae-48b6-9f7f-9b3f98d76543": {"id":"ryanoakes-real", "opend-address":"34.71.74.2"}, 
    "a9f8f651-4d3e-46f1-8d6b-c2f1f3b76429": {"id":"ryanoakes-paper", "opend-address":"34.71.74.2"}, 
    "7d4f8a12-1b3c-45e9-9b1a-2a6e0fc2e975": {"id":"enlixir-real", "opend-address":"34.73.25.174"},
    "d45a6e79-927b-4f3e-889d-3c65a8f0738c": {"id":"enlixir-paper", "opend-address":"34.73.25.174"}
    }

def get_codename(symbol, datetmp, option_value, strikeprice, roundingprice, fixed_multiple, order_tag):
    if order_tag == 0 or order_tag == 1:
        bid_price = strikeprice + (roundingprice * fixed_multiple) if option_value == "call" else strikeprice - (roundingprice * fixed_multiple)
    elif order_tag > 1:
        bid_price = strikeprice
    else:
        return ""

    option_code = "C" if option_value == "call" else "P" if option_value == "put" else ""
    
    if not option_code:
        return ""

    return f"US.{symbol}{datetmp[2:]}{option_code}{bid_price}000"

def format_option_ticker(symbol, expiry_date, option_type, strike_price):
    """Format the option ticker symbol for Polygon API"""
    exp_date = datetime.strptime(expiry_date, '%Y%m%d')
    formatted_date = exp_date.strftime('%y%m%d')
    formatted_strike = f"{float(strike_price):05.0f}"
    option_code = "C" if option_type == "call" else "P" if option_type == "put" else ""
    return f"O:{symbol}{formatted_date}{option_code}{formatted_strike}000"

def fetch_latest_minute(symbol, expiry_date, option_type, strike_price, bar_size):
    BASE_URL = "https://api.polygon.io/v2/aggs/ticker"
    API_KEY = "_gClIMBNzOb6jgnPTg4_xvQ08RSnKELi"
    """Fetch the latest minute of data from Polygon"""
    now = datetime.now(pytz.timezone('America/New_York'))
    """
    end_timestamp = int(now.timestamp() * 1000)  # Convert to milliseconds
    start_timestamp = end_timestamp - (60 * 1000)  # One minute ago in milliseconds
    
    url = f"{self.BASE_URL}/{self.format_option_ticker()}/range/1/minute/{start_timestamp}/{end_timestamp}"
    """
    end_date = now.strftime('%Y-%m-%d')
    
    url = f"{BASE_URL}/{format_option_ticker(symbol, expiry_date, option_type, strike_price)}/range/{bar_size}/minute/{end_date}/{end_date}"
    logger.info(f"[-] fetch_latest_minute: url: {url}")
    params = {
        "adjusted": "true",
        "sort": "asc",
        "apiKey": API_KEY
    }
    
    try:
        response = requests.get(url, params=params)
        if response.status_code == 200:
            data = response.json()
            # logger.info(f"[-] fetch_latest_minute: data: {data}")
            if 'results' not in data:
                logger.error(f"[-] fetch_latest_minute: No results in response data")
                return None
            new_data = data.get('results', [])
            last_bar = new_data[-1]
            converted_bar = {
                'timestamp': pd.to_datetime(last_bar['t'], unit='ms'),
                'open': last_bar['o'],
                'high': last_bar['h'],
                'low': last_bar['l'],
                'close': last_bar['c'],
                'volume': last_bar['v'],
                'vw': last_bar['vw']
            }
            
            logger.info(f"[-] fetch_latest_minute: converted_bar: {converted_bar}")
            return converted_bar
        else:
            logger.error(f"Error response: {response.status_code} - {response.text}")
        return None
    except Exception as e:
        logger.error(f"[-] fetch_latest_minute: Error fetching data: {str(e)}")
        return None

def order_send(order, api_key):
    try:
        logger.info(f"[-] order_send: order: {order}")
        opend_address = "http://" + api_keys[api_key]["opend-address"]
        headers = {"Content-Type": "application/json", "api-key": api_key}
        response = requests.post(opend_address, json=order, headers=headers)
        response.raise_for_status()
        response_json = response.json()
        return response_json
    except Exception as e:
        logger.error(f"[-] order_send: error {e} : {order}")
        return None

def thread_engin4_long(symbol, expiry_date, option_type, strike_price, vwap_column, stop_loss_percentage, reverse_exit, max_positions, reverse_entry, use_exit3, api_key, bar_size, mininum_entry_price, order_type):
    """Main loop to run the live trading engine"""
    global list_flag_exit2
    option = "P" if option_type == "put" else "C"
    list_index = symbol + option + api_key
    logger.info(f"[-] thread_engin4_long: Starting live trading for {format_option_ticker(symbol, expiry_date, option_type, strike_price)}")
    
    # Trading state variables
    long_positions = []  # List of (entry_close, entry_open) tuples
    first_long_entry_open = 0.0  # Track first entry open price for Exit1
    long_pending_entry = False
    engine_orders = []

    # Fetch and process latest minute data
    now = datetime.now(pytz.timezone('America/New_York'))
    next_bar_time = now + timedelta(minutes=bar_size)
    previous_bar = fetch_latest_minute(symbol, expiry_date, option_type, strike_price, bar_size)
    
    try:
        while True:
            while True:
                now = datetime.now(pytz.timezone('America/New_York'))
                if now >= next_bar_time:
                    break
                time.sleep(1)
            
            logger.info(f"[-] thread_engin4_long: now: {now}, next_bar_time: {next_bar_time}")
            
            next_bar_time = now + timedelta(minutes=bar_size)
            
            # Fetch and process latest minute data
            current_bar = fetch_latest_minute(symbol, expiry_date, option_type, strike_price, bar_size)
            
            # Update equity for open positions
            if long_positions:
                avg_entry_price = sum(pos[0] for pos in long_positions) / len(long_positions)
                current_bar['Long_Equity'] = (current_bar['close'] - avg_entry_price) * len(long_positions)
            
            flag_exit3 = False
            # Check for Exit3 conditions
            if use_exit3:
                if long_positions:
                    if not reverse_exit:
                        avg_entry_price = sum(pos[0] for pos in long_positions) / len(long_positions)
                        if current_bar['close'] < avg_entry_price * (1 - stop_loss_percentage):
                            flag_exit3 = True
                    else:
                        avg_entry_price = sum(pos[0] for pos in long_positions) / len(long_positions)
                        if current_bar['close'] > avg_entry_price * (1 + stop_loss_percentage):
                            flag_exit3 = True
            if flag_exit3:
                for order in engine_orders:
                    order['side'] = 'SELL'
                    order_send(order, api_key)
                engine_orders = []
                long_positions = []
                first_long_entry_open = 0.0
                long_pending_entry = False
                continue

            # Execute pending long entry at current bar's open if signal was given in previous bar
            if long_pending_entry and len(long_positions) < max_positions:
                order = {
                    "symbol": get_codename(symbol, expiry_date, option_type, strike_price, 0, 0, 100),
                    "quantity": 1,
                    "side": "BUY",
                    "type": order_type,
                    "api_key": api_key
                }
                order_send(order, api_key)
                engine_orders.append(order)
                long_positions.append((current_bar['open'], current_bar['close']))
                avg_entry_price = sum(pos[0] for pos in long_positions) / len(long_positions)
                current_bar['Long_Equity'] = (current_bar['close'] - avg_entry_price) * len(long_positions)
                if not first_long_entry_open:
                    first_long_entry_open = previous_bar['open']
                current_bar['Long_Entry_Price'] = current_bar['open']
                long_pending_entry = False

            # Entry conditions using selected VWAP
            if not reverse_entry:
                is_bull_bar = current_bar['close'] > current_bar['open'] and current_bar['close'] > current_bar[vwap_column]
            else:
                is_bull_bar = current_bar['close'] < current_bar['open'] and current_bar['close'] < current_bar[vwap_column]
            
            if mininum_entry_price == 0 or current_bar['close'] > mininum_entry_price:
                if len(long_positions) < max_positions and is_bull_bar:
                    long_pending_entry = True

            #if now.hour == 15 and now.minute >= 50 and flag_exit2 == False:
            if list_index in list_flag_exit2 and list_flag_exit2[list_index] == True:
                del list_flag_exit2[list_index]
                
                # Handle Exit2 (last bar)
                if long_positions:
                    for order in engine_orders:
                        order['side'] = 'SELL'
                        order_send(order, api_key)
                    break

            previous_bar = current_bar
            
    except Exception as e:
        logger.error(f"[-] thread_engin4_long: error: {e}")

def get_bid_price(code_name, api_key):
    opend_address = "http://" + api_keys[api_key]["opend-address"]
    headers = {"Content-Type": "application/json", "api-key": api_key}
    json_params = {"symbol": code_name}
    while True:
        try:
            response = requests.post(opend_address + "/get_bid_price", json=json_params, headers=headers)
            response.raise_for_status()
            response_json = response.json()

            try:
                json_object_order_list = json.loads(response_json)
                return json_object_order_list['bid_price']
            except Exception as e:
                logger.error(f"[-] get_bid_price: error: {e}")
                time.sleep(2)
                continue

        except requests.exceptions.RequestException as e:
            logger.error(f"[-] get_bid_price: error: {e}")
            time.sleep(2)
            continue

def get_ask_price(code_name, api_key):
    opend_address = "http://" + api_keys[api_key]["opend-address"]
    headers = {"Content-Type": "application/json", "api-key": api_key}
    json_params = {"symbol": code_name}
    while True:
        try:
            response = requests.post(opend_address + "/get_bid_price", json=json_params, headers=headers)
            response.raise_for_status()
            response_json = response.json()

            try:
                json_object_order_list = json.loads(response_json)
                return json_object_order_list['bid_price']
            except Exception as e:
                logger.error(f"[-] get_bid_price: error: {e}")
                time.sleep(2)
                continue

        except requests.exceptions.RequestException as e:
            logger.error(f"[-] get_bid_price: error: {e}")
            time.sleep(2)
            continue

def exit_positions(data, symbol, action, api_key):
    global list_flag_exit2

    logger.info(f"[-] exit_positions: data: {data}, symbol: {symbol}, action: {action}, api_key: {api_key}")

    option = "C" if action == "exit_calls" else "P" if action == "exit_puts" else None
    if not option:
        logger.error(f"[-] exit_positions: Invalid exit action: {data}")
        return jsonify({"error": "Invalid exit action"}), 403

    list_index = symbol + option + api_key 
    list_flag_exit2[list_index] = True
    
    return jsonify({"success": "Exited positions"}), 200

def forward_order1(data, api_key):
    if api_key not in api_keys:
        logger.error(f"Invalid API key: {api_key}")
        return jsonify({"error": "Invalid API key"}), 403

    action = data.get("action")
    symbol = data.get("symbol", "")
    ordertag = int(data.get("order_tag", -1))

    if action and symbol:
        return exit_positions(data, symbol, action, api_key)

    # Extract relevant order data
    datetmp = data.get('date', '')
    option_value = data.get("option", '')
    roundingprice = int(data.get("RoundingPrice", 0))
    stopLossLevel = int(data.get("StopLossLevel", 0))
    pips = int(data.get("Pips", 0))
    delay = int(data.get("Delay", 0))
    side = data.get("side", '')
    bar_size = data.get("BarSize", "")
    order_type = data.get("type", "")

    multiple_value = G_FIXED_MULTIPLE
    if stopLossLevel:
        multiple_value = stopLossLevel
    
    try:
        strikeprice = int(data.get("strikeprice", ''))
    except ValueError:
        logger.error("Invalid strike price")
        return jsonify({"error": "Invalid strike price"}), 400

    if ordertag == -1:
        logger.error("Missing order tag")
        return jsonify({"error": "Missing order tag"}), 400
    
    if ordertag == 1 and not all([datetmp, symbol, roundingprice, pips, delay]):
        logger.error("Missing or invalid fields in request")
        return jsonify({"error": "Missing or invalid fields"}), 400
    
    if ordertag > 1 and not all([datetmp, symbol]):
        logger.error("Missing or invalid fields in request")
        return jsonify({"error": "Missing or invalid fields"}), 400
    
    buy_code_name = get_codename(symbol, datetmp, option_value, strikeprice, roundingprice, multiple_value, ordertag)
    if not buy_code_name:
        logger.error("Invalid option type")
        return jsonify({"error": "Invalid option type"}), 400

    if bar_size.find("m") != -1:
        bar_size = bar_size.replace("m", "")
        bar_size = int(bar_size)
        vwap_column = data.get("Restriction", "")
        stop_loss_percentage = float(data.get("Exit3Percent", 0.0))
        reverse_exit = data.get("ExitReverse", "")
        reverse_exit = True if reverse_exit == "y" else False
        max_positions = int(data.get("MaxPositions", 0))
        reverse_entry = data.get("EntryReverse", "")
        reverse_entry = True if reverse_entry == "y" else False
        use_exit3 = data.get("Exit3", "")
        use_exit3 = True if use_exit3 == "y" else False
        mininum_entry_price = float(data.get("MinimumEntryPrice", 0))
        logger.info("[-] forward_order1: starting a thread - thread_engin4_long")
        threading.Thread(target=thread_engin4_long, args=(symbol, datetmp, option_value, strikeprice, vwap_column, stop_loss_percentage, reverse_exit, max_positions, reverse_entry, use_exit3, api_key, bar_size, mininum_entry_price, order_type)).start()
        
        return jsonify({"success": "Order forwarded"}), 200
    
    return jsonify({"fail", "Invalid BarSize"}), 200

@app.route("/", methods=["POST"])
def forward_order():
    data = request.json
    api_key = data.get("api_key")
    if not api_key:
        logger.error(f"Missing API key: {data}")
        return jsonify({"error": "Missing API key"}), 403
    
    ordertag = data.get("order_tag")
    if not ordertag:
        logger.error(f"Missing order_tag: {data}")
        return jsonify({"error": "Missing order_tag"}), 403
    
    logger.info(f"request data: {data}")

    if api_key in api_all_keys:
        for api_key_1, api_info in api_keys.items():
            if api_info["id"].find(api_all_keys[api_key]) != -1:
                forward_order1(data, api_key_1)
    else:
        return forward_order1(data, api_key)
    
    return jsonify({"success": "Order forwarded"}), 200

@app.route("/list_orders", methods=["GET"])
def list_orders():
    api_key = request.args.get("api_key")
    if not api_key:
        logger.error(f"Missing API key: {request}")
        return jsonify({"error": "Missing API key"}), 403
    
    if not api_key in api_keys:
        logger.error(f"Invalid API key: {api_key}")
        return jsonify({"error": "Invalid API key"}), 403

    headers = {"Content-Type": "application/json", "api-key": api_key}
    opend_address = "http://" + api_keys[api_key]["opend-address"]

    try:
        response = requests.post(opend_address + "/order_list/", json=None, headers=headers)
        response.raise_for_status()
        response_json = response.json()

        try:
            json_object = json.loads(response_json)
        except Exception as e:
            logger.error(f"[-] list_orders: error: {e}")
            return jsonify(response_json), response.status_code

        for order in json_object:
            logger.info(f"order: {order}")

        return jsonify(response_json), response.status_code
    except requests.exceptions.RequestException as e:
        logger.error(f"list_orders: error: {e}")
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0")
