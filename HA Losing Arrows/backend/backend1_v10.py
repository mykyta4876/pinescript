from flask import Flask, request, jsonify
import requests
from logger import logger, LOGGING_CONFIG
import json
import time
import threading
from concurrent.futures import ThreadPoolExecutor

# Initialize Flask app
app = Flask(__name__)

# Endpoint of the FastAPI server
FASTAPI_URL = "http://35.224.31.48"
G_FIXED_MULTIPLE = 10

# In-memory store for orders
orders = {}
sell_todo_orders = {}
buy_pending_orders = {}
exit_sell_todo_orders = {}
exit_sell_pending_orders = {}
exit_buy_todo_orders = {}
exit_buy_pending_orders = {}
order_pair_map = {}

executor = ThreadPoolExecutor(max_workers=5)

def get_codename(symbol, datetmp, option_value, strikeprice, roundingprice, fixed_multiple):
    bid_price = strikeprice + (roundingprice * fixed_multiple) if option_value == "call" else strikeprice - (roundingprice * fixed_multiple)
    option_code = "C" if option_value == "call" else "P" if option_value == "put" else ""
    
    if not option_code:
        return ""

    return f"US.{symbol}{datetmp[2:]}{option_code}{bid_price}000"

def thread_exit_orders():
    while True:
        processed_list = []
        for order_id, order in exit_sell_todo_orders.items():
            logger.info(f"Exiting Order: ID: {order_id}, Details: {order}")
            order['side'] = "BUY"

            try:
                response = requests.post(FASTAPI_URL, json=order, headers=headers)
                response.raise_for_status()
                response_json = response.json()
                time.sleep(1)

                if "Open position failed" in str(response_json):
                    logger.error(f"[-] thread_exit_orders: SELL: Open position failed: {response_json}")
                    continue

                try:
                    json_object = json.loads(response_json)
                except Exception as e:
                    logger.error(f"[-] thread_exit_orders: SELL: error {e} : {order}")
                    continue

                if "order_id" in json_object[0]:
                    logger.info(f"[-] thread_exit_orders: SELL: Placed the pending exit order of {order_id} successfully. ID: {json_object[0]['order_id']}")
                    processed_list.append(order_id)
                    order_id = json_object[0]['order_id']
                    exit_sell_pending_orders[order_id] = order
                else:
                    logger.error("[-] thread_exit_orders: SELL: Order response missing 'order_id'")

            except requests.exceptions.RequestException as e:
                logger.error(f"[-] thread_exit_orders: SELL: FastAPI request failed: {e}")

        for order_id in processed_list:
            del exit_sell_todo_orders[order_id]

        json_object_order_list = []
        headers = {"Content-Type": "application/json", "api-key": "1125436a-3fb7-5b65-87eb-11zYGrsUz333"}
        while True:
            try:
                response = requests.post(FASTAPI_URL + "/order_list/", json=None, headers=headers)
                response.raise_for_status()
                response_json = response.json()

                try:
                    json_object_order_list = json.loads(response_json)
                    break
                except Exception as e:
                    logger.error(f"[-] thread_exit_orders: order_list: error: {e}")
                    time.sleep(3)
                    continue

            except requests.exceptions.RequestException as e:
                logger.error(f"[-] thread_exit_orders: order_list: error: {e}")
                time.sleep(3)
                continue

        processed_list = []
        for p_order_id, p_order in exit_sell_pending_orders.items():
            for l_order in json_object_order_list:
                if l_order['order_id'] == p_order_id and l_order['order_status'] == "FILLED_ALL":

                    logger.info(f"[-] thread_exit_orders: SELL: {p_order_id} is FILLED_ALL")
                    
                    processed_list.append(p_order_id)

        for order_id in processed_list:
            del exit_sell_pending_orders[order_id]
            if order_id in exit_sell_todo_orders:
                del exit_sell_todo_orders[order_id]

        processed_list = []
        for order_id, order in exit_buy_todo_orders.items():
            if order_id in order_pair_map:
                exit_sell_order_id = order_pair_map[order_id]
                if exit_sell_order_id in exit_sell_pending_orders:
                    continue
                
                if exit_sell_order_id in exit_sell_todo_orders:
                    continue

            logger.info(f"[-] thread_exit_orders: BUY: Exiting Order: ID: {order_id}, Details: {order}")
            order['side'] = "SELL"

            try:
                response = requests.post(FASTAPI_URL, json=order, headers=headers)
                response.raise_for_status()
                response_json = response.json()
                time.sleep(1)

                if "Open position failed" in str(response_json):
                    logger.error(f"[-] thread_exit_orders: BUY: Open position failed: {response_json}")
                    continue

                try:
                    json_object = json.loads(response_json)
                except Exception as e:
                    logger.error(f"[-] thread_exit_orders: BUY: error {e} : {order}")
                    continue

                if "order_id" in json_object[0]:
                    logger.info(f"[-] thread_exit_orders: BUY: Placed the pending exit order of {order_id} successfully. ID: {json_object[0]['order_id']}")
                    processed_list.append(order_id)
                    order_id = json_object[0]['order_id']
                    exit_buy_pending_orders[order_id] = order
                else:
                    logger.error("[-] thread_exit_orders: BUY: Order response missing 'order_id'")
            except requests.exceptions.RequestException as e:
                logger.error(f"[-] thread_exit_orders: BUY: FastAPI request failed: {e}")

        for order_id in processed_list:
            del exit_buy_todo_orders[order_id]

        processed_list = []
        for p_order_id, p_order in exit_buy_pending_orders.items():
            for l_order in json_object_order_list:
                if l_order['order_id'] == p_order_id and l_order['order_status'] == "FILLED_ALL":

                    logger.info(f"[-] thread_exit_orders: BUY: {p_order_id} is FILLED_ALL")
                    
                    processed_list.append(p_order_id)

        for order_id in processed_list:
            del exit_buy_pending_orders[order_id]
            if order_id in exit_buy_todo_orders:
                del exit_buy_todo_orders[order_id]

        time.sleep(10)
