from flask import Flask, request, jsonify
import requests
from logger import logger, LOGGING_CONFIG
import json
import time
import os
from datetime import datetime

last_message = ""

# Initialize Flask app
app = Flask(__name__)

@app.route('/', methods=['GET'])
def hello_world():
    return "Hello, World!"

@app.route('/webhook', methods=['POST', 'GET'])
def set_message():
    global last_message
    """Flask route to manage IBKR orders from TradingView alerts."""
    
    # Validate content type
    if not request.is_json:
        logger.error(f"Invalid content type: {request.content_type}")
        return jsonify({"error": "Content type must be application/json"}), 400
    
    try:
        data = request.json
    except Exception as e:
        logger.error(f"Failed to parse JSON: {str(e)}")
        return jsonify({"error": "Invalid JSON payload"}), 400

    api_key = data.get("api_key")
    if not api_key:
        logger.error(f"Missing API key: {data}")
        return jsonify({"error": "Missing API key"}), 403
    
    if api_key != "1234567890":
        logger.error(f"Invalid API key: {api_key}")
        return jsonify({"error": "Invalid API key"}), 403

    content_type = request.content_type
    logger.info(f"Content type: {content_type}")

    message = data.get("message")
    if not message:
        logger.error("Missing message in payload")
        return jsonify({"error": "Missing message"}), 400
        
    logger.info(f"Message: {message}")
    # Handle different alerts and execute corresponding orders
    if "Supertrend_Strategy_Long_Entry" == message and last_message != 'Supertrend_Strategy_Long_Entry' and last_message != 'Supertrend_Strategy_Short_Entry':
        save_message('BUY') 
        last_message = 'Supertrend_Strategy_Long_Entry'
    elif "Supertrend_Strategy_Short_Entry" == message and last_message != 'Supertrend_Strategy_Long_Entry' and last_message != 'Supertrend_Strategy_Short_Entry':
        save_message('SELL')
        last_message = 'Supertrend_Strategy_Short_Entry'
    elif "Supertrend_Strategy_Long_Exit" == message and last_message == 'Supertrend_Strategy_Long_Entry':
        save_message('SELL')
        last_message = 'Supertrend_Strategy_Long_Exit'
    elif "Supertrend_Strategy_Short_Exit" == message and last_message == 'Supertrend_Strategy_Short_Entry':
        save_message('BUY')
        last_message = 'Supertrend_Strategy_Short_Exit'

    return jsonify({"message": "Order processed"}), 200

@app.route('/get_message', methods=['POST'])
def get_message():
    # Add similar error handling
    if not request.is_json:
        logger.error(f"Invalid content type: {request.content_type}")
        return jsonify({"error": "Content type must be application/json"}), 400
        
    try:
        data = request.json
    except Exception as e:
        logger.error(f"Failed to parse JSON: {str(e)}")
        return jsonify({"error": "Invalid JSON payload"}), 400

    api_key = data.get("api_key")
    if not api_key:
        logger.error(f"Missing API key: {data}")
        return jsonify({"error": "Missing API key"}), 403
    
    if api_key != "1234567890":
        logger.error(f"Invalid API key: {api_key}")
        return jsonify({"error": "Invalid API key"}), 403

    return jsonify({"message": read_message()}), 200

def save_message(message):
    with open('messages.txt', 'a') as file:
        logger.info(message)
        file.write("," + message)

def read_message():
    message = ""
    if os.path.exists('messages.txt'):
        with open('messages.txt', 'r') as file:
            message = file.read().strip()
        os.remove('messages.txt')
    
    return message

if __name__ == "__main__":
    app.run(host="0.0.0.0")
