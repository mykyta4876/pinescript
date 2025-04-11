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
    "fb7c1234-25ae-48b6-9f7f-9b3f98d76543": {"id":"ryanoakes-real", "opend-address":"34.69.232.70"}, 
    "a9f8f651-4d3e-46f1-8d6b-c2f1f3b76429": {"id":"ryanoakes-paper", "opend-address":"34.69.232.70"}, 
    "7d4f8a12-1b3c-45e9-9b1a-2a6e0fc2e975": {"id":"enlixir-real", "opend-address":"34.172.46.17"}, 
    "d45a6e79-927b-4f3e-889d-3c65a8f0738c": {"id":"enlixir-paper", "opend-address":"34.172.46.17"}
    }

# In-memory store for orders
orders = {}
sell_todo_orders = {}
sell_pending_orders = {}
buy_pending_orders = {}
exit_sell_todo_orders = {}
exit_sell_pending_orders = {}
exit_buy_todo_orders = {}
exit_buy_pending_orders = {}
order_pair_map = {}

## Naked Strategy
naked_pending_orders = {}
naked_exit_todo_orders = {}

executor = ThreadPoolExecutor(max_workers=1)

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

def thread_exit3(order):
    global orders

    entry_time = order['entry_time']
    entry_price = order['entry_price']
    api_key = order['api_key']
    api_info = api_keys[api_key]
    stop_loss_order_id = order['stop_loss_order_id']
    while True:
        time.sleep(1)
        now_time = datetime.now().astimezone(pytz.timezone('US/Eastern'))
        if now_time > entry_time + timedelta(minutes=1):
            break

    current_price = get_bid_price(order['symbol'], api_key)
    if current_price <= entry_price + entry_price * order['stop_loss_multiple'] / 100:
        return False
    
    if not stop_loss_order_id in orders:
        logger.info(f"[-] thread_exit3: stop_loss_order_id {stop_loss_order_id} is not in orders, skip")
        return False

    opend_address = "http://" + api_info["opend-address"]
    headers = {"Content-Type": "application/json", "api-key": api_key}
    sell_response = requests.post(opend_address, json=order, headers=headers)
    sell_response.raise_for_status()
    sell_response_json = sell_response.json()
    time.sleep(2)

    try:
        sell_json_object = json.loads(sell_response_json)
    except Exception as e:
        logger.error(f"[-] thread_exit3: error: {e}, exit order of {stop_loss_order_id}, acc:{api_info['id']}, order:{order}")
        return False

    if "order_id" in sell_json_object[0]:
        if stop_loss_order_id in orders:
            del orders[stop_loss_order_id]
        logger.info(f"[-] thread_exit3: exit order of {stop_loss_order_id} is placed successfully")
    else:
        logger.error(f"[-] thread_exit3: exit order of {stop_loss_order_id} is failed")
        return False
    
    return True

    
    
