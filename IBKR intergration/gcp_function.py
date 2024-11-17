import functions_framework
import json

import requests

@functions_framework.http
def hello_http(request):
    """HTTP Cloud Function to manage IBKR orders from TradingView alerts."""
    
    content_type = request.content_type
    print(content_type)

    if content_type == 'text/plain; charset=utf-8':
        message = request.data.decode('utf-8')  # decode from bytes to string
        print(message)
        
        # Handle different alerts and execute corresponding orders
        if "Supertrend_Strategy_Long_Entry" == message:
            request_message('Supertrend_Strategy_Long_Entry')
        elif "Supertrend_Strategy_Short_Entry" == message:
            request_message('Supertrend_Strategy_Short_Entry')
        elif "Supertrend_Strategy_Long_Exit" == message:
            request_message('Supertrend_Strategy_Long_Exit')
        elif "Supertrend_Strategy_Short_Exit" == message:
            request_message('Supertrend_Strategy_Short_Exit')

    return 'Order processed'

def request_message(message):
	headers = {"Content-Type": "application/json"}
	vm_address = "http://34.30.24.141/webhook"
	data = {"message": message, "api_key": "1234567890"}

	try:
		response = requests.post(vm_address, json=data, headers=headers)
		response.raise_for_status()
		response_json = response.json()

		print(f"message: {response_json}")

		return ""
	except requests.exceptions.RequestException as e:
		print(f"request_message: error: {e}")
		return ""
