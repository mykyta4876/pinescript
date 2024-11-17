from flask import Flask, request, jsonify
import requests
import logging
import json
import time

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

def get_codename(symbol, datetmp, option_value, strikeprice, roundingprice, fixed_multiple):
    if option_value == "call":
        bid_price = strikeprice + (roundingprice * fixed_multiple)
    elif option_value == "put":
        bid_price = strikeprice - (roundingprice * fixed_multiple)
    else:
        return ""

    # Construct the buy order code name
    code_name = f"US.{symbol}{datetmp[2:]}"
    if option_value == "put":
        code_name += "P"
    elif option_value == "call":
        code_name += "C"
    
    code_name += f"{bid_price}000"

    return code_name

def exit_positions(data, symbol, action, api_key):
    global orders

    option = "" 
    if action == "exit_calls":
        option = "C"
    elif action == "exit_puts":
        option = "P"
    else:
        logger.error(f"exit-order doesn't have valid action : {data}")
        return jsonify({"error": "exit-order doesn't have valid action"}), 403

    base_symbol = symbol
    headers = {
        "Content-Type": "application/json",
        "api-key": api_key
    }

    # Filter based on base_symbol and option
    selected_items = {
        order_id: order
        for order_id, order in orders.items()
        if order['symbol'].startswith(f'US.{base_symbol}') and order['symbol'][9 + len(base_symbol)] == option and order['side'] == "SELL"
    }

    # Display results
    for order_id, order in selected_items.items():
        logger.error(f"[-] exit_positions: Order ID: {order_id}, Order Details: {order}")
        order['side'] = "BUY"

        del orders[order_id]

        try:
            # Send the buy order request to the FastAPI server
            response = requests.post(FASTAPI_URL, json=order, headers=headers)
            response.raise_for_status()
            response_json = response.json()
            time.sleep(1)

            if len(response_json) == 2 and (response_json[1].find("Open position failed") != -1 or response_json[0].find("Open position failed") != -1):
                logger.error(f"[-] exit_positions: Open position failed : {response_json}")
                continue

            try:
                json_object = json.loads(response_json)
            except Exception as e:
                logger.error(f"[-] exit_positions: error {e} : {response_json}")
                continue

            # Remember the order by storing it in the in-memory dictionary
            if "order_id" in json_object[0]:
                order_id = json_object[0]["order_id"]
                logger.info(f"[-] exit_positions: order placed successfully. Order ID: {order_id}")
            else:
                logger.error(f"[-] exit_positions: order response does not contain 'order_id'")
        except requests.exceptions.RequestException as e:
            logger.error(f"[-] exit_positions: Request to FastAPI failed: {e}")
        except ValueError:
            logger.error(f"[-] exit_positions: Invalid JSON response from FastAPI server")

    # Filter based on base_symbol and option
    selected_items = {
        order_id: order
        for order_id, order in orders.items()
        if order['symbol'].startswith(f'US.{base_symbol}') and order['symbol'][9 + len(base_symbol)] == option and order['side'] == "BUY"
    }

    # Display results
    for order_id, order in selected_items.items():
        logger.error(f"Order ID: {order_id}, Order Details: {order}")
        order['side'] = "SELL"

        del orders[order_id]

        try:
            # Send the buy order request to the FastAPI server
            response = requests.post(FASTAPI_URL, json=order, headers=headers)
            response.raise_for_status()
            response_json = response.json()
            time.sleep(1)

            if len(response_json) == 2 and (response_json[1].find("Open position failed") != -1 or response_json[0].find("Open position failed") != -1):
                logger.error(f"[-] exit_positions: Open position failed : {response_json}")
                continue

            try:
                json_object = json.loads(response_json)
            except Exception as e:
                logger.error(f"[-] exit_positions: error {e} : {response_json}")
                continue

            # Remember the order by storing it in the in-memory dictionary
            if "order_id" in json_object[0]:
                order_id = json_object[0]["order_id"]
                logger.info(f"[-] exit_positions: order placed successfully. Order ID: {order_id}")
            else:
                logger.error(f"[-] exit_positions: order response does not contain 'order_id'")
        except requests.exceptions.RequestException as e:
            logger.error(f"[-] exit_positions: Request to FastAPI failed: {e}")
        except ValueError:
            logger.error(f"[-] exit_positions: Invalid JSON response from FastAPI server")

    return jsonify({"success": "exited Positions"}), 200

