from flask import Flask, request, jsonify
import pytz
import requests
from logger import logger, LOGGING_CONFIG
import json
import time
import threading
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
# Initialize Flask app
app = Flask(__name__)

# Endpoint of the FastAPI server
FASTAPI_URL = "http://34.123.142.4"
G_FIXED_MULTIPLE = 10

api_all_keys = {"a1b2c345-6def-789g-hijk-123456789lmn": "paper",    # execute the order on all paper accounts. 
                "z9y8x765-4wvu-321t-rqpo-987654321abc": "real"}     # execute the order on all real accounts.

api_keys = {
    "fb7c1234-25ae-48b6-9f7f-9b3f98d76543": {"id":"ryanoakes-real", "opend-address":"34.16.63.166"}, 
    "a9f8f651-4d3e-46f1-8d6b-c2f1f3b76429": {"id":"ryanoakes-paper", "opend-address":"34.16.63.166"}, 
    "7d4f8a12-1b3c-45e9-9b1a-2a6e0fc2e975": {"id":"enlixir-real", "opend-address":"34.123.142.4"}, 
    "d45a6e79-927b-4f3e-889d-3c65a8f0738c": {"id":"enlixir-paper", "opend-address":"34.123.142.4"}
    }

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
    threading.current_thread().name = "thread_exit_orders"
    logger.info(f"[-] thread_exit_orders: start")
    while True:
        now_time = datetime.now().astimezone(pytz.timezone('US/Eastern'))
        if now_time.hour < 9:
            time.sleep(10)
            continue

        if now_time.hour == 9 and now_time.minute < 30:
            time.sleep(10)
            continue

        if now_time.hour > 15:
            time.sleep(10)
            continue

        if now_time.weekday() >= 5:
            time.sleep(10)
            continue

        json_object_order_list = []
        for api_key, api_info in api_keys.items():
            counts = 0
            sell_selected_items = {
                order_id: order for order_id, order in sell_todo_orders.items()
                if order['api_key'] == api_key
            }
            counts += len(sell_selected_items)
            
            sell_selected_items = {
                order_id: order for order_id, order in buy_pending_orders.items()
                if order['api_key'] == api_key
            }
            counts += len(sell_selected_items)
            
            sell_selected_items = {
                order_id: order for order_id, order in exit_sell_todo_orders.items()
                if order['api_key'] == api_key
            }
            counts += len(sell_selected_items)

            sell_selected_items = {
                order_id: order for order_id, order in exit_sell_pending_orders.items()
                if order['api_key'] == api_key
            }
            counts += len(sell_selected_items)

            sell_selected_items = {
                order_id: order for order_id, order in exit_buy_todo_orders.items()
                if order['api_key'] == api_key
            }
            counts += len(sell_selected_items)

            sell_selected_items = {
                order_id: order for order_id, order in exit_buy_pending_orders.items()
                if order['api_key'] == api_key
            }
            counts += len(sell_selected_items)

            if counts == 0:
                logger.info(f"[-] thread_exit_orders: {api_info['id']} has no orders")
                continue

            json_object_order_list = []
            headers = {"Content-Type": "application/json", "api-key": api_key}
            opend_address = "http://" + api_info["opend-address"]
            while True:
                try:
                    response = requests.post(opend_address + "/order_list/", json=None, headers=headers)
                    response.raise_for_status()
                    response_json = response.json()

                    try:
                        json_object_order_list = json.loads(response_json)
                        break
                    except Exception as e:
                        logger.error(f"[-] thread_exit_orders: order_list: error: {e}, acc:{api_info['id']}")
                        time.sleep(3)
                        break

                except requests.exceptions.RequestException as e:
                    logger.error(f"[-] thread_exit_orders: order_list: error: {e}, acc:{api_info['id']}")
                    time.sleep(3)
                    break

            processed_list = []
            for p_order_id, p_order in sell_todo_orders.items():
                p_order_only_id = p_order_id.replace(api_keys[api_key]["id"], "")
                for l_order in json_object_order_list:
                    if l_order['order_id'] == p_order_only_id and l_order['order_status'] == "FILLED_ALL":
                        logger.info(f"[-] sell_order: {p_order_id} is FILLED_ALL")
                        
                        try:
                            sell_response = requests.post(opend_address, json=p_order, headers=headers)
                            sell_response.raise_for_status()
                            sell_response_json = sell_response.json()
                            time.sleep(1)

                            try:
                                sell_json_object = json.loads(sell_response_json)
                            except Exception as e:
                                logger.error(f"[-] sell_order: error: {e}, sell order of {p_order_id}, acc:{api_info['id']}, order:{p_order}")
                                break

                            order_id = sell_json_object[0]["order_id"] + api_keys[api_key]["id"]
                            orders[p_order_id] = buy_pending_orders[p_order_id]
                            orders[order_id] = p_order
                            order_pair_map[p_order_id] = order_id
                            processed_list.append(p_order_id)

                            logger.info(f"[-] sell_order: Sell order placed. Order ID: {order_id}, sell order of {p_order_id}, acc:{api_info['id']}, order:{p_order}")
                            break
                        except requests.exceptions.RequestException as e:
                            logger.error(f"[-] sell_order: Sell order failed: {e}, sell order of {p_order_id}, acc:{api_info['id']}, order:{p_order}")
                            break

            for order_id in processed_list:
                del sell_todo_orders[order_id]
                del buy_pending_orders[order_id]

            processed_list = []
            for order_id, order in exit_sell_todo_orders.items():
                if order["api_key"] != api_key:
                    continue
                logger.info(f"Exiting Order: ID: {order_id}, Details: {order}")
                order['side'] = "BUY"

                try:
                    response = requests.post(opend_address, json=order, headers=headers)
                    response.raise_for_status()
                    response_json = response.json()
                    time.sleep(1)

                    if "Open position failed" in str(response_json):
                        logger.error(f"[-] thread_exit_orders: SELL: Open position failed: {response_json}, acc:{api_info['id']}, order:{order}")
                        continue

                    try:
                        json_object = json.loads(response_json)
                    except Exception as e:
                        logger.error(f"[-] thread_exit_orders: SELL: error: {e}, acc:{api_info['id']}, order:{order}")
                        continue

                    if "order_id" in json_object[0]:
                        logger.info(f"[-] thread_exit_orders: SELL: Placed the pending exit order of {order_id} successfully. ID: {json_object[0]['order_id']}, acc:{api_info['id']}, order:{order}")
                        processed_list.append(order_id)
                        order_id = json_object[0]['order_id'] + api_keys[api_key]["id"]
                        exit_sell_pending_orders[order_id] = order
                    else:
                        logger.error(f"[-] thread_exit_orders: SELL: Order response missing 'order_id', acc:{api_info['id']}, order:{order}")

                except requests.exceptions.RequestException as e:
                    logger.error(f"[-] thread_exit_orders: SELL: FastAPI request failed: {e}, acc:{api_info['id']}, order:{order}")

            for order_id in processed_list:
                del exit_sell_todo_orders[order_id]

            processed_list = []
            for p_order_id, p_order in exit_sell_pending_orders.items():
                p_order_only_id = p_order_id.replace(api_keys[api_key]["id"], "")
                for l_order in json_object_order_list:
                    if l_order['order_id'] == p_order_only_id and l_order['order_status'] == "FILLED_ALL":
                        logger.info(f"[-] thread_exit_orders: SELL: {p_order_id} is FILLED_ALL, acc:{api_info['id']}, order:{p_order}")
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

                logger.info(f"[-] thread_exit_orders: BUY: Exiting Order: ID: {order_id}, Details: {order}, acc:{api_info['id']}")
                order['side'] = "SELL"

                try:
                    response = requests.post(opend_address, json=order, headers=headers)
                    response.raise_for_status()
                    response_json = response.json()
                    time.sleep(1)

                    if "Open position failed" in str(response_json):
                        logger.error(f"[-] thread_exit_orders: BUY: Open position failed: {response_json}")
                        continue

                    try:
                        json_object = json.loads(response_json)
                    except Exception as e:
                        logger.error(f"[-] thread_exit_orders: BUY: error {e}, acc:{api_info['id']}, order:{order}")
                        continue

                    if "order_id" in json_object[0]:
                        logger.info(f"[-] thread_exit_orders: BUY: Placed the pending exit order of {order_id} successfully. ID: {json_object[0]['order_id']}")
                        processed_list.append(order_id)
                        order_id = json_object[0]['order_id'] + api_keys[api_key]["id"]
                        exit_buy_pending_orders[order_id] = order
                    else:
                        logger.error(f"[-] thread_exit_orders: BUY: Order response missing 'order_id', acc:{api_info['id']}, order:{order}")
                except requests.exceptions.RequestException as e:
                    logger.error(f"[-] thread_exit_orders: BUY: FastAPI request failed: {e}, acc:{api_info['id']}, order:{order}")

            for order_id in processed_list:
                del exit_buy_todo_orders[order_id]

            processed_list = []
            for p_order_id, p_order in exit_buy_pending_orders.items():
                p_order_only_id = p_order_id.replace(api_keys[api_key]["id"], "")
                for l_order in json_object_order_list:
                    if l_order['order_id'] == p_order_only_id and l_order['order_status'] == "FILLED_ALL":

                        logger.info(f"[-] thread_exit_orders: BUY: {p_order_id} is FILLED_ALL, acc:{api_info['id']}, order:{p_order}")
                        
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

    base_symbol = symbol

    sell_selected_items = {
        order_id: order for order_id, order in orders.items()
        if order['symbol'].startswith(f'US.{base_symbol}') and order['symbol'][9 + len(base_symbol)] == option and order['side'] == "SELL" and order['api_key'] == api_key
    }

    if len(sell_selected_items) == 0:
        return jsonify({"success": "Exited positions"}), 200

    for order_id, order in sell_selected_items.items():
        del orders[order_id]
        exit_sell_todo_orders[order_id] = order
    
    buy_to_exit_orders = {
        order_id: order for order_id, order in orders.items()
        if order['symbol'].startswith(f'US.{base_symbol}') and order['symbol'][9 + len(base_symbol)] == option and order['side'] == "BUY" and order['api_key'] == api_key
    }
    
    for order_id, order in buy_to_exit_orders.items():
        del orders[order_id]
        exit_buy_todo_orders[order_id] = order
    
    return jsonify({"success": "Exited positions"}), 200

