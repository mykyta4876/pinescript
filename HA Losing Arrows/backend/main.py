import json
import sys
import os
from typing import Optional, Dict

from fastapi import FastAPI, HTTPException, Header, Depends
import uvicorn
from moomoo import (
    OpenSecTradeContext,
    OpenQuoteContext,
    TrdMarket,
    SecurityFirm,
    TrdSide,
    OrderType,
    TrdEnv,
    RET_OK,
    ModifyOrderOp,
    TrailType,
    SysConfig
)

from logger import logger, LOGGING_CONFIG


HOST = '127.0.0.1'
PORT = 11111

ACC_DETAILS = {
    # ryanoakes
    "fb7c1234-25ae-48b6-9f7f-9b3f98d76543": {
        "acc_id": 283445328178805387,
        "trd_env": TrdEnv.REAL,
    },
    "a9f8f651-4d3e-46f1-8d6b-c2f1f3b76429": {
        "acc_option_id": 1022345,
        "acc_stock_id": 1022340,
        "trd_env": TrdEnv.SIMULATE,
    },
    # enlixir
    "7d4f8a12-1b3c-45e9-9b1a-2a6e0fc2e975": {
        "acc_id": 283445330963143138,
        "trd_env": TrdEnv.REAL,
    },
    "d45a6e79-927b-4f3e-889d-3c65a8f0738c": {
        "acc_option_id": 978757,
        "acc_stock_id": 978753,
        "trd_env": TrdEnv.SIMULATE,
    }
}

VALID_API_KEYS = ACC_DETAILS.keys()
#TRADING_PASSWORD = os.environ.get("TRADING_PASS")
#TRADING_PASSWORD = "120120" #ryanoakes, backend-opend-test-20241008-081306
TRADING_PASSWORD = "772877" #enlixir, backend-opend-20241008-075506

MODIFY_ORDER_OPERATIONS = {
    "NONE": ModifyOrderOp.NONE,
    "NORMAL": ModifyOrderOp.NORMAL,
    "CANCEL": ModifyOrderOp.CANCEL,
    "DISABLE": ModifyOrderOp.DISABLE,
    "ENABLE": ModifyOrderOp.ENABLE,
    "DELETE": ModifyOrderOp.DELETE
}

TRAIL_TYPE = {
    "NONE": TrailType.NONE,
    "RATIO": TrailType.RATIO,
    "AMOUNT": TrailType.AMOUNT
}

ORDER_TYPE = {
    "NONE": OrderType.NONE,
    "NORMAL": OrderType.NORMAL,
    "MARKET": OrderType.MARKET,
    "ABSOLUTE_LIMIT": OrderType.ABSOLUTE_LIMIT,
    "AUCTION": OrderType.AUCTION,
    "AUCTION_LIMIT": OrderType.AUCTION_LIMIT,
    "SPECIAL_LIMIT": OrderType.SPECIAL_LIMIT,
    "SPECIAL_LIMIT_ALL": OrderType.SPECIAL_LIMIT_ALL,
    "STOP": OrderType.STOP,
    "STOP_LIMIT": OrderType.STOP_LIMIT,
    "MARKET_IF_TOUCHED": OrderType.MARKET_IF_TOUCHED,
    "LIMIT_IF_TOUCHED": OrderType.LIMIT_IF_TOUCHED,
    "TRAILING_STOP": OrderType.TRAILING_STOP,
    "TRAILING_STOP_LIMIT": OrderType.TRAILING_STOP_LIMIT,
    "TWAP_LIMIT": OrderType.TWAP_LIMIT,
    "TWAP": OrderType.TWAP,
    "VWAP_LIMIT": OrderType.VWAP_LIMIT,
    "VWAP": OrderType.VWAP
}


SysConfig.enable_proto_encrypt(True)
rsa_path = "/home/purehtc/moomoo_OpenD_8.1.4108_Ubuntu16.04/moomoo_OpenD_8.1.4108_Ubuntu16.04/private_rsa_key.pem"
SysConfig.set_init_rsa_file(rsa_path)   # rsa private key file path


