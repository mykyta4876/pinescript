from flask import Flask, request, jsonify
import pytz
import requests
from logger import logger, LOGGING_CONFIG
import json
import time
import threading
import os
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta
from collections import defaultdict

# Initialize Flask app
app = Flask(__name__)

G_FIXED_MULTIPLE = 10

api_all_keys = {"a1b2c345-6def-789g-hijk-123456789lmn": "paper",    # execute the order on all paper accounts. 
                "z9y8x765-4wvu-321t-rqpo-987654321abc": "real"}     # execute the order on all real accounts.

api_keys = {
    "fb7c1234-25ae-48b6-9f7f-9b3f98d76543": {"id":"ryanoakes-real", "opend-address":"34.71.74.2"}, 
    #"a9f8f651-4d3e-46f1-8d6b-c2f1f3b76429": {"id":"ryanoakes-paper", "opend-address":"34.71.74.2"}, 
    "7d4f8a12-1b3c-45e9-9b1a-2a6e0fc2e975": {"id":"enlixir-real", "opend-address":"34.73.25.174"}, 
    #"d45a6e79-927b-4f3e-889d-3c65a8f0738c": {"id":"enlixir-paper", "opend-address":"34.73.25.174"}
    }

# In-memory store for orders
orders = {}
sell_todo_orders = {}
sell_pending_orders = {}
buy_todo_orders = {}
buy_pending_orders = {}
exit_sell_todo_orders = {}
exit_sell_pending_orders = {}
exit_buy_todo_orders = {}
exit_buy_pending_orders = {}
order_pair_map = {}

## Naked Strategy
naked_todo_orders = {}
naked_pending_orders = {}
naked_exit_todo_orders = {}

executor = ThreadPoolExecutor(max_workers=1)

def get_codename(symbol, datetmp, option_value, strikeprice, roundingprice, fixed_multiple, ordertag):
    option_code = "C" if option_value == "call" else "P" if option_value == "put" else ""
    
    if not option_code:
        return ""

    if ordertag == 1:
        # naked strategy
        bid_price = strikeprice
    else:
        # covered strategy
        bid_price = strikeprice + (roundingprice * fixed_multiple) if option_value == "call" else strikeprice - (roundingprice * fixed_multiple)

    return f"US.{symbol}{datetmp[2:]}{option_code}{bid_price}000"

def save_orders_into_jsonfile():
    global orders
    global sell_todo_orders
    global buy_pending_orders
    global exit_sell_todo_orders
    global exit_sell_pending_orders
    global exit_buy_todo_orders
    global exit_buy_pending_orders
    global naked_pending_orders
    global naked_exit_todo_orders
    global order_pair_map

    total_orders = {}
    total_orders['orders'] = orders
    total_orders['sell_todo_orders'] = sell_todo_orders
    total_orders['buy_pending_orders'] = buy_pending_orders
    total_orders['exit_sell_todo_orders'] = exit_sell_todo_orders
    total_orders['exit_sell_pending_orders'] = exit_sell_pending_orders
    total_orders['exit_buy_todo_orders'] = exit_buy_todo_orders
    total_orders['exit_buy_pending_orders'] = exit_buy_pending_orders
    total_orders['naked_pending_orders'] = naked_pending_orders
    total_orders['naked_exit_todo_orders'] = naked_exit_todo_orders

    count = len(sell_todo_orders) + len(buy_pending_orders) + len(exit_sell_todo_orders) + len(exit_sell_pending_orders) + len(exit_buy_todo_orders) + len(exit_buy_pending_orders) + len(naked_pending_orders) + len(naked_exit_todo_orders)
    if count == 0:
        order_pair_map = {}
    total_orders['order_pair_map'] = order_pair_map
    with open("orders.json", "w") as f:
        json.dump(total_orders, f)
    logger.info(f"[-] save_orders_into_jsonfile: Orders saved")

@app.route("/call_save_orders_into_jsonfile", methods=["GET"])
def call_save_orders_into_jsonfile():
    save_orders_into_jsonfile()
    return jsonify({"success": "Orders saved"}), 200

def load_orders_from_jsonfile():
    global orders
    global sell_todo_orders
    global buy_pending_orders
    global exit_sell_todo_orders
    global exit_sell_pending_orders
    global exit_buy_todo_orders
    global exit_buy_pending_orders
    global naked_pending_orders
    global naked_exit_todo_orders
    global order_pair_map

    if not os.path.exists("orders.json"):
        logger.error(f"[-] load_orders_from_jsonfile: orders.json does not exist")
        return

    with open("orders.json", "r") as f:
        total_orders = json.load(f)
    
    orders = total_orders['orders']
    sell_todo_orders = total_orders['sell_todo_orders']
    buy_pending_orders = total_orders['buy_pending_orders']
    exit_sell_todo_orders = total_orders['exit_sell_todo_orders']
    exit_sell_pending_orders = total_orders['exit_sell_pending_orders']
    exit_buy_todo_orders = total_orders['exit_buy_todo_orders']
    exit_buy_pending_orders = total_orders['exit_buy_pending_orders']
    naked_pending_orders = total_orders['naked_pending_orders']
    naked_exit_todo_orders = total_orders['naked_exit_todo_orders']
    order_pair_map = total_orders['order_pair_map']
    logger.info(f"[-] load_orders_from_jsonfile: Orders loaded")


