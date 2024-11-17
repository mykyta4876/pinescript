from flask import Flask, request, jsonify
import requests
import logging
import json
import time
import threading

# Initialize Flask app
app = Flask(__name__)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Endpoint of the FastAPI server
FASTAPI_URL = "http://34.134.7.0"
G_FIXED_MULTIPLE = 10

# In-memory store for orders
orders = {}
pending_orders = {}
buy_pending_orders = {}

def get_codename(symbol, datetmp, option_value, strikeprice, roundingprice, fixed_multiple):
    bid_price = strikeprice + (roundingprice * fixed_multiple) if option_value == "call" else strikeprice - (roundingprice * fixed_multiple)
    option_code = "C" if option_value == "call" else "P" if option_value == "put" else ""
    
    if not option_code:
        return ""

    return f"US.{symbol}{datetmp[2:]}{option_code}{bid_price}000"

def exit_positions(data, symbol, action, api_key):
    option = "C" if action == "exit_calls" else "P" if action == "exit_puts" else None
    if not option:
        logger.error(f"Invalid exit action: {data}")
        return jsonify({"error": "Invalid exit action"}), 403

    headers = {"Content-Type": "application/json", "api-key": api_key}
    base_symbol = symbol

    selected_items = {
        order_id: order for order_id, order in orders.items()
        if order['symbol'].startswith(f'US.{base_symbol}') and order['symbol'][9 + len(base_symbol)] == option and order['side'] == "SELL"
    }

    for order_id, order in selected_items.items():
        logger.info(f"Exiting Order: ID: {order_id}, Details: {order}")
        order['side'] = "BUY"
        del orders[order_id]

        try:
            response = requests.post(FASTAPI_URL, json=order, headers=headers)
            response.raise_for_status()
            response_json = response.json()
            time.sleep(1)

            if "Open position failed" in str(response_json):
                logger.error(f"Open position failed (SELL): {response_json}")
                continue

            try:
                json_object = json.loads(response_json)
            except Exception as e:
                logger.error(f"[-] exit_positions: SELL: error {e} : {order}")
                return retry_buy_order(fixed_multiple - 1)

            if "order_id" in json_object[0]:
                logger.info(f"Exited SELL Order {order_id} successfully. ID: {json_object[0]['order_id']}")
            else:
                logger.error("Order response missing 'order_id'")
        except requests.exceptions.RequestException as e:
            logger.error(f"FastAPI request failed: {e}")

    selected_items = {
        order_id: order for order_id, order in orders.items()
        if order['symbol'].startswith(f'US.{base_symbol}') and order['symbol'][9 + len(base_symbol)] == option and order['side'] == "BUY"
    }

    for order_id, order in selected_items.items():
        logger.info(f"Exiting Order: ID: {order_id}, Details: {order}")
        order['side'] = "SELL"
        del orders[order_id]

        try:
            response = requests.post(FASTAPI_URL, json=order, headers=headers)
            response.raise_for_status()
            response_json = response.json()
            time.sleep(1)

            if "Open position failed" in str(response_json):
                logger.error(f"Open position failed (BUY): {response_json}")
                continue

            try:
                json_object = json.loads(response_json)
            except Exception as e:
                logger.error(f"[-] exit_positions: BUY: error {e} : {order}")
                return retry_buy_order(fixed_multiple - 1)

            if "order_id" in json_object[0]:
                logger.info(f"Exited BUY Order {order_id} successfully. ID: {json_object[0]['order_id']}")
            else:
                logger.error("Order response missing 'order_id'")
        except requests.exceptions.RequestException as e:
            logger.error(f"FastAPI request failed: {e}")

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

            pending_orders[order_id] = sell_order_data
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
    while True:
        time.sleep(2)
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
            for p_order_id, p_order in pending_orders.items():
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
                            processed_list.append(p_order_id)

                            logger.info(f"[-] sell_order: Sell order placed. Order ID: {order_id} : sell order of {p_order_id}")
                            break
                        except requests.exceptions.RequestException as e:
                            logger.error(f"[-] sell_order: Sell order failed: {e} : sell order of {p_order_id}")
                            break

            for order_id in processed_list:
                del pending_orders[order_id]
                del buy_pending_orders[order_id]

        except requests.exceptions.RequestException as e:
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

    """Endpoint to retrieve all placed orders"""
    return jsonify(orders), 200

if __name__ == "__main__":
    #app.run(host="0.0.0.0", port=80)
    thread1 = threading.Thread(target=sell_order)
    thread1.start()
    app.run(host="0.0.0.0", port=443, ssl_context=("sapiogenics.com.crt", "sapiogenics.com.key"))