class HiddenPrints:
    def __enter__(self):
        self._original_stdout = sys.stdout
        sys.stdout = open(os.devnull, 'w')

    def __exit__(self, exc_type, exc_val, exc_tb):
        sys.stdout.close()
        sys.stdout = self._original_stdout


def create_contexts():
    """Create both trade and quote contexts"""
    with HiddenPrints():
        trd_ctx = OpenSecTradeContext(
            filter_trdmarket=TrdMarket.US,
            host=HOST,
            port=PORT,
            security_firm=SecurityFirm.FUTUINC
        )
        quote_ctx = OpenQuoteContext(
            host=HOST,
            port=PORT
        )
    return trd_ctx, quote_ctx


def api_key_validation(api_key: str = Header(...)):
    """Function for api key validation"""
    if api_key not in VALID_API_KEYS:
        raise HTTPException(status_code=403, detail="Invalid API key")
    return api_key

# Unlock trade
def unlock_trade(trd_ctx):
    ret, data = trd_ctx.unlock_trade(password=TRADING_PASSWORD)
    if ret != RET_OK:
        logger.critical(f"Unlock trade failed: {data}")
        raise ConnectionError(f"Unlock trade failed: {data}")
    logger.critical('Unlock Trade success!')


def add_acc_details(params: dict, api_key: str, isFutures: bool):
    acc_details = ACC_DETAILS[api_key]
    if acc_details["trd_env"] == TrdEnv.SIMULATE:
        if isFutures:
            params["acc_id"] = acc_details["acc_stock_id"]
        else:
            params["acc_id"] = acc_details["acc_option_id"]
    else:
        params["acc_id"] = acc_details["acc_id"]
        
    params["trd_env"] = acc_details["trd_env"]


app = FastAPI()
trade_context, quote_context = create_contexts()
logger.info("Trade and Quote contexts have been initiated")
unlock_trade(trade_context)


@app.post("/")
def place_order(order_info: dict, api_key: str = Depends(api_key_validation)):
    """Function intended for sending orders through the use of moomoo API"""
    logger.info('received order creation request...')
    logger.info(order_info)
    qty = float(order_info["quantity"])
    if qty < 1:
        logger.info(f"Requested qty: {qty}. Changed to qty: 1")
        qty = 1

    params = dict()
    params["price"] = 1
    params["qty"] = qty
    params["code"] = order_info["symbol"]
    params["trd_side"] = TrdSide.BUY if order_info["side"] == 'BUY' else TrdSide.SELL
    params["order_type"] = ORDER_TYPE[order_info["type"]]
    isFutures = order_info.get("account_type", "") == "futures"

    add_acc_details(params, api_key, isFutures)

    ret, data = trade_context.place_order(**params)
    if ret != RET_OK:
        logger.critical(f"Open position failed: {data}")
        return {'Open position failed: ', data}
    else:
        logger.info("Order has been sent successfully")
        data_json = data.to_json(orient='records', lines=False)
        return data_json

@app.post("/get_ask_price")
def get_ask_price(params: Optional[Dict] = None, api_key: str = Depends(api_key_validation)):
    logger.info('received get_ask_price request...')
    ret, data = quote_context.get_market_snapshot([params["symbol"]])
    if ret != RET_OK:
        logger.critical(f"get_ask_price error: {data}")
        return {'get_ask_price error: ', data}
    data_json = {'ask_price': data['code'][0]['ask_price']}
    return data_json

@app.post("/get_bid_price")
def get_bid_price(params: Optional[Dict] = None, api_key: str = Depends(api_key_validation)):
    logger.info('received get_bid_price request...')
    ret, data = quote_context.get_market_snapshot([params["symbol"]])
    if ret != RET_OK:
        logger.critical(f"get_bid_price error: {data}")
        return {'get_bid_price error: ', data}
    data_json = {'bid_price': data['code'][0]['bid_price']}
    return data_json

