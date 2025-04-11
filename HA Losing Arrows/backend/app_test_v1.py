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
    "a9f8f651-4d3e-46f1-8d6b-c2f1f3b76429": {"id":"ryanoakes-paper", "opend-address":"34.71.74.2"}, 
    "7d4f8a12-1b3c-45e9-9b1a-2a6e0fc2e975": {"id":"enlixir-real", "opend-address":"34.73.25.174"}, 
    "d45a6e79-927b-4f3e-889d-3c65a8f0738c": {"id":"enlixir-paper", "opend-address":"34.73.25.174"}
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

executor = ThreadPoolExecutor(max_workers=1)

def get_codename(symbol, datetmp, option_value, strikeprice, roundingprice, fixed_multiple):
    bid_price = strikeprice + (roundingprice * fixed_multiple) if option_value == "call" else strikeprice - (roundingprice * fixed_multiple)
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
    global order_pair_map

    total_orders = {}
    total_orders['orders'] = orders
    total_orders['sell_todo_orders'] = sell_todo_orders
    total_orders['buy_pending_orders'] = buy_pending_orders
    total_orders['exit_sell_todo_orders'] = exit_sell_todo_orders
    total_orders['exit_sell_pending_orders'] = exit_sell_pending_orders
    total_orders['exit_buy_todo_orders'] = exit_buy_todo_orders
    total_orders['exit_buy_pending_orders'] = exit_buy_pending_orders

    count = len(sell_todo_orders) + len(buy_pending_orders) + len(exit_sell_todo_orders) + len(exit_sell_pending_orders) + len(exit_buy_todo_orders) + len(exit_buy_pending_orders)
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
    order_pair_map = total_orders['order_pair_map']
    logger.info(f"[-] load_orders_from_jsonfile: Orders loaded")


def merge_orders(input_data, max_quantity=5):
  # Step 1: Group and sum quantities by symbol, side, and type
  grouped_data = defaultdict(lambda: {"symbol": None, "quantity": 0, "side": None, "type": None, "api_key": None, "original_ids": []})

  for key, value in input_data.items():
      # Use (symbol, side, type) as the grouping key
      group_key = (value["symbol"], value["side"], value["type"])
      
      if grouped_data[group_key]["symbol"] is None:
          grouped_data[group_key]["symbol"] = value["symbol"]
          grouped_data[group_key]["side"] = value["side"]
          grouped_data[group_key]["type"] = value["type"]
          grouped_data[group_key]["api_key"] = value["api_key"]
      
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
                  "api_key": item["api_key"]
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
                  "api_key": item["api_key"]
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
                                if order['symbol'] in symbol_last_price and 'entry_price' in order:
                                    if symbol_last_price[order['symbol']] > 1.3 * order['entry_price']:
                                        logger.info(f"[-] thread_exit_orders: SELL: {order_id} is 1.3x entry price. symbol:{order['symbol']}")
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
                    for l_order in json_object_order_list:
                        if l_order['order_id'] == p_order_only_id and l_order['order_status'] == "FILLED_ALL":
                            logger.info(f"[-] thread_exit_orders: (buy order) {p_order_id} is FILLED_ALL")
                            if "try_count" in p_order and p_order["try_count"] > 10:
                                logger.error(f"[-] thread_exit_orders: try_count of placing sell order is greater than 10, acc:{api_info['id']}, order:{p_order}")
                                processed_list.append(p_order_id)
                                break

                            try:
                                sell_response = requests.post(opend_address, json=p_order, headers=headers)
                                sell_response.raise_for_status()
                                sell_response_json = sell_response.json()
                                time.sleep(2)

                                if "Open position failed" in str(sell_response_json):
                                    logger.error(f"[-] thread_exit_orders: error of placing sell order: {sell_response_json}, acc:{api_info['id']}, order:{p_order}")
                                    continue

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
                            order = orders[p_order_id]
                            order['entry_price'] = l_order['dealt_avg_price']
                            orders[p_order_id] = order
                            del sell_pending_orders[p_order_id]
                            if order['symbol'] not in symbol_list:
                                symbol_list.append(order['symbol'])
                
                logger.info(f"[-] thread_exit_orders: {api_info['id']} ### Finished the step - confirming sell orders")

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
                logger.info(f"[-] thread_exit_orders: {api_info['id']} finished")
            time.sleep(10)
        except Exception as e:
            logger.error(f"[-] thread_exit_orders: error: {e}")
            time.sleep(10)

    logger.info("[-] thread_exit_orders: end")

def exit_positions(data, symbol, action, api_key):
    option = "C" if action == "exit_calls" else "P" if action == "exit_puts" else None
    if not option:
        logger.error(f"[-] exit_positions: Invalid exit action: {data}")
        return jsonify({"error": "Invalid exit action"}), 403

    base_symbol = symbol

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
        global buy_pending_orders
        global sell_todo_orders

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
    memory_orders['buy_pending_orders'] = buy_pending_orders
    memory_orders['exit_sell_todo_orders'] = exit_sell_todo_orders
    memory_orders['exit_sell_pending_orders'] = exit_sell_pending_orders
    memory_orders['exit_buy_todo_orders'] = exit_buy_todo_orders
    memory_orders['exit_buy_pending_orders'] = exit_buy_pending_orders

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


def get_bid_price(code_list, api_key):
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
                logger.error(f"[-] get_bid_price: unexpected response format: {json_object}")
                time.sleep(2)
                continue

            bid_price_list = {}
            for snapshot_item in json_object['snapshot']:
                if snapshot_item['code'] in code_list:
                    bid_price_list[snapshot_item['code']] = snapshot_item['bid_price']
            
            logger.info(f"[-] get_bid_price: Successfully got bid prices: {bid_price_list}")
            return bid_price_list

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

def get_ask_price(code_list, api_key):
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
                logger.error(f"[-] get_ask_price: unexpected response format: {json_object}")
                time.sleep(2)
                continue

            ask_price_list = {}
            for snapshot_item in json_object['snapshot']:
                if snapshot_item['code'] in code_list:
                    ask_price_list[snapshot_item['code']] = snapshot_item['ask_price']
            
            logger.info(f"[-] get_ask_price: Successfully got ask prices: {ask_price_list}")
            return ask_price_list

        except requests.exceptions.RequestException as e:
            logger.error(f"[-] get_ask_price: request error: {e}")
            logger.error(f"Request params: {json_params}")
            time.sleep(2)
            continue
        except Exception as e:
            logger.error(f"[-] get_ask_price: unexpected error: {e}")
            logger.error(f"Response content: {response.text if 'response' in locals() else 'No response'}")
            time.sleep(2)
            continue

if __name__ == "__main__":
    app.run(host="0.0.0.0")
    load_orders_from_jsonfile()
    init_background_tasks()

