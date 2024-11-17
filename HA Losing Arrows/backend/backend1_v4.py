from flask import Flask, request, jsonify
import requests
import logging
import json
import time

app = Flask(__name__)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

FASTAPI_URL = "http://34.134.7.0"
G_FIXED_MULTIPLE = 10
orders = {}  # In-memory store for orders


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

            if "Open position failed" in str(response_json):
                logger.error(f"Open position failed: {response_json}")
                continue

            if "order_id" in response_json[0]:
                logger.info(f"Order placed successfully. ID: {response_json[0]['order_id']}")
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
        logger.error("Missing API key")
        return jsonify({"error": "Missing API key"}), 403

    action = data.get("action")
    symbol = data.get("symbol", "")

    if action and symbol:
        return exit_positions(data, symbol, action, api_key)

    # Extract relevant order data
    datetmp = data.get('date', '')
    option_value = data.get("option", '')
    roundingprice = data.get("RoundingPrice", 0)
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
                return retry_buy_order(fixed_multiple - 1)

            orders[response_json[0]["order_id"]] = buy_order_data
            logger.info(f"Buy order placed. Order ID: {response_json[0]['order_id']}")
            return response_json, response.status_code
        except requests.exceptions.RequestException as e:
            logger.error(f"Buy order failed: {e}")
            return jsonify({"error": str(e)}), 500

    buy_response_json, buy_response_status = retry_buy_order(G_FIXED_MULTIPLE)

    if buy_response_status != 200:
        return buy_response_json, buy_response_status

    # Now send the original sell order
    sell_code_name = get_codename(symbol, datetmp, option_value, strikeprice, roundingprice, 0)
    sell_order_data = {
        "symbol": sell_code_name,
        "quantity": data.get("quantity"),
        "side": "SELL",
        "type": data.get("type"),
    }

    try:
        sell_response = requests.post(FASTAPI_URL, json=sell_order_data, headers=headers)
        sell_response.raise_for_status()
        sell_response_json = sell_response.json()
        orders[sell_response_json[0]["order_id"]] = sell_order_data
        logger.info(f"Sell order placed. Order ID: {sell_response_json[0]['order_id']}")
        return jsonify(sell_response_json), sell_response.status_code
    except requests.exceptions.RequestException as e:
        logger.error(f"Sell order failed: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/orders", methods=["GET"])
def get_orders():
    return jsonify(orders)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=80)