def forward_order1(data, api_key):      
    if api_key not in api_keys:
        logger.error(f"Invalid API key: {api_key}")
        return jsonify({"error": "Invalid API key"}), 403

    action = data.get("action")
    symbol = data.get("symbol", "")

    if action and symbol:
        return exit_positions(data, symbol, action, api_key)

    # Extract relevant order data
    datetmp = data.get('date', '')
    option_value = data.get("option", '')
    roundingprice = int(data.get("RoundingPrice", 0))
    stopLossLevel = int(data.get("StopLossLevel", 0))
    side = data.get("side", '')
    
    multiple_value = G_FIXED_MULTIPLE
    if stopLossLevel:
        multiple_value = stopLossLevel
    

    if side != "SELL" or not all([datetmp, symbol, roundingprice]):
        logger.error("Missing or invalid fields in request")
        return jsonify({"error": "Missing or invalid fields"}), 400

    try:
        strikeprice = int(data.get("strikeprice", ''))
    except ValueError:
        logger.error("Invalid strike price")
        return jsonify({"error": "Invalid strike price"}), 400

    buy_code_name = get_codename(symbol, datetmp, option_value, strikeprice, roundingprice, multiple_value)
    if not buy_code_name:
        logger.error("Invalid option type")
        return jsonify({"error": "Invalid option type"}), 400

    buy_order_data = {
        "symbol": buy_code_name,
        "quantity": data.get("quantity"),
        "side": "BUY",
        "type": data.get("type"),
        "api_key": api_key,
    }

    headers = {"Content-Type": "application/json", "api-key": api_key}

    # Function to retry buy order with reduced multiple
    def retry_buy_order(fixed_multiple):
        if fixed_multiple < multiple_value - 2:
            logger.error("Buy order failed after 3 attempts")
            return jsonify({"error": "Buy order failed after 3 attempts"}), 500

        code_name = get_codename(symbol, datetmp, option_value, strikeprice, roundingprice, fixed_multiple)
        if not code_name:
            logger.error("Invalid option type")
            return jsonify({"error": "Invalid option type"}), 400

        buy_order_data["symbol"] = code_name
        try:
            fastapi_url = "http://" + api_keys[api_key]["opend-address"]
            response = requests.post(fastapi_url, json=buy_order_data, headers=headers)
            response.raise_for_status()
            response_json = response.json()
            time.sleep(1)

            if "Open position failed" in str(response_json):
                logger.error(f"Open position failed: {response_json} : {code_name} : {fixed_multiple}")
                return retry_buy_order(fixed_multiple - 1)

            try:
                json_object = json.loads(response_json)
            except Exception as e:
                logger.error(f"[-] forward_order: error {e} : {code_name} : {fixed_multiple}")
                return retry_buy_order(fixed_multiple - 1)

            order_id = json_object[0]["order_id"] + api_keys[api_key]["id"]
            buy_pending_orders[order_id] = buy_order_data

            # Now send the original sell order
            sell_code_name = get_codename(symbol, datetmp, option_value, strikeprice, roundingprice, 0)
            sell_order_data = {
                "symbol": sell_code_name,
                "quantity": data.get("quantity"),
                "side": "SELL",
                "type": data.get("type"),
                "api_key": api_key,
            }

            sell_todo_orders[order_id] = sell_order_data
            logger.info(f"Buy pending order placed. Order ID: {order_id} : {code_name} : {fixed_multiple}")
            return response_json, response.status_code
        except requests.exceptions.RequestException as e:
            logger.error(f"Buy order failed: {e} : {code_name}")
            return jsonify({"error": str(e)}), 500

    buy_response_json, buy_response_status = retry_buy_order(multiple_value)

    return buy_response_json, buy_response_status