def exit_positions(data, symbol, action, api_key):
    option = "C" if action == "exit_calls" else "P" if action == "exit_puts" else None
    if not option:
        logger.error(f"[-] exit_positions: Invalid exit action: {data}")
        return jsonify({"error": "Invalid exit action"}), 403

    headers = {"Content-Type": "application/json", "api-key": api_key}
    base_symbol = symbol

    sell_selected_items = {
        order_id: order for order_id, order in orders.items()
        if order['symbol'].startswith(f'US.{base_symbol}') and order['symbol'][9 + len(base_symbol)] == option and order['side'] == "SELL"
    }

    if len(sell_selected_items) == 0:
        return jsonify({"success": "Exited positions"}), 200

    for order_id, order in sell_selected_items.items():
        del orders[order_id]
        exit_sell_todo_orders[order_id] = order
    
    buy_to_exit_orders = {
        order_id: order for order_id, order in orders.items()
        if order['symbol'].startswith(f'US.{base_symbol}') and order['symbol'][9 + len(base_symbol)] == option and order['side'] == "BUY"
    }
    
    for order_id, order in buy_to_exit_orders.items():
        del orders[order_id]
        exit_buy_todo_orders[order_id] = order
    
    return jsonify({"success": "Exited positions"}), 200

@app.route("/", methods=["POST"])
def forward_order():
    data = request.json
    api_key = data.get("api_key")
    if not api_key:
        logger.error(f"Missing API key: {data}")
        return jsonify({"error": "Missing API key"}), 403

    logger.info(f"request data: {data}")

    action = data.get("action")
    symbol = data.get("symbol", "")

    if action and symbol:
        return exit_positions(data, symbol, action, api_key)

    # Extract relevant order data
    datetmp = data.get('date', '')
    option_value = data.get("option", '')
    roundingprice = int(data.get("RoundingPrice", 0))
    side = data.get("side", '')

    if side != "SELL" or not all([datetmp, symbol, roundingprice]):
        logger.error("Missing or invalid fields in request")
        return jsonify({"error": "Missing or invalid fields"}), 400

    try:
        strikeprice = int(data.get("strikeprice", ''))
    except ValueError:
        logger.error("Invalid strike price")
        return jsonify({"error": "Invalid strike price"}), 400

    buy_code_name = get_codename(symbol, datetmp, option_value, strikeprice, roundingprice, G_FIXED_MULTIPLE)
    if not buy_code_name:
        logger.error("Invalid option type")
        return jsonify({"error": "Invalid option type"}), 400

    buy_order_data = {
        "symbol": buy_code_name,
        "quantity": data.get("quantity"),
        "side": "BUY",
        "type": data.get("type"),
    }

    headers = {"Content-Type": "application/json", "api-key": api_key}

    # Function to retry buy order with reduced multiple
    def retry_buy_order(fixed_multiple):
        if fixed_multiple < G_FIXED_MULTIPLE - 2:
            return jsonify({"error": "Buy order failed after 3 attempts"}), 500

        code_name = get_codename(symbol, datetmp, option_value, strikeprice, roundingprice, fixed_multiple)
        if not code_name:
            return jsonify({"error": "Invalid option type"}), 400

        buy_order_data["symbol"] = code_name
        try:
            response = requests.post(FASTAPI_URL, json=buy_order_data, headers=headers)
            response.raise_for_status()
            response_json = response.json()

            if "Open position failed" in str(response_json):
                logger.error(f"Open position failed: {response_json} : {code_name} : {fixed_multiple}")
                return retry_buy_order(fixed_multiple - 1)

            try:
                json_object = json.loads(response_json)
            except Exception as e:
                logger.error(f"[-] forward_order: error {e} : {code_name} : {fixed_multiple}")
                return retry_buy_order(fixed_multiple - 1)

            order_id = json_object[0]["order_id"]
            buy_pending_orders[order_id] = buy_order_data

            # Now send the original sell order
            sell_code_name = get_codename(symbol, datetmp, option_value, strikeprice, roundingprice, 0)
            sell_order_data = {
                "symbol": sell_code_name,
                "quantity": data.get("quantity"),
                "side": "SELL",
                "type": data.get("type"),
            }

            sell_todo_orders[order_id] = sell_order_data
            logger.info(f"Buy pending order placed. Order ID: {order_id} : {code_name} : {fixed_multiple}")
            return response_json, response.status_code
        except requests.exceptions.RequestException as e:
            logger.error(f"Buy order failed: {e} : {code_name}")
            return jsonify({"error": str(e)}), 500

    buy_response_json, buy_response_status = retry_buy_order(G_FIXED_MULTIPLE)

    return buy_response_json, buy_response_status