def merge_orders(input_data, max_quantity=5):
  # Step 1: Group and sum quantities by symbol, side, and type
  grouped_data = defaultdict(lambda: {"symbol": None, "quantity": 0, "side": None, "type": None, "api_key": None, "order_tag": None, "original_ids": []})

  for key, value in input_data.items():
      # Use (symbol, side, type) as the grouping key
      group_key = (value["symbol"], value["side"], value["type"], value["api_key"], value["order_tag"])
      
      if grouped_data[group_key]["symbol"] is None:
          grouped_data[group_key]["symbol"] = value["symbol"]
          grouped_data[group_key]["side"] = value["side"]
          grouped_data[group_key]["type"] = value["type"]
          grouped_data[group_key]["api_key"] = value["api_key"]
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

    threading.current_thread().name = "thread_exit_orders"
    logger.info(f"[-] thread_exit_orders: start")
    while True:
        now_time = datetime.now().astimezone(pytz.timezone('US/Eastern'))
        if now_time.hour < 9:
            time.sleep(10)
            continue
        
        if now_time.hour == 9 and now_time.minute == 25 and now_time.second > 30 and now_time.second < 45:
            load_orders_from_jsonfile()

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
            
            # confirm the pending naked orders
            naked_todo_orders_copy = naked_pending_orders.copy()
            
            processed_list = []
            for p_order_id, p_order in naked_todo_orders_copy.items():
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
            naked_exit_todo_orders_copy_merged = merge_orders(naked_exit_todo_orders_copy, 10)
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

            # confirm the pending sell orders
            sell_todo_orders_copy = sell_todo_orders.copy()
            
            processed_list = []
            for p_order_id, p_order in sell_todo_orders_copy.items():
                p_order_only_id = p_order_id.replace(api_keys[api_key]["id"], "")
                for l_order in json_object_order_list:
                    if l_order['order_id'] == p_order_only_id and l_order['order_status'] == "FILLED_ALL":
                        logger.info(f"[-] thread_exit_orders: SELL: {p_order_id} is FILLED_ALL")
                        
                        try:
                            sell_response = requests.post(opend_address, json=p_order, headers=headers)
                            sell_response.raise_for_status()
                            sell_response_json = sell_response.json()
                            time.sleep(2)

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

                            if p_order['order_tag'] == 1:
                                sell_pending_orders[order_id] = p_order
                                
                            break
                        except requests.exceptions.RequestException as e:
                            logger.error(f"[-] sell_order: Sell order failed: {e}, sell order of {p_order_id}, acc:{api_info['id']}, order:{p_order}")
                            break

            for order_id in processed_list:
                if order_id in sell_todo_orders:
                    del sell_todo_orders[order_id]
                if order_id in buy_pending_orders:
                    del buy_pending_orders[order_id]

            # confirm the pending sell orders
            processed_list = []
            for order_id, order in sell_pending_orders.items():
                order_only_id = order_id.replace(api_keys[api_key]["id"], "")
                for l_order in json_object_order_list:
                    if l_order['order_id'] == order_only_id and l_order['order_status'] == "FILLED_ALL":
                        logger.info(f"[-] thread_exit_orders: SELL: {order_id} is FILLED_ALL {l_order}")
                        order['stop_loss_order_id'] = order_id
                        order['entry_price'] = l_order['dealt_avg_price']
                        order['entry_time'] = datetime.strptime(l_order['updated_time'], '%Y-%m-%d %H:%M:%S.%f')
                        processed_list.append(order_id)
                        threading.Thread(target=thread_exit3, args=(order,)).start()
                        break

            for order_id in processed_list:
                if order_id in sell_pending_orders:
                    del sell_pending_orders[order_id]

            exit_sell_todo_orders_copy = exit_sell_todo_orders.copy()
            exit_sell_todo_orders_copy_merged = merge_orders(exit_sell_todo_orders_copy, 10)
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
                if order_id in exit_sell_pending_orders:
                    del exit_sell_pending_orders[order_id]

            if len(exit_sell_todo_orders) > 0:
                continue

            exit_buy_todo_orders_copy = exit_buy_todo_orders.copy()
            exit_buy_todo_orders_copy_merged = merge_orders(exit_buy_todo_orders_copy, 10)
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
                            order_id = json_object[0]['order_id'] + api_keys[api_key]["id"]
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

            processed_list = []
            for p_order_id, p_order in exit_buy_pending_orders.items():
                p_order_only_id = p_order_id.replace(api_keys[api_key]["id"], "")
                for l_order in json_object_order_list:
                    if l_order['order_id'] == p_order_only_id and l_order['order_status'] == "FILLED_ALL":

                        logger.info(f"[-] thread_exit_orders: BUY: {p_order_id} is FILLED_ALL, acc:{api_info['id']}, order:{p_order}")
                        
                        processed_list.append(p_order_id)

            for order_id in processed_list:
                if order_id in exit_buy_pending_orders:
                    del exit_buy_pending_orders[order_id]
        
            logger.info(f"[-] thread_exit_orders: {api_info['id']} finished")
        time.sleep(10)

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
            if order['symbol'].startswith(f'US.{base_symbol}') and order['symbol'][9 + len(base_symbol)] == option and order['side'] == "SELL" and order['api_key'] == api_key and order['order_tag'] == ordertag
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
            if order['symbol'].startswith(f'US.{base_symbol}') and order['symbol'][9 + len(base_symbol)] == option and order['side'] == "BUY" and order['api_key'] == api_key and order['order_tag'] == ordertag
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
    pips = int(data.get("Pips", 0))
    delay = int(data.get("Delay", 0))
    side = data.get("side", '')
    
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
    
    if ordertag == 0 and (side != "SELL" or not all([datetmp, symbol, roundingprice])):
        logger.error("Missing or invalid fields in request")
        return jsonify({"error": "Missing or invalid fields"}), 400

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

    headers = {"Content-Type": "application/json", "api-key": api_key}

    # Naked Strategy
    if ordertag > 1:
        code_name = buy_code_name
        order_data = {
            "symbol": code_name,
            "quantity": data.get("quantity"),
            "side": side,
            "type": data.get("type"),
            "api_key": api_key,
            "order_tag": ordertag,
		}
        
        try:
            fastapi_url = "http://" + api_keys[api_key]["opend-address"]
            response = requests.post(fastapi_url, json=order_data, headers=headers)
            response.raise_for_status()
            response_json = response.json()
            time.sleep(2)

            
            if "Open position failed" in str(response_json):
                logger.error(f"forward_order: Naked: Open position failed: {response_json} : {code_name}")
                return jsonify({"error": "Open position failed"}), 500

            try:
                json_object = json.loads(response_json)
            except Exception as e:
                logger.error(f"[-] forward_order: Naked: error {e} : {code_name}")
                return jsonify({"error": str(e)}), 500

            order_id = json_object[0]["order_id"] + api_keys[api_key]["id"]
            naked_pending_orders[order_id] = order_data

            logger.info(f"[-] forward_order: Naked: Buy pending order placed. Order ID: {order_id} : {code_name}")

            return response_json, response.status_code
        except Exception as e:
            logger.error(f"[-] forward_order: Naked: error {e} : {code_name}")
            return jsonify({"error": str(e)}), 500

    if ordertag != 0 and ordertag != 1:
        logger.error(f"[-] forward_order: Invalid order tag: {data}")
        return jsonify({"error": "Invalid order tag"}), 400
    
    # Covered Strategy
    buy_order_data = {
        "symbol": buy_code_name,
        "quantity": data.get("quantity"),
        "side": "BUY",
        "type": data.get("type"),
        "api_key": api_key,
        "order_tag": ordertag,
    }

    # Function to retry buy order with reduced multiple
    def retry_buy_order(fixed_multiple):
        global buy_pending_orders
        global sell_todo_orders

        if fixed_multiple < multiple_value - 2:
            logger.error("Buy order failed after 3 attempts")
            return jsonify({"error": "Buy order failed after 3 attempts"}), 500

        code_name = get_codename(symbol, datetmp, option_value, strikeprice, roundingprice, fixed_multiple, ordertag)
        if not code_name:
            logger.error("Invalid option type")
            return jsonify({"error": "Invalid option type"}), 400

        buy_order_data["symbol"] = code_name
        try:
            fastapi_url = "http://" + api_keys[api_key]["opend-address"]
            response = requests.post(fastapi_url, json=buy_order_data, headers=headers)
            response.raise_for_status()
            response_json = response.json()
            time.sleep(2)

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
            sell_code_name = get_codename(symbol, datetmp, option_value, strikeprice, roundingprice, 0, ordertag)
            sell_order_data = {
                "symbol": sell_code_name,
                "quantity": data.get("quantity"),
                "side": "SELL",
                "type": data.get("type"),
                "api_key": api_key,
                "order_tag": ordertag,
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
    load_orders_from_jsonfile()
    init_background_tasks()