@app.post("/get_snapshot")
def get_snapshot(params: Optional[Dict] = None, api_key: str = Depends(api_key_validation)):
    try:
        symbol_list = params["symbol_list"]
        logger.info(f'received get_snapshot request for {symbol_list}')
        ret, data = quote_context.get_market_snapshot(symbol_list)
        logger.info(f"get_snapshot data: {data}, ret: {ret}")
        if ret != RET_OK:
            logger.error(f"get_snapshot error: {data}")
            return {'error', data}
        json_data = data.to_json(orient='records')
        json_data = json.loads(json_data)
        logger.info(f"json_data: {json_data}")
        data_json = {'snapshot': json_data}
        return data_json
    except Exception as e:
        logger.error(f"get_snapshot error: {e}")
        return {'error', e}

@app.get("/positions/")
def get_positions(params: Optional[Dict] = None, api_key: str = Depends(api_key_validation)):
    """Function returns all positions"""
    logger.info('received positions request...')
    params = dict() if params is None else params
    params["refresh_cache"] = True
    add_acc_details(params, api_key)
    ret, data = trade_context.position_list_query(**params)
    if ret != RET_OK:
        logger.critical(f"position_list_query error: {data}")
        return {'position_list_query error: ', data}
    data_json = data.to_json(orient='records', lines=False)
    return data_json

@app.get("/accs/")
def get_accounts(params: Optional[Dict] = None, api_key: str = Depends(api_key_validation)):
    """Function returns all positions"""
    logger.info('received accounts request...')
    ret, data = trade_context.get_acc_list()
    if ret == RET_OK:
        logger.info(f"accounts: \n{data}")
    else:
        logger.critical(f"get_acc_list error: {data}")
        return {'account_list_query error: ', data}
    data_json = data.to_json(orient='records', lines=False)
    return data_json

@app.post("/order_list/")
def order_list_query(params: Optional[Dict] = None, api_key: str = Depends(api_key_validation)):
    params = dict() if params is None else params
    isFutures = params.get("account_type", "") == "futures"
    add_acc_details(params, api_key, isFutures)
    ret, data = trade_context.order_list_query(**params)
    if ret != RET_OK:
        logger.critical(f"order_list_query error: {data}")
        return {'order_list_query error: ', data}
    data_json = data.to_json(orient='records', lines=False)
    return data_json


@app.post("/modify_order/")
def modify_order(params: dict, api_key: str = Depends(api_key_validation)):
    modify_order_op = params.get("modify_order_op", "NONE")
    if not (modify_order_op in MODIFY_ORDER_OPERATIONS.keys()):
        logger.critical('invalid modify_order_op')
        return {"message": "invalid modify_order_op"}
    params["modify_order_op"] = MODIFY_ORDER_OPERATIONS[modify_order_op]

    trail_type = params.get("trail_type", None)
    if trail_type is not None:
        if not (trail_type in TRAIL_TYPE.keys()):
            logger.critical('invalid trail_type')
            return {"message": "invalid trail_type"}
        params["trail_type"] = TRAIL_TYPE[trail_type]

    add_acc_details(params, api_key)
    ret, data = trade_context.modify_order(**params)
    if ret != RET_OK:
        logger.critical(f"modify_order error: {data}")
        return {'modify_order error: ', data}
    data_json = data.to_json(orient='records', lines=False)
    return data_json


@app.get("/exit/")
def close_contexts(api_key: str = Depends(api_key_validation)):
    """Function closes both trade and quote contexts"""
    logger.info("Closing trade and quote contexts")
    trade_context.close()
    quote_context.close()
    return {"message": "success"}


@app.get("/max_quantity/")
def acctradinginfo_query(params: dict, api_key: str = Depends(api_key_validation)):
    order_type = params.get("order_type")
    if not (order_type in ORDER_TYPE.keys()):
        logger.critical('invalid order_type')
        return {"message": "invalid order_type"}
    params["order_type"] = ORDER_TYPE[order_type]
    add_acc_details(params, api_key)
    ret, data = trade_context.acctradinginfo_query(**params)
    if ret != RET_OK:
        logger.critical(f"acctradinginfo_query error: {data}")
        return {'acctradinginfo_query error': data}
    data_json = data.to_json(orient='records', lines=False)
    return data_json


if __name__ == "__main__":
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=80,
        log_config=LOGGING_CONFIG
    )