@app.route("/", methods=["POST"])
def forward_order():
    data = request.json
    api_key = data.get("api_key")
    if not api_key:
        logger.error(f"Missing API key: {data}")
        return jsonify({"error": "Missing API key"}), 403
    
    logger.info(f"request data: {data}")

    if check_thread_status() == False:
        logger.error("forward_order: thread_exit_orders is not running")
        executor.submit(thread_exit_orders)
        logger.info("forward_order: thread_exit_orders started again")

    if api_key in api_all_keys:
        for api_key_1, api_info in api_keys.items():
            if api_info["id"].find(api_all_keys[api_key]) != -1:
                forward_order1(data, api_key_1)
    else:
        return forward_order1(data, api_key)
    
    return jsonify({"success": "Order forwarded"}), 200
          
@app.route("/saved_orders", methods=["GET"])
def get_orders():
    global orders
    """Endpoint to retrieve all placed orders"""
    return jsonify(orders)

@app.route("/list_orders", methods=["GET"])
def list_orders():
    headers = {"Content-Type": "application/json", "api-key": "d45a6e79-927b-4f3e-889d-3c65a8f0738c"}

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


@app.route("/list_memory_orders", methods=["GET"])
def list_memory_orders():
    memory_orders = {}
    memory_orders['buy_pending_orders'] = buy_pending_orders
    memory_orders['exit_sell_todo_orders'] = exit_sell_todo_orders
    memory_orders['exit_sell_pending_orders'] = exit_sell_pending_orders
    memory_orders['exit_buy_todo_orders'] = exit_buy_todo_orders
    memory_orders['exit_buy_pending_orders'] = exit_buy_pending_orders

    return jsonify(memory_orders), 200
    
def init_background_tasks():
    executor.submit(thread_exit_orders)

    
def check_thread_status():
    """Check if thread_exit_orders is running"""
    for thread in threading.enumerate():
        if thread.name == "thread_exit_orders":
            return True
    return False

@app.route("/thread_status", methods=["GET"])
def get_thread_status():
    return jsonify({"status": "running" if check_thread_status() else "not running"}), 200


if __name__ == "__main__":
    app.run(host="0.0.0.0")
    init_background_tasks()