@app.route("/saved_orders", methods=["GET"])
def get_orders():
    global orders
    """Endpoint to retrieve all placed orders"""
    return jsonify(orders)

def sell_order():
    headers = {"Content-Type": "application/json", "api-key": "1125436a-3fb7-5b65-87eb-11zYGrsUz333"}
    logger.info(f"sell_order: start")

    while True:
        time.sleep(10)

        if len(sell_todo_orders) == 0:
            continue
        try:
            response = requests.post(FASTAPI_URL + "/order_list/", json=None, headers=headers)
            response.raise_for_status()
            response_json = response.json()

            try:
                json_object = json.loads(response_json)
            except Exception as e:
                logger.error(f"[-] list_orders: error: {e}")
                continue

            processed_list = []
            for p_order_id, p_order in sell_todo_orders.items():
                for l_order in json_object:
                    if l_order['order_id'] == p_order_id and l_order['order_status'] == "FILLED_ALL":
                        logger.error(f"[-] sell_order: {p_order_id} is FILLED_ALL")
                        
                        try:
                            sell_response = requests.post(FASTAPI_URL, json=p_order, headers=headers)
                            sell_response.raise_for_status()
                            sell_response_json = sell_response.json()

                            try:
                                sell_json_object = json.loads(sell_response_json)
                            except Exception as e:
                                logger.error(f"[-] sell_order: error {e} : sell order of {p_order_id}")
                                break

                            order_id = sell_json_object[0]["order_id"]
                            orders[p_order_id] = buy_pending_orders[p_order_id]
                            orders[order_id] = p_order
                            order_pair_map[p_order_id] = order_id
                            processed_list.append(p_order_id)

                            logger.info(f"[-] sell_order: Sell order placed. Order ID: {order_id} : sell order of {p_order_id}")
                            break
                        except requests.exceptions.RequestException as e:
                            logger.error(f"[-] sell_order: Sell order failed: {e} : sell order of {p_order_id}")
                            break

            for order_id in processed_list:
                del sell_todo_orders[order_id]
                del buy_pending_orders[order_id]

        except requests.exceptions.RequestException as e:
            logger.error(f"sell_order: RequestException: {e}")
            continue
        except Exception as e:
            logger.error(f"sell_order: error: {e}")
            continue

    return

@app.route("/list_orders", methods=["GET"])
def list_orders():
    headers = {"Content-Type": "application/json", "api-key": "1125436a-3fb7-5b65-87eb-11zYGrsUz333"}

    try:
        response = requests.post(FASTAPI_URL + "/order_list/", json=None, headers=headers)
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

def init_background_tasks():
    executor.submit(sell_order)
    executor.submit(thread_exit_orders)

if __name__ == "__main__":
    app.run(host="0.0.0.0")
    init_background_tasks()
