import json

# Load orders from json file
with open("orderlist.json", "r") as f:
    orders = json.load(f)

# Find IWM call orders
iwm_call_orders = [
    order for order in orders
    if "IWM" in order['code'] and "C" in order['code']
]

# Print results
print("Found IWM call orders:")
for order in iwm_call_orders:
    print(f"Details: {order}")
    print("---")

with open("iwm_call_orders.json", "w") as f:
    json.dump(iwm_call_orders, f)
