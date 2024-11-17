from flask import Flask, request, jsonify
import requests
import logging
import json

# Initialize Flask app
app = Flask(__name__)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Endpoint of the FastAPI server
FASTAPI_URL = "http://34.134.7.0"

# In-memory store for orders
orders = {}

@app.route("/", methods=["POST"])
def forward_order():
    # Extract the data from the incoming request
    data = request.json

    # Extract the API key from the JSON body
    api_key = data.get("api_key")
    if not api_key:
        logger.error("Missing API key in the request body")
        return jsonify({"error": "Missing API key in the request body"}), 403

    # Extract and process data
    datetmp = data.get('date', '')
    option_value = data.get("option", '')
    symbol = data.get('symbol', '')
    strikeprice = int(data.get("strikeprice", ''))
    roundingprice = int(data.get("RoundingPrice", ''))
    side = data.get("side", '')

    if side != "SELL":
        logger.error("the alert is not SELL")
        return jsonify({"error": "the alert is not SELL"}), 400

    if not datetmp or not symbol or not strikeprice or not roundingprice:
        logger.error("Missing required fields in the request body")
        return jsonify({"error": "Missing required fields in the request body"}), 400

    # Calculate the buy order strike price
    fixed_multiple = 10
    if option_value == "call":
        buy_strikeprice = strikeprice + (roundingprice * fixed_multiple)
    elif option_value == "put":
        buy_strikeprice = strikeprice - (roundingprice * fixed_multiple)
    else:
        logger.error("Invalid option type")
        return jsonify({"error": "Invalid option type"}), 400

    # Construct the buy order code name
    buy_code_name = f"US.{symbol}{datetmp[2:]}"
    if option_value == "put":
        buy_code_name += "P"
    elif option_value == "call":
        buy_code_name += "C"
    
    buy_code_name += f"{buy_strikeprice}000"
    logger.info(f"Generated buy_code_name: {buy_code_name}")

    # Construct and send the buy order
    buy_order_data = {
        "symbol": buy_code_name,
        "quantity": data.get("quantity"),
        "side": "BUY",
        "type": data.get("type"),
    }

    headers = {
        "Content-Type": "application/json",
        "api-key": api_key
    }

    try:
        # Send the buy order request to the FastAPI server
        buy_response = requests.post(FASTAPI_URL, json=buy_order_data, headers=headers)
        buy_response.raise_for_status()
        buy_response_json = buy_response.json()

        try:
            json_object = json.loads(buy_response_json)
        except Exception as e:
            print(f"[-] forward_order: error {e}")
            return "", response.status_code

        # Remember the order by storing it in the in-memory dictionary
        buy_order_id = json_object[0]["order_id"]
        if buy_order_id:
            orders[buy_order_id] = buy_order_data
            logger.info(f"Buy order placed successfully. Order ID: {buy_order_id}")
        else:
            logger.error("Buy order response does not contain 'order_id'")
            return jsonify({"error": "Buy order response does not contain 'order_id'"}), 500

        # Now construct and send the original sell order
        sell_code_name = f"US.{symbol}{datetmp[2:]}"
        if option_value == "put":
            sell_code_name += "P"
        elif option_value == "call":
            sell_code_name += "C"
        
        sell_code_name += f"{strikeprice}000"
        logger.info(f"Generated sell_code_name: {sell_code_name}")

        sell_order_data = {
            "symbol": sell_code_name,
            "quantity": data.get("quantity"),
            "side": "SELL",
            "type": data.get("type"),
        }

        sell_response = requests.post(FASTAPI_URL, json=sell_order_data, headers=headers)
        sell_response.raise_for_status()
        sell_response_json = sell_response.json()

        try:
            json_object = json.loads(sell_response_json)
        except Exception as e:
            print(f"[-] forward_order: error {e}")
            return "", response.status_code

        # Remember the order by storing it in the in-memory dictionary
        sell_order_id = json_object[0]["order_id"]
        if sell_order_id:
            orders[sell_order_id] = sell_order_data
            logger.info(f"Sell order placed successfully. Order ID: {sell_order_id}")
        else:
            logger.error("Sell order response does not contain 'order_id'")
            return jsonify({"error": "Sell order response does not contain 'order_id'"}), 500

    except requests.exceptions.RequestException as e:
        logger.error(f"Request to FastAPI failed: {e}")
        return jsonify({"error": str(e)}), 500
    except ValueError:
        logger.error("Invalid JSON response from FastAPI server")
        return jsonify({"error": "Invalid JSON response from FastAPI server"}), 500

    # Return the response from FastAPI back to the client
    return jsonify(sell_response_json), sell_response.status_code

@app.route("/orders", methods=["GET"])
def get_orders():
    """Endpoint to retrieve all placed orders"""
    return jsonify(orders)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=80)