def merge_orders(input_data, max_quantity=5):
    # Step 1: Group and sum quantities by symbol, side, and type
    grouped_data = defaultdict(lambda: {"symbol": None, "quantity": 0, "side": None, "type": None, "api_key": None, "multiple_exit_level": 0, "order_tag": None, "original_ids": []})

    for key, value in input_data.items():
        # Use (symbol, side, type) as the grouping key
        group_key = (value["symbol"], value["side"], value["type"])
        
        if grouped_data[group_key]["symbol"] is None:
            grouped_data[group_key]["symbol"] = value["symbol"]
            grouped_data[group_key]["side"] = value["side"]
            grouped_data[group_key]["type"] = value["type"]
            grouped_data[group_key]["api_key"] = value["api_key"]
            grouped_data[group_key]["multiple_exit_level"] = value["multiple_exit_level"]
            grouped_data[group_key]["order_tag"] = value["order_tag"]
            
        # Sum the quantity and keep track of the original IDs
        grouped_data[group_key]["quantity"] += int(value["quantity"])
        grouped_data[group_key]["original_ids"].append(key)

    # Step 2: Split any entries with quantity > 5 and retain unique IDs
    result = {}
    for item in grouped_data.values():
        quantity = item["quantity"]
        original_ids = item["original_ids"]
        
        # Calculate the number of full chunks of 5 and the remainder
        full_chunks = quantity // max_quantity
        remainder = quantity % max_quantity
        
        # Process each original ID separately
        id_counter = 0  # Counter to generate unique IDs based on original IDs
        
        for original_id in original_ids:
            # Assign chunks of 5 to the original ID, creating unique IDs for each chunk
            while full_chunks > 0:
                if id_counter == 0:
                    chunk_id = original_id
                else:
                    chunk_id = f"{original_id}-{id_counter}"
                result[chunk_id] = {
                    "symbol": item["symbol"],
                    "quantity": max_quantity,
                    "side": item["side"],
                    "type": item["type"],
                    "api_key": item["api_key"],
                    "multiple_exit_level": item["multiple_exit_level"],
                    "order_tag": item["order_tag"]
                }
                full_chunks -= 1
                id_counter += 1
            
            # If there is a remainder, add it to the final chunk of this original ID
            if remainder > 0:
                if id_counter == 0:
                    remainder_id = original_id
                else:
                    remainder_id = f"{original_id}-{id_counter}"

                result[remainder_id] = {
                    "symbol": item["symbol"],
                    "quantity": remainder,
                    "side": item["side"],
                    "type": item["type"],
                    "api_key": item["api_key"],
                    "multiple_exit_level": item["multiple_exit_level"],
                    "order_tag": item["order_tag"]
                }
                remainder = 0  # Set remainder to 0 after processing
                id_counter += 1

    return result

