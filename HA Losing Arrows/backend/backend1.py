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
    strikeprice = data.get("strikeprice", '')

    if not datetmp or not symbol or not strikeprice:
        logger.error("Missing required fields in the request body")
        return jsonify({"error": "Missing required fields in the request body"}), 400

    code_name = f"US.{symbol}{datetmp[2:]}"
    if option_value == "put":
        code_name += "P"
    elif option_value == "call":
        code_name += "C"
    else:
        logger.error("Invalid option type")
        return jsonify({"error": "Invalid option type"}), 400
    
    code_name += strikeprice + "000"
    logger.info(f"Generated code_name: {code_name}")

    # Extract necessary fields for the FastAPI request
    fastapi_data = {
        "symbol": code_name,
        "quantity": data.get("quantity"),
        "side": data.get("side"),
        "type": data.get("type"),
    }

    # Send the request to the FastAPI server
    headers = {
        "Content-Type": "application/json",
        "api-key": api_key
    }

    try:
        response = requests.post(FASTAPI_URL, json=fastapi_data, headers=headers)
        response.raise_for_status()  # Raises an HTTPError if the response was an error
        response_json = response.json()  # Parse JSON response
        print(response_json)
        
        try:
            json_object = json.loads(response_json)
        except Exception as e:
            print(f"[-] forward_order: error {e}")
            return "", response.status_code

        # Remember the order by storing it in the in-memory dictionary
        order_id = json_object[0]["order_id"]
        if order_id:
            orders[order_id] = fastapi_data
            logger.info(f"Order placed successfully. Order ID: {order_id}")
        else:
            logger.error("Order response does not contain 'order_id'")
            return jsonify({"error": "Order response does not contain 'order_id'"}), 500

    except requests.exceptions.RequestException as e:
        logger.error(f"Request to FastAPI failed: {e}")
        return jsonify({"error": str(e)}), 500
    except ValueError:
        logger.error("Invalid JSON response from FastAPI server")
        return jsonify({"error": "Invalid JSON response from FastAPI server"}), 500

    # Return the response from FastAPI back to the client
    return jsonify(response_json), response.status_code

@app.route("/orders", methods=["GET"])
def get_orders():
    """Endpoint to retrieve all placed orders"""
    return jsonify(orders)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=80)
