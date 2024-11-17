from collections import defaultdict

input_data = {
  "7899521336893191919ryanoakes-real": {
    "symbol": "US.IWM241029P213000",
    "quantity": "1",
    "side": "BUY",
    "type": "MARKET",
    "api_key": "fb7c1234-25ae-48b6-9f7f-9b3f98d76543"
  },
  "2151311791827974324ryanoakes-real": {
    "symbol": "US.IWM241029P220000",
    "quantity": "1",
    "side": "SELL",
    "type": "MARKET",
    "api_key": "fb7c1234-25ae-48b6-9f7f-9b3f98d76543"
  },
  "705162805877925954ryanoakes-real": {
    "symbol": "US.IWM241029P214000",
    "quantity": "1",
    "side": "BUY",
    "type": "MARKET",
    "api_key": "fb7c1234-25ae-48b6-9f7f-9b3f98d76543"
  },
  "3180481744188611542ryanoakes-real": {
    "symbol": "US.IWM241029P221000",
    "quantity": "1",
    "side": "SELL",
    "type": "MARKET",
    "api_key": "fb7c1234-25ae-48b6-9f7f-9b3f98d76543"
  },
  "6002092951538682792ryanoakes-real": {
    "symbol": "US.IWM241029P215000",
    "quantity": "1",
    "side": "BUY",
    "type": "MARKET",
    "api_key": "fb7c1234-25ae-48b6-9f7f-9b3f98d76543"
  },
  "6849262870684931382ryanoakes-real": {
    "symbol": "US.IWM241029P222000",
    "quantity": "1",
    "side": "SELL",
    "type": "MARKET",
    "api_key": "fb7c1234-25ae-48b6-9f7f-9b3f98d76543"
  },
  "8522430431047724653ryanoakes-real": {
    "symbol": "US.IWM241029P215000",
    "quantity": "1",
    "side": "BUY",
    "type": "MARKET",
    "api_key": "fb7c1234-25ae-48b6-9f7f-9b3f98d76543"
  },
  "2824481022781261768ryanoakes-real": {
    "symbol": "US.IWM241029P222000",
    "quantity": "1",
    "side": "SELL",
    "type": "MARKET",
    "api_key": "fb7c1234-25ae-48b6-9f7f-9b3f98d76543"
  },
  "8264551825378587245ryanoakes-real": {
    "symbol": "US.IWM241029P215000",
    "quantity": "1",
    "side": "BUY",
    "type": "MARKET",
    "api_key": "fb7c1234-25ae-48b6-9f7f-9b3f98d76543"
  },
  "4509098938086065438ryanoakes-real": {
    "symbol": "US.IWM241029P222000",
    "quantity": "1",
    "side": "SELL",
    "type": "MARKET",
    "api_key": "fb7c1234-25ae-48b6-9f7f-9b3f98d76543"
  },
  "7106974836784701370ryanoakes-real": {
    "symbol": "US.IWM241029P215000",
    "quantity": "1",
    "side": "BUY",
    "type": "MARKET",
    "api_key": "fb7c1234-25ae-48b6-9f7f-9b3f98d76543"
  },
  "1292408256478461561ryanoakes-real": {
    "symbol": "US.IWM241029P222000",
    "quantity": "1",
    "side": "SELL",
    "type": "MARKET",
    "api_key": "fb7c1234-25ae-48b6-9f7f-9b3f98d76543"
  },
  "8129553981747476752ryanoakes-real": {
    "symbol": "US.IWM241029P215000",
    "quantity": "1",
    "side": "BUY",
    "type": "MARKET",
    "api_key": "fb7c1234-25ae-48b6-9f7f-9b3f98d76543"
  },
  "1764932975256016220ryanoakes-real": {
    "symbol": "US.IWM241029P222000",
    "quantity": "1",
    "side": "SELL",
    "type": "MARKET",
    "api_key": "fb7c1234-25ae-48b6-9f7f-9b3f98d76543"
  },
  "4662425154452023220ryanoakes-real": {
    "symbol": "US.IWM241029P215000",
    "quantity": "1",
    "side": "BUY",
    "type": "MARKET",
    "api_key": "fb7c1234-25ae-48b6-9f7f-9b3f98d76543"
  },
  "4276723289773256392ryanoakes-real": {
    "symbol": "US.IWM241029P222000",
    "quantity": "1",
    "side": "SELL",
    "type": "MARKET",
    "api_key": "fb7c1234-25ae-48b6-9f7f-9b3f98d76543"
  },
  "4296921570514524398ryanoakes-real": {
    "symbol": "US.IWM241029P215000",
    "quantity": "1",
    "side": "BUY",
    "type": "MARKET",
    "api_key": "fb7c1234-25ae-48b6-9f7f-9b3f98d76543"
  },
  "342280622698304915ryanoakes-real": {
    "symbol": "US.IWM241029P222000",
    "quantity": "1",
    "side": "SELL",
    "type": "MARKET",
    "api_key": "fb7c1234-25ae-48b6-9f7f-9b3f98d76543"
  },
  "8114596517388829325ryanoakes-real": {
    "symbol": "US.IWM241029P215000",
    "quantity": "1",
    "side": "BUY",
    "type": "MARKET",
    "api_key": "fb7c1234-25ae-48b6-9f7f-9b3f98d76543"
  },
  "6980324856012796345ryanoakes-real": {
    "symbol": "US.IWM241029P222000",
    "quantity": "1",
    "side": "SELL",
    "type": "MARKET",
    "api_key": "fb7c1234-25ae-48b6-9f7f-9b3f98d76543"
  }
}

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

result = merge_orders(input_data, 5)
print(result)