def thread_exit_orders():
    global buy_pending_orders
    global sell_todo_orders
    global sell_pending_orders
    global exit_sell_todo_orders
    global exit_buy_todo_orders
    global exit_sell_pending_orders
    global exit_buy_pending_orders
    global naked_pending_orders
    global naked_exit_todo_orders
    global order_pair_map
    global orders
    symbol_list = []
    symbol_last_price = {}
    symbol_last_time = datetime.now().astimezone(pytz.timezone('US/Eastern'))

    threading.current_thread().name = "thread_exit_orders"
    logger.info(f"[-] thread_exit_orders: start")
    
    while True:
        try:
            now_time = datetime.now().astimezone(pytz.timezone('US/Eastern'))
            if now_time.hour < 9:
                time.sleep(10)
                continue
            
            if now_time.hour == 9 and now_time.minute == 25 and now_time.second > 30 and now_time.second < 45:
                load_orders_from_jsonfile()
                symbol_list = []
                symbol_last_price = {}
            if now_time.hour == 9 and now_time.minute < 30:
                time.sleep(10)
                continue

            if now_time.hour == 16 and now_time.minute == 10 and now_time.second > 0 and now_time.second < 15:
                save_orders_into_jsonfile()

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

                sell_selected_items = {
                    order_id: order for order_id, order in naked_pending_orders.items()
                    if order['api_key'] == api_key
                }
                counts += len(sell_selected_items)

                sell_selected_items = {
                    order_id: order for order_id, order in naked_exit_todo_orders.items()
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
                        time.sleep(2)

                        try:
                            json_object_order_list = json.loads(response_json)
                            break
                        except Exception as e:
                            logger.error(f"[-] thread_exit_orders: order_list: error: {e}, acc:{api_info['id']}")
                            break

                    except requests.exceptions.RequestException as e:
                        logger.error(f"[-] thread_exit_orders: order_list: error: {e}, acc:{api_info['id']}")
                        break
                
                logger.info(f"[-] thread_exit_orders: {api_info['id']} ### Finished the step - getting order list")

                # confirm the pending naked orders
                naked_pending_orders_copy = naked_pending_orders.copy()
                
                processed_list = []
                for p_order_id, p_order in naked_pending_orders_copy.items():
                    p_order_only_id = p_order_id.replace(api_keys[api_key]["id"], "")
                    for l_order in json_object_order_list:
                        if l_order['order_id'] == p_order_only_id and l_order['order_status'] == "FILLED_ALL":
                            logger.info(f"[-] thread_exit_orders: NAKED: pending order {p_order_id} is FILLED_ALL")
                            orders[p_order_id] = p_order
                            processed_list.append(p_order_id)
                            break

                for order_id in processed_list:
                    if order_id in naked_pending_orders:
                        del naked_pending_orders[order_id]

                # place the exit orders for naked orders
                naked_exit_todo_orders_copy = naked_exit_todo_orders.copy()
                naked_exit_todo_orders_copy_merged = merge_orders(naked_exit_todo_orders_copy, 5)
                for order_id, order in naked_exit_todo_orders_copy.items():
                    del naked_exit_todo_orders[order_id]
                
                for order_id, order in naked_exit_todo_orders_copy_merged.items():
                    naked_exit_todo_orders[order_id] = order

                naked_exit_todo_orders_copy = naked_exit_todo_orders.copy()
                processed_list = []
                for order_id, order in naked_exit_todo_orders_copy.items():
                    if order["api_key"] != api_key:
                        continue
                    logger.info(f"[-] thread_exit_orders: NAKED: Exiting Order: ID: {order_id}, Details: {order}")
                    if order["side"] == "BUY":
                        order['side'] = "SELL"
                    else:
                        order['side'] = "BUY"
                    order['type'] = "MARKET"

                    try:
                        response = requests.post(opend_address, json=order, headers=headers)
                        response.raise_for_status()
                        response_json = response.json()
                        time.sleep(3)

                        if "Open position failed" in str(response_json):
                            logger.error(f"[-] thread_exit_orders: NAKED: Open position failed: {response_json}, acc:{api_info['id']}, order:{order}")
                            continue

                        try:
                            json_object = json.loads(response_json)
                        except Exception as e:
                            logger.error(f"[-] thread_exit_orders: NAKED: error: {e}, acc:{api_info['id']}, order:{order}")
                            continue

                        if "order_id" in json_object[0]:
                            logger.info(f"[-] thread_exit_orders: NAKED: Placed the pending exit order of {order_id} successfully. ID: {json_object[0]['order_id']}, acc:{api_info['id']}, order:{order}")
                            processed_list.append(order_id)
                        else:
                            logger.error(f"[-] thread_exit_orders: NAKED: Order response missing 'order_id', acc:{api_info['id']}, order:{order}")

                    except requests.exceptions.RequestException as e:
                        logger.error(f"[-] thread_exit_orders: NAKED: FastAPI request failed: {e}, acc:{api_info['id']}, order:{order}")

                for order_id in processed_list:
                    del naked_exit_todo_orders[order_id]

                if len(symbol_list) > 0:
                    symbol_last_time_after_lmin = symbol_last_time + timedelta(minutes=1)
                    if now_time > symbol_last_time_after_lmin:
                        symbol_last_price = get_bid_price(symbol_list, api_key)
                        symbol_last_time = now_time

                        logger.info(f"[-] thread_exit_orders: {api_info['id']} ### Finished the step - getting bid prices")

                        copy_orders = orders.copy()
                        sell_selected_items = {
                            order_id: order for order_id, order in copy_orders.items()
                            if order['side'] == "SELL" and order['api_key'] == api_key
                        }

                        for order_id, order in sell_selected_items.items():
                            if order_id in orders:
                                if order['symbol'] in symbol_last_price and 'entry_price' in order and 'multiple_exit_level' in order and order['multiple_exit_level'] > 0:
                                    if (symbol_last_price[order['symbol']] > order['multiple_exit_level'] * order['entry_price'] and order['order_tag'] == 0) or (symbol_last_price[order['symbol']] < order['multiple_exit_level'] * order['entry_price'] and order['order_tag'] == 1):
                                        logger.info(f"[-] thread_exit_orders: SELL: {order_id} is {order['multiple_exit_level']}x entry price. symbol:{order['symbol']}")
                                        if not order_id in exit_sell_todo_orders:
                                            exit_sell_todo_orders[order_id] = order
                                        if order_id in orders:
                                            del orders[order_id]

                                        for buy_order_id, sell_order_id in order_pair_map.items():
                                            if sell_order_id == order_id:
                                                if not buy_order_id in exit_buy_todo_orders:
                                                    exit_buy_todo_orders[buy_order_id] = orders[buy_order_id]
                                                if buy_order_id in orders:
                                                    del orders[buy_order_id]
                        
                        logger.info(f"[-] thread_exit_orders: {api_info['id']} ### Finished the step - checking multiple exit condition")
                        
                sell_todo_orders_copy = sell_todo_orders.copy()
                
                processed_list = []
                for p_order_id, p_order in sell_todo_orders_copy.items():
                    p_order_only_id = p_order_id.replace(api_keys[api_key]["id"], "")

                    bFilled = False
                    for l_order in json_object_order_list:
                        if l_order['order_id'] == p_order_only_id and l_order['order_status'] == "FILLED_ALL":
                            logger.info(f"[-] thread_exit_orders: (buy order) {p_order_id} is FILLED_ALL")
                            bFilled = True
                            break;
                    
                    if not bFilled:
                        logger.info(f"[-] thread_exit_orders: (buy order) {p_order_id} is not FILLED_ALL")
                        continue

                    if "try_count" in p_order and p_order["try_count"] > 10:
                        logger.error(f"[-] thread_exit_orders: try_count of placing sell order is greater than 10, acc:{api_info['id']}, order:{p_order}")
                        processed_list.append(p_order_id)
                        break
                    
                    while True:
                        try:
                            sell_response = requests.post(opend_address, json=p_order, headers=headers)
                            sell_response.raise_for_status()
                            sell_response_json = sell_response.json()
                            time.sleep(2)

                            if "Open position failed" in str(sell_response_json):
                                if "due to the insufficient liquidity" in str(sell_response_json):
                                    logger.error(f"[-] thread_exit_orders: error of placing sell order: {sell_response_json}, acc:{api_info['id']}, order:{p_order}")
                                    bid_volume = get_bid_volume([p_order['symbol']], api_key)
                                    if bid_volume[p_order['symbol']] > 0 and bid_volume[p_order['symbol']] >= int(p_order['quantity']):
                                        logger.info(f"[-] thread_exit_orders: bid volume of {p_order['symbol']} is greater than 0 and greater than or equal to the quantity, so retry, acc:{api_info['id']}, order:{p_order}")
                                        time.sleep(10)
                                        continue
                                    else:
                                        logger.error(f"[-] thread_exit_orders: bid volume of {p_order['symbol']} is 0, acc:{api_info['id']}, order:{p_order}")
                                        if "try_count" in sell_todo_orders[p_order_id]:
                                            sell_todo_orders[p_order_id]["try_count"] += 1
                                        else:
                                            sell_todo_orders[p_order_id]["try_count"] = 1
                                        break
                                else:
                                    logger.error(f"[-] thread_exit_orders: error of placing sell order: {sell_response_json}, acc:{api_info['id']}, order:{p_order}")
                                    if "try_count" in sell_todo_orders[p_order_id]:
                                        sell_todo_orders[p_order_id]["try_count"] += 1
                                    else:
                                        sell_todo_orders[p_order_id]["try_count"] = 1
                                    break

                            try:
                                sell_json_object = json.loads(sell_response_json)
                            except Exception as e:
                                logger.error(f"[-] thread_exit_orders: error of placing sell order: {e}, sell order of {p_order_id}, acc:{api_info['id']}, order:{p_order}")
                                if "try_count" in sell_todo_orders[p_order_id]:
                                    sell_todo_orders[p_order_id]["try_count"] += 1
                                else:
                                    sell_todo_orders[p_order_id]["try_count"] = 1
                                break

                            order_id = sell_json_object[0]["order_id"] + api_keys[api_key]["id"]
                            orders[p_order_id] = buy_pending_orders[p_order_id]
                            orders[order_id] = p_order
                            order_pair_map[p_order_id] = order_id
                            processed_list.append(p_order_id)
                            sell_pending_orders[order_id] = p_order

                            logger.info(f"[-] thread_exit_orders: Placed sell order. Order ID: {order_id}, sell order of {p_order_id}, acc:{api_info['id']}, order:{p_order}")
                            break
                        except requests.exceptions.RequestException as e:
                            logger.error(f"[-] thread_exit_orders: Failed to place sell order: {e}, sell order of {p_order_id}, acc:{api_info['id']}, order:{p_order}")
                            if "try_count" in sell_todo_orders[p_order_id]:
                                sell_todo_orders[p_order_id]["try_count"] += 1
                            else:
                                sell_todo_orders[p_order_id]["try_count"] = 1
                            break

                logger.info(f"[-] thread_exit_orders: {api_info['id']} ### Finished the step - placing sell orders")

                for order_id in processed_list:
                    if order_id in sell_todo_orders:
                        del sell_todo_orders[order_id]
                    if order_id in buy_pending_orders:
                        del buy_pending_orders[order_id]

                sell_pending_orders_copy = sell_pending_orders.copy()
                for p_order_id, p_order in sell_pending_orders_copy.items():
                    p_order_only_id = p_order_id.replace(api_keys[api_key]["id"], "")
                    for l_order in json_object_order_list:
                        if l_order['order_id'] == p_order_only_id and l_order['order_status'] == "FILLED_ALL":
                            logger.info(f"[-] thread_exit_orders: Sell pending order {p_order_id} is FILLED_ALL, fill price:{l_order['dealt_avg_price']}")
                            if p_order_id in orders:
                                orders[p_order_id]['entry_price'] = l_order['dealt_avg_price']
                            
                            logger.info(f"[-] thread_exit_orders: Sell pending order 1")

                            if p_order_id in sell_pending_orders:
                                del sell_pending_orders[p_order_id]
                            
                            logger.info(f"[-] thread_exit_orders: Sell pending order 2")
                            
                            if p_order['symbol'] not in symbol_list:
                                symbol_list.append(p_order['symbol'])
                
                logger.info(f"[-] thread_exit_orders: {api_info['id']} ### Finished the step - confirming sell orders (coverd strategy)")

                naked_pending_orders_copy = naked_pending_orders.copy()
                for p_order_id, p_order in naked_pending_orders_copy.items():
                    p_order_only_id = p_order_id.replace(api_keys[api_key]["id"], "")
                    for l_order in json_object_order_list:
                        if l_order['order_id'] == p_order_only_id and l_order['order_status'] == "FILLED_ALL":
                            logger.info(f"[-] thread_exit_orders: Sell pending order {p_order_id} is FILLED_ALL, fill price:{l_order['dealt_avg_price']}")
                            if p_order_id in orders:
                                orders[p_order_id]['entry_price'] = l_order['dealt_avg_price']
                            
                            if p_order_id in naked_pending_orders:
                                del naked_pending_orders[p_order_id]
                            
                            if p_order['symbol'] not in symbol_list:
                                symbol_list.append(p_order['symbol'])
                
                logger.info(f"[-] thread_exit_orders: {api_info['id']} ### Finished the step - confirming sell orders (naked strategy)")

                exit_sell_todo_orders_copy = exit_sell_todo_orders.copy()
                for order_id, order in exit_sell_todo_orders_copy.items():
                    code_name = order['symbol']
                    str_day = code_name[-10:-8]
                    str_month = code_name[-12:-10]
                    str_year = code_name[-14:-12]
                    if code_name[-7] == 'C' or code_name[-7] == 'P':
                        str_day = code_name[-9:-7]
                        str_month = code_name[-11:-9]
                        str_year = code_name[-13:-11]

                    date_str = f"20{str_year}-{str_month}-{str_day}"
                    # Make the date_obj timezone-aware
                    date_obj = datetime.strptime(date_str, "%Y-%m-%d").replace(tzinfo=pytz.timezone('US/Eastern'))
                    date_obj = date_obj + timedelta(days=1)
                    if date_obj <= now_time:
                        del exit_sell_todo_orders[order_id]
                        logger.info(f"Removed expired order {order_id} for {code_name}")

                logger.info(f"[-] thread_exit_orders: {api_info['id']} ### Finished the step - checking expired orders")

                exit_sell_todo_orders_copy_merged = merge_orders(exit_sell_todo_orders_copy, 5)
                for order_id, order in exit_sell_todo_orders_copy.items():
                    del exit_sell_todo_orders[order_id]
                
                for order_id, order in exit_sell_todo_orders_copy_merged.items():
                    exit_sell_todo_orders[order_id] = order

                exit_sell_todo_orders_copy = exit_sell_todo_orders.copy()
                processed_list = []
                for order_id, order in exit_sell_todo_orders_copy.items():
                    if order["api_key"] != api_key:
                        continue

                    logger.info(f"Exiting Order: ID: {order_id}, Details: {order}")

                    p_order_only_id = order_id.replace(api_keys[api_key]["id"], "")
                    bFilled = False
                    for l_order in json_object_order_list:
                        if l_order['order_id'] == p_order_only_id and l_order['order_status'] == "FILLED_ALL":
                            bFilled = True
                            break
                    
                    if not bFilled:
                        logger.info(f"[-] thread_exit_orders: SELL: {order_id} is not FILLED_ALL")
                        continue

                    order['side'] = "BUY"

                    try:
                        response = requests.post(opend_address, json=order, headers=headers)
                        response.raise_for_status()
                        response_json = response.json()
                        time.sleep(3)

                        if "Open position failed" in str(response_json):
                            logger.error(f"[-] thread_exit_orders: SELL: Open position failed: {response_json}, acc:{api_info['id']}, order:{order}")
                            continue

                        try:
                            json_object = json.loads(response_json)
                        except Exception as e:
                            logger.error(f"[-] thread_exit_orders: SELL: error: {e}, acc:{api_info['id']}, order:{order}")
                            continue

                        if "order_id" in json_object[0]:
                            processed_list.append(order_id)
                            new_order_id = json_object[0]['order_id'] + api_keys[api_key]["id"]
                            order['new_order_id'] = new_order_id
                            exit_sell_pending_orders[order_id] = order
                            logger.info(f"[-] thread_exit_orders: SELL: Placed the pending exit order of {order_id} successfully. ID: {new_order_id}, acc:{api_info['id']}, order:{order}")
                        else:
                            logger.error(f"[-] thread_exit_orders: SELL: Order response missing 'order_id', acc:{api_info['id']}, order:{order}")

                    except requests.exceptions.RequestException as e:
                        logger.error(f"[-] thread_exit_orders: SELL: FastAPI request failed: {e}, acc:{api_info['id']}, order:{order}")

                for order_id in processed_list:
                    del exit_sell_todo_orders[order_id]

                logger.info(f"[-] thread_exit_orders: {api_info['id']} ### Finished the step - placing orders to exit sell orders")

                processed_list = []
                for p_order_id, p_order in exit_sell_pending_orders.items():
                    new_order_id = p_order['new_order_id']
                    if not new_order_id:
                        continue
                    p_order_only_id = new_order_id.replace(api_keys[api_key]["id"], "")
                    for l_order in json_object_order_list:
                        if l_order['order_id'] == p_order_only_id and l_order['order_status'] == "FILLED_ALL":
                            logger.info(f"[-] thread_exit_orders: SELL: {new_order_id} is FILLED_ALL, acc:{api_info['id']}, order:{p_order}")
                            processed_list.append(p_order_id)

                for order_id in processed_list:
                    if order_id in exit_sell_pending_orders:
                        del exit_sell_pending_orders[order_id]

                logger.info(f"[-] thread_exit_orders: {api_info['id']} ### Finished the step - confirming exit sell orders")

                if len(exit_sell_todo_orders) > 0:
                    continue

                exit_buy_todo_orders_copy = exit_buy_todo_orders.copy()
                exit_buy_todo_orders_copy_merged = merge_orders(exit_buy_todo_orders_copy, 5)
                for order_id, order in exit_buy_todo_orders_copy.items():
                    del exit_buy_todo_orders[order_id]
                
                for order_id, order in exit_buy_todo_orders_copy_merged.items():
                    exit_buy_todo_orders[order_id] = order

                exit_buy_todo_orders_copy = exit_buy_todo_orders.copy()
                processed_list = []
                for order_id, order in exit_buy_todo_orders_copy.items():
                    if order_id in order_pair_map:
                        exit_sell_order_id = order_pair_map[order_id]
                        if exit_sell_order_id in exit_sell_pending_orders:
                            continue
                        
                        if exit_sell_order_id in exit_sell_todo_orders:
                            continue

                    if order["api_key"] != api_key:
                        continue

                    logger.info(f"[-] thread_exit_orders: BUY: Exiting Order: ID: {order_id}, Details: {order}, acc:{api_info['id']}")
                    order['side'] = "SELL"
                    count = 0
                    while True:
                        try:
                            count += 1
                            if count > 3:
                                logger.error(f"[-] thread_exit_orders: BUY: Open position failed (3 times): ID: {order_id}, Details: {order}, acc:{api_info['id']}")
                                processed_list.append(order_id)
                                break

                            response = requests.post(opend_address, json=order, headers=headers)
                            response.raise_for_status()
                            response_json = response.json()
                            time.sleep(2)

                            if "Open position failed" in str(response_json):
                                logger.error(f"[-] thread_exit_orders: BUY: Open position failed: {response_json}, ID: {order_id}, Details: {order}, acc:{api_info['id']}")
                                time.sleep(1)
                                continue

                            try:
                                json_object = json.loads(response_json)
                            except Exception as e:
                                logger.error(f"[-] thread_exit_orders: BUY: error {e}, ID: {order_id}, Details: {order}, acc:{api_info['id']}")
                                time.sleep(1)
                                continue

                            if "order_id" in json_object[0]:
                                logger.info(f"[-] thread_exit_orders: BUY: Placed the pending exit order of {order_id} successfully. ID: {json_object[0]['order_id']}")
                                processed_list.append(order_id)
                                order_id = json_object[0]['order_id'] + api_info["id"]
                                exit_buy_pending_orders[order_id] = order
                                break
                            else:
                                logger.error(f"[-] thread_exit_orders: BUY: Order response missing 'order_id', ID: {order_id}, Details: {order}, acc:{api_info['id']}")
                                time.sleep(1)
                        except requests.exceptions.RequestException as e:
                            logger.error(f"[-] thread_exit_orders: BUY: FastAPI request failed: {e}, ID: {order_id}, Details: {order}, acc:{api_info['id']}")
                            time.sleep(1)

                for order_id in processed_list:
                    if order_id in exit_buy_todo_orders:
                        del exit_buy_todo_orders[order_id]

                logger.info(f"[-] thread_exit_orders: {api_info['id']} ### Finished the step - placing orders to exit buy orders")

                processed_list = []
                for p_order_id, p_order in exit_buy_pending_orders.items():
                    p_order_only_id = p_order_id.replace(api_info["id"], "")
                    for l_order in json_object_order_list:
                        if l_order['order_id'] == p_order_only_id and l_order['order_status'] == "FILLED_ALL":

                            logger.info(f"[-] thread_exit_orders: BUY: {p_order_id} is FILLED_ALL, acc:{api_info['id']}, order:{p_order}")
                            
                            processed_list.append(p_order_id)

                for order_id in processed_list:
                    if order_id in exit_buy_pending_orders:
                        del exit_buy_pending_orders[order_id]
            
                logger.info(f"[-] thread_exit_orders: {api_info['id']} ### Finished the step - confirming exit buy orders")

                # Naked Strategy - handle entry order
                processed_list = []
                naked_todo_orders_copy = naked_todo_orders.copy()
                for order_id, order in naked_todo_orders_copy.items():
                    if order['api_key'] == api_key:
                        flag_in_exiting = False
                        for exit_order_id, exit_order in naked_exit_todo_orders.items():
                            if exit_order['symbol'].find(order['symbol']) != -1 and exit_order['api_key'] == api_key:
                                flag_in_exiting = True
                                break
                        if flag_in_exiting == False:
                            is_success = send_naked_order_limit(order, api_key)
                            if is_success:
                                processed_list.append(order_id)

                for order_id in processed_list:
                    del naked_todo_orders[order_id]

                # Covered Strategy - handle entry order
                processed_list = []
                buy_todo_orders_copy = buy_todo_orders.copy()
                for order_id, order in buy_todo_orders_copy.items():
                    if order['api_key'] == api_key:
                        flag_in_exiting = False
                        for exit_order_id, exit_order in naked_exit_todo_orders.items():
                            if exit_order['symbol'].find(order['symbol']) != -1 and exit_order['api_key'] == api_key:
                                flag_in_exiting = True
                                break
                        
                        if flag_in_exiting == False:
                            retry_buy_order(order['multiple_exit_level'], order['symbol'], order['date'], order['option'], order['strikeprice'], order['roundingprice'], order['multiple_exit_level'], order['api_key'], order['order_tag'], order['multiple_exit_level'], order['quantity'], order['type'])
                            processed_list.append(order_id)

                for order_id in processed_list:
                    del buy_todo_orders[order_id]

                logger.info(f"[-] thread_exit_orders: {api_info['id']} finished")
            time.sleep(10)
        except Exception as e:
            logger.error(f"[-] thread_exit_orders: error: {e}")
            time.sleep(10)

    logger.info("[-] thread_exit_orders: end")

def exit_positions(data, symbol, action, api_key, ordertag):
    option = "C" if action == "exit_calls" else "P" if action == "exit_puts" else None
    if not option:
        logger.error(f"[-] exit_positions: Invalid exit action: {data}")
        return jsonify({"error": "Invalid exit action"}), 403

    base_symbol = symbol
    
    if ordertag == 0:
        copy_orders = orders.copy()
        sell_selected_items = {
            order_id: order for order_id, order in copy_orders.items()
            if order['symbol'].startswith(f'US.{base_symbol}') and order['symbol'][9 + len(base_symbol)] == option and order['side'] == "SELL" and order['api_key'] == api_key
        }

        if len(sell_selected_items) == 0:
            return jsonify({"success": "Exited positions"}), 200

        for order_id, order in sell_selected_items.items():
            if order_id in orders:
                del orders[order_id]
            exit_sell_todo_orders[order_id] = order
        
        copy_orders = orders.copy()
        buy_to_exit_orders = {
            order_id: order for order_id, order in copy_orders.items()
            if order['symbol'].startswith(f'US.{base_symbol}') and order['symbol'][9 + len(base_symbol)] == option and order['side'] == "BUY" and order['api_key'] == api_key
        }
        
        for order_id, order in buy_to_exit_orders.items():
            if order_id in orders:
                del orders[order_id]
            exit_buy_todo_orders[order_id] = order
    elif ordertag > 0:
        copy_orders = orders.copy()
        to_exit_orders = {
            order_id: order for order_id, order in copy_orders.items()
            if order['symbol'].startswith(f'US.{base_symbol}') and order['symbol'][9 + len(base_symbol)] == option and order['api_key'] == api_key and order['order_tag'] == ordertag
        }
        
        for order_id, order in to_exit_orders.items():
            if order_id in orders:
                del orders[order_id]
            naked_exit_todo_orders[order_id] = order
    
    return jsonify({"success": "Exited positions"}), 200

# Function to retry buy order with reduced multiple
def retry_buy_order(fixed_multiple, symbol, datetmp, option_value, strikeprice, roundingprice, multiple_value, api_key, ordertag, multiple_exit_level, quantity, type):
    global buy_pending_orders
    global sell_todo_orders

    headers = {"Content-Type": "application/json", "api-key": api_key}

    if fixed_multiple < multiple_value - 2:
        logger.error("Buy order failed after 3 attempts")
        return jsonify({"error": "Buy order failed after 3 attempts"}), 500

    code_name = get_codename(symbol, datetmp, option_value, strikeprice, roundingprice, fixed_multiple)
    if not code_name:
        logger.error("Invalid option type")
        return jsonify({"error": "Invalid option type"}), 400

    buy_order_data = {
        "symbol": code_name,
        "quantity": quantity,
        "side": "BUY",
        "type": type,
        "api_key": api_key,
        "multiple_exit_level": multiple_exit_level,
        "order_tag": ordertag,
    }

    try:
        fastapi_url = "http://" + api_keys[api_key]["opend-address"]
        response = requests.post(fastapi_url, json=buy_order_data, headers=headers)
        response.raise_for_status()
        response_json = response.json()
        time.sleep(2)

        if "Open position failed" in str(response_json):
            if "due to the insufficient liquidity" in str(response_json):
                logger.error(f"[-] forward_order: error of placing buy order: {response_json}, acc:{api_keys[api_key]['id']}, order:{buy_order_data}")
                ask_volume = get_ask_volume([buy_order_data['symbol']], api_key)
                if ask_volume[buy_order_data['symbol']] > 0 and ask_volume[buy_order_data['symbol']] >= int(buy_order_data['quantity']):
                    logger.info(f"[-] forward_order: ask volume of {buy_order_data['symbol']} is greater than 0 and greater than or equal to the quantity, so retry, acc:{api_keys[api_key]['id']}, order:{buy_order_data}")
                    time.sleep(10)
                    return retry_buy_order(fixed_multiple, symbol, datetmp, option_value, strikeprice, roundingprice, multiple_value, api_key, ordertag, multiple_exit_level, quantity, type)
                else:
                    logger.error(f"[-] forward_order: bid volume of {buy_order_data['symbol']} is less than quantity, acc:{api_keys[api_key]['id']}, order:{buy_order_data}")
            else:
                logger.error(f"[-] forward_order: Open position failed: {response_json} : {code_name} : {fixed_multiple}")
            
            return retry_buy_order(fixed_multiple - 1, symbol, datetmp, option_value, strikeprice, roundingprice, multiple_value, api_key, ordertag, multiple_exit_level, quantity, type)

        try:
            json_object = json.loads(response_json)
        except Exception as e:
            logger.error(f"[-] forward_order: error {e} : {code_name} : {fixed_multiple}")
            return retry_buy_order(fixed_multiple - 1, symbol, datetmp, option_value, strikeprice, roundingprice, multiple_value, api_key, ordertag, multiple_exit_level, quantity, type)

        order_id = json_object[0]["order_id"] + api_keys[api_key]["id"]
        
        buy_pending_orders[order_id] = buy_order_data

        # Now send the original sell order
        sell_code_name = get_codename(symbol, datetmp, option_value, strikeprice, roundingprice, 0)
        sell_order_data = {
            "symbol": sell_code_name,
            "quantity": quantity,
            "side": "SELL",
            "type": type,
            "api_key": api_key,
            "multiple_exit_level": multiple_exit_level,
            "order_tag": ordertag,
        }

        sell_todo_orders[order_id] = sell_order_data

        logger.info(f"Buy pending order placed. Order ID: {order_id} : {code_name} : {fixed_multiple}")
        return response_json, response.status_code
    except requests.exceptions.RequestException as e:
        logger.error(f"Buy order failed: {e} : {code_name}")
        return jsonify({"error": str(e)}), 500

def send_order_limit(order_data, api_key):
    headers = {"Content-Type": "application/json", "api-key": api_key}
    try:
        fastapi_url = "http://" + api_keys[api_key]["opend-address"]
        response = requests.post(fastapi_url, json=order_data, headers=headers)
        response.raise_for_status()
        response_json = response.json()
        time.sleep(2)

        
        if "Open position failed" in str(response_json):
            logger.error(f"send_naked_order_limit: Open position failed: {response_json} : {order_data['symbol']}")
            return False

        try:
            json_object = json.loads(response_json)
        except Exception as e:
            logger.error(f"[-] send_naked_order_limit: error {e} : {order_data['symbol']}")
            return False

        order_id = json_object[0]["order_id"] + api_keys[api_key]["id"]
        naked_pending_orders[order_id] = order_data

        logger.info(f"[-] send_naked_order_limit: Buy pending order placed. Order ID: {order_id} : {order_data['symbol']}")

        return True
    except Exception as e:
        logger.error(f"[-] send_naked_order_limit: error {e} : {order_data['symbol']}")
        return False


def send_naked_order_limit(order_data, api_key):
    middle_price_list = get_middle_price([order_data['symbol']], api_key)

    if not order_data['symbol'] in middle_price_list:
        logger.error(f"[-] send_naked_order_limit: middle price of {order_data['symbol']} is not in middle_price_list, acc:{api_keys[api_key]['id']}, order:{order_data}")
        return False
    
    middle_price = middle_price_list[order_data['symbol']]
    order_data['type'] = "NORMAL"

    if order_data['side'] == "BUY":
        order_data['price'] = middle_price + 0.1
        while send_order_limit(order_data, api_key) == False:
            time.sleep(10)
            logger.info(f"[-] send_naked_order_limit: retrying to send order, acc:{api_keys[api_key]['id']}, order:{order_data}")
            order_data['price'] = order_data['price'] + 0.1
        return True
    else:
        bid_price_list = get_bid_price([order_data['symbol']], api_key)
        if order_data['symbol'] in bid_price_list:
            order_data['price'] = bid_price_list[order_data['symbol']] - 0.1
        else:
            logger.error(f"[-] send_naked_order_limit: bid price of {order_data['symbol']} is not in bid_price_list, acc:{api_keys[api_key]['id']}, order:{order_data}")
            return False

def forward_order1(data, api_key):
    if api_key not in api_keys:
        logger.error(f"Invalid API key: {api_key}")
        return jsonify({"error": "Invalid API key"}), 403

    action = data.get("action")
    symbol = data.get("symbol", "")
    ordertag = int(data.get("order_tag", -1))

    if action and symbol:
        return exit_positions(data, symbol, action, api_key, ordertag)

    # Extract relevant order data
    datetmp = data.get('date', '')
    option_value = data.get("option", '')
    roundingprice = int(data.get("RoundingPrice", 0))
    stopLossLevel = int(data.get("StopLossLevel", 0))
    multiple_exit_level = float(data.get("Method", 0.0))
    side = data.get("side", '')
    
    multiple_value = G_FIXED_MULTIPLE
    if stopLossLevel:
        multiple_value = stopLossLevel
    
    if ordertag == -1:
        logger.error("Missing order tag")
        return jsonify({"error": "Missing order tag"}), 400
    
    # Covered Strategy (ordertag = 0)
    if ordertag == 0 and (side != "SELL" or not all([datetmp, symbol, roundingprice])):
        logger.error("Missing or invalid fields in request")
        return jsonify({"error": "Missing or invalid fields"}), 400

    # Naked Strategy (ordertag  = 1)
    if ordertag > 0 and not all([datetmp, symbol]):
        logger.error("Missing or invalid fields in request")
        return jsonify({"error": "Missing or invalid fields"}), 400
    
    try:
        strikeprice = int(data.get("strikeprice", ''))
    except ValueError:
        logger.error("Invalid strike price")
        return jsonify({"error": "Invalid strike price"}), 400

    buy_code_name = get_codename(symbol, datetmp, option_value, strikeprice, roundingprice, multiple_value, ordertag)
    if not buy_code_name:
        logger.error("Invalid option type")
        return jsonify({"error": "Invalid option type"}), 400

    headers = {"Content-Type": "application/json", "api-key": api_key}

    flag_in_exiting = False
    if ordertag == 0:
        for order_id, order in exit_sell_todo_orders.items():
            if order['symbol'].find(symbol) != -1 and order['api_key'] == api_key:
                logger.info(f"[-] forward_order1: {symbol} is in exit_sell_todo_orders, acc:{api_keys[api_key]['id']}, order:{order}")
                flag_in_exiting = True
                break
    
        if flag_in_exiting == False:
            for order_id, order in exit_buy_todo_orders.items():
                if order['symbol'].find(symbol) != -1 and order['api_key'] == api_key:
                    logger.info(f"[-] forward_order1: {symbol} is in exit_buy_todo_orders, acc:{api_keys[api_key]['id']}, order:{order}")
                    flag_in_exiting = True
                    break
    elif ordertag > 0:
        for order_id, order in naked_exit_todo_orders.items():
            if order['symbol'].find(symbol) != -1 and order['api_key'] == api_key:
                logger.info(f"[-] forward_order1: {symbol} is in naked_exit_todo_orders, acc:{api_keys[api_key]['id']}, order:{order}")
                flag_in_exiting = True
                break
    
    # Naked Strategy
    if ordertag > 0:
        code_name = buy_code_name
        order_data = {
            "symbol": code_name,
            "quantity": data.get("quantity"),
            "side": side,
            "type": data.get("type"),
            "api_key": api_key,
            "order_tag": ordertag,
            "multiple_exit_level": multiple_exit_level,
		}
        
        if flag_in_exiting == True:
            now_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            naked_todo_orders[now_time] = order_data
            return jsonify({"success": "naked order is in exiting, so added to naked_todo_orders"}), 200

        while True:
            is_success = send_naked_order_limit(order_data, api_key)
            if is_success:
                return jsonify({"success": "naked order is not in exiting, so sent to naked_pending_orders"}), 200
            else:
                time.sleep(10)

    # Covered Strategy
    if flag_in_exiting == True:
        order_data = {}
        order_data['symbol'] = symbol
        order_data['quantity'] = data.get("quantity")
        order_data['side'] = side
        order_data['type'] = data.get("type")
        order_data['api_key'] = api_key
        order_data['multiple_exit_level'] = multiple_exit_level
        order_data['order_tag'] = ordertag
        
        now_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        buy_todo_orders[now_time] = order_data
        return jsonify({"success": "buy order is in exiting, so added to buy_todo_orders"}), 200
    else:
        buy_response_json, buy_response_status = retry_buy_order(multiple_value, symbol, datetmp, option_value, strikeprice, roundingprice, multiple_value, api_key, ordertag, multiple_exit_level, data.get("quantity"), data.get("type"))

    return buy_response_json, buy_response_status


@app.route("/", methods=["POST"])
def forward_order():
    data = request.json
    api_key = data.get("api_key")
    if not api_key:
        logger.error(f"Missing API key: {data}")
        return jsonify({"error": "Missing API key"}), 403
    
    logger.info(f"request data: {data}")

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
    data = request.json
    api_key = data.get("api_key")
    if not api_key:
        logger.error(f"Missing API key: {data}")
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


@app.route("/list_memory_orders", methods=["GET"])
def list_memory_orders():
    memory_orders = {}
    memory_orders['orders'] = orders
    memory_orders['buy_pending_orders'] = buy_pending_orders
    memory_orders['exit_sell_todo_orders'] = exit_sell_todo_orders
    memory_orders['exit_sell_pending_orders'] = exit_sell_pending_orders
    memory_orders['exit_buy_todo_orders'] = exit_buy_todo_orders
    memory_orders['exit_buy_pending_orders'] = exit_buy_pending_orders
    memory_orders['naked_pending_orders'] = naked_pending_orders
    memory_orders['naked_exit_todo_orders'] = naked_exit_todo_orders

    return jsonify(memory_orders), 200
    
def init_background_tasks():
    if check_thread_status():
        return
    
    executor.submit(thread_exit_orders)
    
def check_thread_status():
    """Check if thread_exit_orders is running"""
    for thread in threading.enumerate():
        if thread.name == "thread_exit_orders":
            return True
    return False

def get_snapshot(code_list, api_key):
    opend_address = "http://" + api_keys[api_key]["opend-address"]
    headers = {"Content-Type": "application/json", "api-key": api_key}
    
    json_params = {
        "symbol_list": code_list
    }

    while True:
        try:
            response = requests.post(
                opend_address + "/get_snapshot", 
                json=json_params,
                headers=headers
            )
            response.raise_for_status()
            json_object = response.json()  # Response is already JSON parsed

            # Check if response has the expected structure
            if 'snapshot' not in json_object:
                logger.error(f"[-] get_snapshot: unexpected response format: {json_object}")
                time.sleep(2)
                continue

            logger.info(f"[-] get_snapshot: Successfully got snapshot: {json_object['snapshot']}")
            return json_object['snapshot']

        except requests.exceptions.RequestException as e:
            logger.error(f"[-] get_bid_price: request error: {e}")
            logger.error(f"Request params: {json_params}")
            time.sleep(2)
            continue
        except Exception as e:
            logger.error(f"[-] get_bid_price: unexpected error: {e}")
            logger.error(f"Response content: {response.text if 'response' in locals() else 'No response'}")
            time.sleep(2)
            continue

def get_bid_price(code_list, api_key):
    snapshot = get_snapshot(code_list, api_key)
    
    bid_price_list = {}
    for snapshot_item in snapshot:
        if snapshot_item['code'] in code_list:
            bid_price_list[snapshot_item['code']] = snapshot_item['bid_price']
            
    logger.info(f"[-] get_bid_price: Successfully got bid prices: {bid_price_list}")
    return bid_price_list

def get_ask_price(code_list, api_key):
    snapshot = get_snapshot(code_list, api_key)
    
    ask_price_list = {}
    for snapshot_item in snapshot:
        if snapshot_item['code'] in code_list:
            ask_price_list[snapshot_item['code']] = snapshot_item['ask_price']
            
    logger.info(f"[-] get_ask_price: Successfully got ask prices: {ask_price_list}")
    return ask_price_list
    
def get_middle_price(code_list, api_key):
    snapshot = get_snapshot(code_list, api_key)
    
    middle_price_list = {}
    for snapshot_item in snapshot:
        if snapshot_item['code'] in code_list:
            middle_price_list[snapshot_item['code']] = (snapshot_item['bid_price'] + snapshot_item['ask_price']) / 2

    logger.info(f"[-] get_middle_price: Successfully got middle prices: {middle_price_list}")
    return middle_price_list

def get_ask_volume(code_list, api_key):
    snapshot = get_snapshot(code_list, api_key)
    
    ask_volume_list = {}
    for snapshot_item in snapshot:
        if snapshot_item['code'] in code_list:
            ask_volume_list[snapshot_item['code']] = snapshot_item['ask_vol']
            
    logger.info(f"[-] get_ask_volume: Successfully got ask volumes: {ask_volume_list}")
    return ask_volume_list

def get_bid_volume(code_list, api_key):
    snapshot = get_snapshot(code_list, api_key)
    
    bid_volume_list = {}
    for snapshot_item in snapshot:
        if snapshot_item['code'] in code_list:
            bid_volume_list[snapshot_item['code']] = snapshot_item['bid_vol']
            
    logger.info(f"[-] get_bid_volume: Successfully got bid volumes: {bid_volume_list}")
    return bid_volume_list

if __name__ == "__main__":
    app.run(host="0.0.0.0")
    load_orders_from_jsonfile()
    init_background_tasks()