@app.route("/", methods=["POST"])
def forward_order():
    global orders
    # Extract the data from the incoming request
    data = request.json

    # Extract the API key from the JSON body
    api_key = data.get("api_key")
    if not api_key:
        logger.error("Missing API key in the request body")
        return jsonify({"error": "Missing API key in the request body"}), 403

    action = data.get('action')
    symbol = data.get('symbol', '')

    if action and symbol:
        return exit_positions(data, symbol, action, api_key)

    # Extract and process data
    datetmp = data.get('date', '')
    option_value = data.get("option", '')

    try:
        strikeprice = int(data.get("strikeprice", ''))
    except Exception as e:
        logger.error(f"error: {e}")
        return jsonify({"error": "strikeprice is not valid"}), 400

    roundingprice = int(data.get("RoundingPrice", ''))
    side = data.get("side", '')

    if side != "SELL":
        logger.error("the alert is not SELL")
        return jsonify({"error": "the alert is not SELL"}), 400

    if not datetmp or not symbol or not strikeprice or not roundingprice:
        logger.error("Missing required fields in the request body")
        return jsonify({"error": "Missing required fields in the request body"}), 400

    # Calculate the buy order strike price
    fixed_multiple = G_FIXED_MULTIPLE
    buy_code_name = get_codename(symbol, datetmp, option_value, strikeprice, roundingprice, fixed_multiple)
    if len(buy_code_name) == 0:
        logger.error("Invalid option type")
        return jsonify({"error": "Invalid option type"}), 400

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

        if len(buy_response_json) == 2 and (buy_response_json[1].find("Open position failed") != -1 or buy_response_json[0].find("Open position failed") != -1):
            print(f"[-] forward_order: Open position failed : {buy_response_json} : {fixed_multiple}")

            fixed_multiple = G_FIXED_MULTIPLE - 1
            buy_code_name2 = get_codename(symbol, datetmp, option_value, strikeprice, roundingprice, fixed_multiple)
            if len(buy_code_name2) == 0:
                logger.error("Invalid option type")
                return jsonify({"error": "Invalid option type"}), 400

            logger.info(f"Generated buy_code_name: {buy_code_name2}")

            # Construct and send the buy order
            buy_order_data2 = {
                "symbol": buy_code_name2,
                "quantity": data.get("quantity"),
                "side": "BUY",
                "type": data.get("type"),
            }

            try:
                # Send the buy order request to the FastAPI server
                buy_response2 = requests.post(FASTAPI_URL, json=buy_order_data2, headers=headers)
                buy_response2.raise_for_status()
                buy_response_json2 = buy_response2.json()

                if len(buy_response_json2) == 2 and (buy_response_json2[1].find("Open position failed") != -1 or buy_response_json2[0].find("Open position failed") != -1):
                    print(f"[-] forward_order: Open position failed : {buy_response_json2} : {fixed_multiple}")

                    fixed_multiple = G_FIXED_MULTIPLE - 2
                    buy_code_name3 = get_codename(symbol, datetmp, option_value, strikeprice, roundingprice, fixed_multiple)
                    if len(buy_code_name3) == 0:
                        logger.error("Invalid option type")
                        return jsonify({"error": "Invalid option type"}), 400

                    logger.info(f"Generated buy_code_name: {buy_code_name3}")

                    # Construct and send the buy order
                    buy_order_data3 = {
                        "symbol": buy_code_name3,
                        "quantity": data.get("quantity"),
                        "side": "BUY",
                        "type": data.get("type"),
                    }

                    try:
                        # Send the buy order request to the FastAPI server
                        buy_response3 = requests.post(FASTAPI_URL, json=buy_order_data3, headers=headers)
                        buy_response3.raise_for_status()
                        buy_response_json3 = buy_response3.json()

                        if len(buy_response_json3) == 2 and (buy_response_json3[1].find("Open position failed") != -1 or buy_response_json3[0].find("Open position failed") != -1):
                            print(f"[-] forward_order: Open position failed : {buy_response_json3} : {fixed_multiple}, 3 times failed")
                            return jsonify({"error": "Open position failed, 3 times failed"}), 500

                        try:
                            json_object = json.loads(buy_response_json3)
                        except Exception as e:
                            print(f"[-] forward_order: error {e} : {fixed_multiple}")
                            return "", buy_response3.status_code

                        # Remember the order by storing it in the in-memory dictionary
                        if "order_id" in json_object[0]:
                            buy_order_id3 = json_object[0]["order_id"]
                            orders[buy_order_id3] = buy_order_data3
                            logger.info(f"Buy order placed successfully. Order ID: {buy_order_id3} : {fixed_multiple}")
                        else:
                            logger.error(f"Buy order response does not contain 'order_id', {fixed_multiple}")
                            return jsonify({"error": "Buy order response does not contain 'order_id', 3"}), 500

                    except requests.exceptions.RequestException as e:
                        logger.error(f"Request to FastAPI failed: {e} : {fixed_multiple}")
                        return jsonify({"error": str(e)}), 500
                    except ValueError:
                        logger.error(f"Invalid JSON response from FastAPI server : {fixed_multiple}")
                        return jsonify({"error": "Invalid JSON response from FastAPI server"}), 500
                else:
                    try:
                        json_object = json.loads(buy_response_json2)
                    except Exception as e:
                        print(f"[-] forward_order: error {e} : {fixed_multiple}")
                        return "", buy_response2.status_code

                    # Remember the order by storing it in the in-memory dictionary
                    if "order_id" in json_object[0]:
                        buy_order_id2 = json_object[0]["order_id"]
                        orders[buy_order_id2] = buy_order_data2
                        logger.info(f"Buy order placed successfully. Order ID: {buy_order_id2} : {fixed_multiple}")
                    else:
                        logger.error(f"Buy order response does not contain 'order_id', {fixed_multiple}")
                        return jsonify({"error": "Buy order response does not contain 'order_id', 2"}), 500

            except requests.exceptions.RequestException as e:
                logger.error(f"Request to FastAPI failed: {e} : {fixed_multiple}")
                return jsonify({"error": str(e)}), 500
            except ValueError:
                logger.error(f"Invalid JSON response from FastAPI server : {fixed_multiple}")
                return jsonify({"error": "Invalid JSON response from FastAPI server"}), 500
        else:
            try:
                json_object = json.loads(buy_response_json)
            except Exception as e:
                print(f"[-] forward_order: error {e} : {buy_response_json} : {fixed_multiple}")
                return "", buy_response.status_code

            # Remember the order by storing it in the in-memory dictionary
            if "order_id" in json_object[0]:
                buy_order_id = json_object[0]["order_id"]
                orders[buy_order_id] = buy_order_data
                logger.info(f"Buy order placed successfully. Order ID: {buy_order_id} : {fixed_multiple}")
            else:
                logger.error(f"Buy order response does not contain 'order_id', {fixed_multiple}")
                return jsonify({"error": "Buy order response does not contain 'order_id', 1"}), 500

        # Now construct and send the original sell order
        sell_code_name = get_codename(symbol, datetmp, option_value, strikeprice, roundingprice, 0)
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
            return "", sell_response.status_code

        # Remember the order by storing it in the in-memory dictionary
        if "order_id" in json_object[0]:
            sell_order_id = json_object[0]["order_id"]
            orders[sell_order_id] = sell_order_data
            logger.info(f"Sell order placed successfully. Order ID: {sell_order_id}")
        else:
            logger.error("Sell order response does not contain 'order_id'")
            return jsonify({"error": "Sell order response does not contain 'order_id'"}), 500

    except requests.exceptions.RequestException as e:
        logger.error(f"Request to FastAPI failed: {e}: {fixed_multiple}")
        return jsonify({"error": str(e)}), 500
    except ValueError:
        logger.error(f"Invalid JSON response from FastAPI server : {fixed_multiple}")
        return jsonify({"error": "Invalid JSON response from FastAPI server"}), 500

    # Return the response from FastAPI back to the client
    return jsonify(sell_response_json), sell_response.status_code

@app.route("/orders", methods=["GET"])
def get_orders():
    global orders
    """Endpoint to retrieve all placed orders"""
    return jsonify(orders)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=80)
