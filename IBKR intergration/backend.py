import functions_framework
import json

@functions_framework.http
def hello_http(request):
    """HTTP Cloud Function to manage IBKR orders from TradingView alerts."""
    
    content_type = request.content_type
    print(content_type)

    if content_type == 'text/plain; charset=utf-8':
        message = request.data.decode('utf-8')  # decode from bytes to string
        print(message)
        
        # Handle different alerts and execute corresponding orders
        if "Suptertrend_Strategy_Long_Entry" in message:
            save_message('BUY')
        elif "Suptertrend_Strategy_Short_Entry" in message:
            save_message('SELL')
        elif "Suptertrend_Strategy_Long_Exit" in message:
            save_message('BUY')
        elif "Suptertrend_Strategy_Short_Exit" in message:
            save_message('SELL')

    return 'Order processed'

def save_message(message):
    with open('messages.txt', 'w') as file:
        file.write(message + '\n')
