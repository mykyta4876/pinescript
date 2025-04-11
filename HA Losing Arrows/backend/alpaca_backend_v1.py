from alpaca.trading.client import TradingClient
from alpaca.trading.requests import MarketOrderRequest, LimitOrderRequest, GetOrdersRequest
from alpaca.trading.enums import OrderSide, TimeInForce
from alpaca.data.requests import StockLatestQuoteRequest
from alpaca.data.historical import StockHistoricalDataClient
from alpaca.trading.enums import QueryOrderStatus
import requests

trading_client = TradingClient('PKU32CO7FB5929T1AMPC', 'W2G1EOVgmr04xqO8FeCrmdllp95DOlOzT9izgePk', paper=True)

# Add data client initialization at the top level with trading_client
data_client = StockHistoricalDataClient('AK73AUHJRTF18R9N3PPO', 'EE2gE77T67cheArxpG9JghnBJ6KPN4oTxKxL3Bww')

def submit_market_order(symbol, qty, side):
    # preparing market order
    result = {}
    try:
        market_order_data = MarketOrderRequest(
                            symbol=symbol,
                            qty=qty,
                            side=side,
                            time_in_force=TimeInForce.DAY
                        )

        # Market order
        market_order = trading_client.submit_order(
                        order_data=market_order_data
                    )
        
        result['order_id'] = market_order.id
        result['status'] = "ok"
        return result
    except Exception as e:
        print(f"Error submitting market order: {e}")
        result['status'] = f"{e}"
        return result

def submit_limit_order(symbol, qty, side, limit_price, notional):
    # preparing limit order
    limit_order_data = LimitOrderRequest(
                        symbol=symbol,
                        limit_price=limit_price,
                        notional=notional,
                        side=side,
                        time_in_force=TimeInForce.FOK
                    )

    # Limit order
    limit_order = trading_client.submit_order(
                    order_data=limit_order_data
                )
    return limit_order

def get_orders():
    get_orders_data = GetOrdersRequest(
        status=QueryOrderStatus.CLOSED,
        limit=1000,
        nested=True  # show nested multi-leg orders
    )
    
    return trading_client.get_orders(filter=get_orders_data)

def get_latest_quotes(symbols):
    """
    Get the latest bid and ask prices for given symbols (stocks or options)
    Args:
        symbols (str or list): Single symbol or list of symbols
                             For options, use format like 'US.RUTW250226P2165000'
    Returns:
        dict: Latest quote data including bid and ask prices
    """
    # Convert single symbol to list if necessary
    if isinstance(symbols, str):
        symbols = [symbols]
    
    request_params = StockLatestQuoteRequest(
        symbol_or_symbols=symbols,
        feed=None
    )
    
    try:
        return data_client.get_stock_latest_quote(request_params)  # Changed to use data_client
    except Exception as e:
        print(f"Error getting quotes: {e}")
        return None

def convert_moomoo_symbol_to_alpaca(symbol):
    # Convert Moomoo symbol to Alpaca symbol
    # Example: RUTW250226P2165000 -> RUTW250226P02165000
    # Example: RUTW250226C2165000 -> RUTW250226C02165000

    # Get the last 7 characters of the symbol
    second_part = symbol[-7:]
    # Get the odd string before the strike price
    first_part = symbol[:-7]

    # Construct the Alpaca symbol
    alpaca_symbol = f"{first_part}0{second_part}"

    return alpaca_symbol

def convert_alpaca_symbol_to_moomoo(symbol):
    # Convert Alpaca symbol to Moomoo symbol
    # Example: RUTW250226P02165000 -> RUTW250226P2165000
    # Example: RUTW250226C02165000 -> RUTW250226C2165000
    
    # Get the last 7 characters of the symbol
    second_part = symbol[-7:]
    # Get the odd string before the strike price
    first_part = symbol[:-8]

    # Construct the Moomoo symbol
    moomoo_symbol = f"{first_part}{second_part}"

    return moomoo_symbol

def get_latest_quotes_by_api(symbol_or_symbols):
    url = f"https://data.alpaca.markets/v1beta1/options/quotes/latest?symbols={symbol_or_symbols}"
    headers = {"APCA-API-KEY-ID": "AK73AUHJRTF18R9N3PPO", "APCA-API-SECRET-KEY": "EE2gE77T67cheArxpG9JghnBJ6KPN4oTxKxL3Bww", "Content-Type": "application/json"}
    response = requests.get(url, headers=headers)
    return response.json()

if __name__ == "__main__":
    #print(convert_moomoo_symbol_to_alpaca('RUTW250303P2110000'))
    #print(convert_alpaca_symbol_to_moomoo('RUTW250303P02110000'))

    #print(submit_market_order('QQQ250302C00507000', 1, OrderSide.BUY))
    print(get_orders())