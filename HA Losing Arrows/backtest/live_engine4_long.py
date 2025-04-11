import pandas as pd
import requests
import sys
import time
from datetime import datetime, timedelta
import pytz

class LiveEngine4Long:
    def __init__(self, symbol, strike_price, expiry_date, max_positions, reverse_entry, 
                 vwap_type, use_exit3, stop_loss_percentage, reverse_exit):
        self.API_KEY = "_gClIMBNzOb6jgnPTg4_xvQ08RSnKELi"
        self.BASE_URL = "https://api.polygon.io/v2/aggs/ticker"
        
        # Trading parameters
        self.symbol = symbol
        self.strike_price = strike_price
        self.expiry_date = expiry_date
        self.max_positions = max_positions
        self.reverse_entry = reverse_entry
        self.vwap_type = vwap_type
        self.use_exit3 = use_exit3
        self.stop_loss_percentage = stop_loss_percentage
        self.reverse_exit = reverse_exit       # Trading state
        self.long_positions = []  # List of entry prices
        self.pending_long_entry = False
        self.first_long_entry_open = 0.0
       
        # Data storage
        self.minute_data = []
        #self.quote_ctx = OpenQuoteContext(host='127.0.0.1', port=11111)
        #self.trade_ctx = OpenSecTradeContext(host='127.0.0.1', port=11111)
       
    def format_option_ticker(self):
        """Format the option ticker symbol for Polygon API"""
        exp_date = datetime.strptime(self.expiry_date, '%Y-%m-%d')
        formatted_date = exp_date.strftime('%y%m%d')
        formatted_strike = f"{float(self.strike_price):05.0f}"
        return f"O:{self.symbol}{formatted_date}C{formatted_strike}000"
   
    def fetch_latest_minute(self):
        """Fetch the latest minute of data from Polygon"""
        now = datetime.now(pytz.timezone('America/New_York'))
        """
        end_timestamp = int(now.timestamp() * 1000)  # Convert to milliseconds
        start_timestamp = end_timestamp - (60 * 1000)  # One minute ago in milliseconds
        
        url = f"{self.BASE_URL}/{self.format_option_ticker()}/range/1/minute/{start_timestamp}/{end_timestamp}"
        """
        end_date = now.strftime('%Y-%m-%d')
        
        url = f"{self.BASE_URL}/{self.format_option_ticker()}/range/1/minute/{end_date}/{end_date}"
        print(url)
        params = {
            "adjusted": "true",
            "sort": "asc",
            "apiKey": self.API_KEY
        }
        
        try:
            response = requests.get(url, params=params)
            if response.status_code == 200:
                data = response.json()
                new_data = data.get('results', [])
                last_bar = new_data[-1]
                converted_bar = {
                    'timestamp': pd.to_datetime(last_bar['t'], unit='ms'),
                    'open': last_bar['o'],
                    'high': last_bar['h'],
                    'low': last_bar['l'],
                    'close': last_bar['c'],
                    'volume': last_bar['v'],
                    'vw': last_bar['vw']
                }
                return converted_bar
            else:
                print(f"Error response: {response.status_code} - {response.text}")
            return None
        except Exception as e:
            print(f"Error fetching data: {str(e)}")
            return None
   
    """
    def enter_long_position(self, price):
        #Execute long entry order
        try:
            # Place buy order through Moomoo API
            ret, data = self.trade_ctx.place_order(
                price=price,
                qty=1,  # Quantity of contracts
                code=self.format_option_ticker(),
                trd_side=TrdSide.BUY,
                order_type=OrderType.MARKET,
                adjust_limit=0,
                trd_env=TrdEnv.REAL
            )
            
            if ret == RET_OK:
                self.long_positions.append(price)
                print(f"Entered long position at {price}")
            else:
                print(f"Failed to enter position: {data}")
                
        except Exception as e:
            print(f"Error entering position: {str(e)}")
   
    def exit_all_positions(self):
        #Exit all long positions
        if not self.long_positions:
            return
            
        try:
            # Place sell order through Moomoo API
            ret, data = self.trade_ctx.place_order(
                price=0,  # Market order
                qty=len(self.long_positions),
                code=self.format_option_ticker(),
                trd_side=TrdSide.SELL,
                order_type=OrderType.MARKET,
                adjust_limit=0,
                trd_env=TrdEnv.REAL
            )
            
            if ret == RET_OK:
                print(f"Exited all positions")
                self.long_positions = []
            else:
                print(f"Failed to exit positions: {data}")
                
        except Exception as e:
            print(f"Error exiting positions: {str(e)}")
    """
    
    def run(self, vwap_column, expiry_date, strike_price, stop_loss_percentage, reverse_exit, max_positions, reverse_entry, use_exit3):
        """Main loop to run the live trading engine"""
        print(f"Starting live trading for {self.format_option_ticker()}")
                
        # Trading state variables
        long_positions = []  # List of (entry_close, entry_open) tuples
        first_long_entry_open = 0.0  # Track first entry open price for Exit1
        long_pending_entry = False

        # Fetch and process latest minute data
        now = datetime.now(pytz.timezone('America/New_York'))
        next_bar_time = now + timedelta(minutes=1)
        previous_bar = self.fetch_latest_minute()

        time.sleep(60)

        try:
            while True:
                while True:
                    now = datetime.now(pytz.timezone('America/New_York'))
                    if now >= next_bar_time:
                        break
                    time.sleep(1)
                next_bar_time = now + timedelta(minutes=1)
                
                """
                # Check if it's trading hours (9:30 AM - 4:00 PM ET)
                if now.hour < 9 or (now.hour == 9 and now.minute < 30) or now.hour >= 16:
                    print("Outside trading hours. Waiting...")
                    time.sleep(60)
                    continue
                """

                # Fetch and process latest minute data
                current_bar = self.fetch_latest_minute()
                
                # Update equity for open positions
                if long_positions:
                    avg_entry_price = sum(pos[0] for pos in long_positions) / len(long_positions)
                    current_bar['Long_Equity'] = (current_bar['close'] - avg_entry_price) * len(long_positions)
                
                # Check for Exit3 conditions
                if use_exit3:
                    if long_positions:
                        if not reverse_exit:
                            avg_entry_price = sum(pos[0] for pos in long_positions) / len(long_positions)
                            if current_bar['close'] < avg_entry_price * (1 - stop_loss_percentage):
                                break
                        else:
                            avg_entry_price = sum(pos[0] for pos in long_positions) / len(long_positions)
                            if current_bar['close'] > avg_entry_price * (1 + stop_loss_percentage):
                                break
                        
                # Execute pending long entry at current bar's open if signal was given in previous bar
                if long_pending_entry and len(long_positions) < max_positions:
                    long_positions.append((current_bar['open'], current_bar['close']))
                    avg_entry_price = sum(pos[0] for pos in long_positions) / len(long_positions)
                    current_bar['Long_Equity'] = (current_bar['close'] - avg_entry_price) * len(long_positions)
                    if not first_long_entry_open:
                        first_long_entry_open = previous_bar['open']
                    current_bar['Long_Entry_Price'] = current_bar['open']
                    long_pending_entry = False

                # Entry conditions using selected VWAP
                if not reverse_entry:
                    is_bull_bar = current_bar['close'] > current_bar['open'] and current_bar['close'] > current_bar[vwap_column]
                else:
                    is_bull_bar = current_bar['close'] < current_bar['open'] and current_bar['close'] < current_bar[vwap_column]
                
                if len(long_positions) < max_positions and is_bull_bar:
                    long_pending_entry = True

                if now.hour == 16 and now.minute >= 0:
                    # Handle Exit2 (last bar)
                    if long_positions:
                        break
                
                previous_bar = current_bar
                
        except KeyboardInterrupt:
            print("Stopping live trading engine...")
def main():
   if len(sys.argv) < 9:
       print("Usage: python live_engine4_long.py <symbol> <strike_price> <expiry_date> <max_positions> <reverse_entry> <vwap_type> <use_exit3> <stop_loss_percentage> <reverse_exit>")
       print('Example: python live_engine4_long.py SPY 470 2024-03-15 10 r vw y 0.2 r')
       return
   
   try:
       symbol = sys.argv[1]
       strike_price = float(sys.argv[2])
       expiry_date = sys.argv[3]
       max_positions = int(sys.argv[4])
       reverse_entry = sys.argv[5].lower() == 'r'
       vwap_type = sys.argv[6]
       use_exit3 = sys.argv[7].lower() == 'y'
       stop_loss_percentage = float(sys.argv[8])
       reverse_exit = sys.argv[9].lower() == 'r'
       
       engine = LiveEngine4Long(
           symbol, strike_price, expiry_date, max_positions, 
           reverse_entry, vwap_type, use_exit3, stop_loss_percentage, reverse_exit
       )
       engine.run()
       
   except Exception as e:
       print(f"Error: {str(e)}")
if __name__ == "__main__":
   main()