import json
import requests
from ibapi.client import *
from ibapi.wrapper import *
from ibapi.contract import Contract
from ibapi.order import Order
from logger import logger, LOGGING_CONFIG
import time

first_run_flag = True

class TradeApp(EWrapper, EClient): 
    def __init__(self): 
        EClient.__init__(self, self)
        self.nextValidOrderId = 0
        self.started = False

    def placeOrder(self, orderId, contract, order):
        super().placeOrder(orderId, contract, order)
        logger.info(f"Order placed. OrderId: {orderId}, contract: {contract}")

    def nextValidId(self, orderId: int):
        super().nextValidId(orderId)
        self.nextValidOrderId = orderId
        logger.info(f"Next Valid Order ID: {orderId}")
        self.start()


    def nextOrderId(self):
        oid = self.nextValidOrderId
        self.nextValidOrderId += 1
        return oid
        
    def create_contract(self):
        contract = Contract()
        contract.symbol = "NVDA"
        contract.secType = "STK"
        contract.exchange = "SMART"
        contract.currency = "USD"
        return contract

    def create_market_order(self, action):
        order = Order()
        order.action = action
        order.orderType = "MKT"
        order.totalQuantity = 1
        return order
    
    def request_message(self):
        headers = {"Content-Type": "application/json"}
        vm_address = "http://34.174.93.159/get_message"
        data = {"api_key": "1234567890"}
        try:
            response = requests.post(vm_address, json=data, headers=headers)
            response.raise_for_status()
            json_object = response.json()
            
            logger.info(f"json_object: {json_object}")

            if not "message" in json_object:
                return ""
            
            message = json_object["message"]
            #logger.info(f"message: {message}")

            return message
        except requests.exceptions.RequestException as e:
            logger.error(f"request_message: error: {e}")
            return ""

    def start(self):
        global first_run_flag
        if self.started:
            return

        self.started = True

        contract = self.create_contract()
        while True:
            message = self.request_message()
            if first_run_flag:
                first_run_flag = False
                continue
            
            order_cmds = message.split(",")
            for order_cmd in order_cmds:
                if order_cmd == "BUY":
                    order = self.create_market_order("BUY")
                    self.placeOrder(self.nextOrderId(), contract, order)
                    logger.info(f"BUY order placed")
                elif order_cmd == "SELL": 
                    order = self.create_market_order("SELL")
                    self.placeOrder(self.nextOrderId(), contract, order)
                    logger.info(f"SELL order placed")
            time.sleep(2)

app = TradeApp()      
app.connect("127.0.0.1", 7497, clientId=1)
app.run()
