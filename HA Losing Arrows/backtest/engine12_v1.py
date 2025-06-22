import pandas as pd
import requests
import sys
from datetime import datetime
import time
import pytz
from tqdm import tqdm
from logger import logger, LOGGING_CONFIG

class Engine12:
    def __init__(self, timeframe, option_type, input_file, phase_index_setting=0.05):
        self.API_KEY = "_gClIMBNzOb6jgnPTg4_xvQ08RSnKELi"
        self.BASE_URL = "https://api.polygon.io/v2/aggs/ticker"
        self.timeframe = timeframe
        self.option_type = option_type
        self.input_file = input_file
        self.phase_index_setting = phase_index_setting
        self.cached_data = {}  # Cache for storing option data

    def format_option_ticker(self, symbol, expiry_date, strike_price):
        """Format the option ticker symbol for Polygon API"""
        # Convert expiry date to required format (YYMMDD), ignoring time
        exp_date = pd.to_datetime(expiry_date).date()
        formatted_date = exp_date.strftime('%y%m%d')
        
        # Format strike price with required padding
        formatted_strike = f"{float(strike_price):05.0f}"
        
        return f"O:{symbol}{formatted_date}{self.option_type}{formatted_strike}000"

    def fetch_option_data(self, ticker, start_time, end_time):
        """Fetch option data from Polygon API"""
        # Convert times to Unix milliseconds
        start_ms = int(pd.to_datetime(start_time).timestamp() * 1000)
        end_ms = int(pd.to_datetime(end_time).timestamp() * 1000)
        
        start_date = start_time.strftime('%Y-%m-%d')
        end_date = end_time.strftime('%Y-%m-%d')
        
        # Extract number from timeframe (e.g., '5m' -> '5')
        minutes = int(self.timeframe.replace('m', ''))
        
        url = f"{self.BASE_URL}/{ticker}/range/{minutes}/minute/{start_date}/{end_date}"
        params = {
            "adjusted": "true",
            "sort": "asc",
            "apiKey": self.API_KEY
        }
        
        try:
            response = requests.get(url, params=params)
            if response.status_code == 200:
                data = response.json()
                return data.get('results', [])
            else:
                print(f"Error fetching data: {response.status_code} - {response.text}")
                return None
        except Exception as e:
            print(f"Error: {str(e)}")
            return None

    def calculate_phase_index(self, df, start_price):
        """Calculate Phase Index based on price movements"""
        phase_index = 0
        last_phase_price = start_price
        phase_indices = []

        for _, row in df.iterrows():
            current_price = row['close']
            price_change = abs(current_price - last_phase_price)
            threshold = last_phase_price * self.phase_index_setting

            if price_change >= threshold:
                if current_price > last_phase_price:
                    # Price went up - increment phase index
                    if phase_index < 0:
                        phase_index = 0
                    phase_index += 1
                else:
                    # Price went down - decrement phase index
                    if phase_index > 0:
                        phase_index = 0
                    phase_index -= 1
                last_phase_price = current_price

            phase_indices.append(phase_index)

        return phase_indices

    def calculate_short_trading_signals(self, df):
        """Calculate short trading signals based on phase index changes"""
        short_entry_price = []
        short_exit_price = []
        short_pnl = []
        
        current_entry_price = None
        current_entry_index = None
        
        for i, row in df.iterrows():
            current_phase = row['phase_index']
            current_close = row['close']
            
            # Initialize with None
            entry_price = None
            exit_price = None
            pnl = None
            
            # Check if this is the first time phase index = -1 (short entry signal)
            if current_phase == -1 and current_entry_price is None:
                current_entry_price = current_close
                current_entry_index = i
                entry_price = current_close
            
            # Check if phase index increased and close price > entry price (short exit signal)
            elif current_entry_price is not None:
                # Get previous phase index
                if i > 0:
                    prev_phase = df.iloc[i-1]['phase_index']
                    
                    # If phase index increased AND close price > entry price
                    if current_phase > prev_phase and current_close > current_entry_price:
                        exit_price = current_close
                        pnl = current_entry_price - current_close  # Short P&L: entry - exit
                        current_entry_price = None
                        current_entry_index = None
            
            short_entry_price.append(entry_price)
            short_exit_price.append(exit_price)
            short_pnl.append(pnl)
        
        # Handle any open position at the end
        if current_entry_price is not None:
            final_close = df.iloc[-1]['close']
            final_pnl = current_entry_price - final_close  # Short P&L: entry - final close
            short_pnl[-1] = final_pnl
        
        return short_entry_price, short_exit_price, short_pnl

    def process_data(self):
        """Process the input file and generate results"""
        try:
            # Extract symbol from filename
            symbol = self.input_file.split('.')[0].split()[0]
            
            # Read input Excel file
            df_input = pd.read_excel(self.input_file)
            total_rows = len(df_input)
            logger.info(f"Processing {total_rows} rows...")
            
            # Convert datetime columns to pandas datetime
            df_input['start'] = pd.to_datetime(df_input['start'])
            df_input['end'] = pd.to_datetime(df_input['end'])
            df_input['expiry'] = pd.to_datetime(df_input['expiry'])
            
            # Initialize list to store all results
            all_results = []

            # Process each row
            for idx, row in df_input.iterrows():
                logger.info(f"Processing row {idx + 1} of {total_rows} ({((idx + 1)/total_rows * 100):.1f}%)")
                
                # Create unique key for caching
                cache_key = f"{symbol}_{row['strike']}_{row['expiry'].date()}_{row['start'].date()}_{row['end'].date()}"
                
                # Check if we need to fetch data
                if cache_key not in self.cached_data:
                    logger.info(f"Fetching new data for strike: {row['strike']}, expiry: {row['expiry'].date()}, start: {row['start'].date()}, end: {row['end'].date()}")
                    ticker = self.format_option_ticker(symbol, row['expiry'], row['strike'])

                    retry_count = 1
                    while retry_count > 0:
                        data = self.fetch_option_data(ticker, row['start'], row['end'])
                        if data:
                            break
                        else:
                            logger.info("No data found from polygon, retrying...")
                            time.sleep(3)
                            retry_count -= 1

                    time.sleep(0.5)  # Rate limiting
                    
                    if data:
                        # Convert to DataFrame
                        option_data = pd.DataFrame(data)
                        option_data['timestamp'] = pd.to_datetime(option_data['t'], unit='ms').dt.tz_localize('UTC').dt.tz_convert('America/New_York').dt.strftime('%Y-%m-%d %H:%M:%S')
                        option_data['timestamp'] = pd.to_datetime(option_data['timestamp'])
                        option_data = option_data.rename(columns={'c': 'close', 'o': 'open', 'h': 'high', 'l': 'low', 'v': 'volume'})
                        self.cached_data[cache_key] = option_data
                        logger.info(f"Cached {len(option_data)} bars of data")
                    else:
                        logger.info("No data found from polygon")
                        continue
                else:
                    logger.info(f"Using cached data for strike: {row['strike']}, expiry: {row['expiry'].date()}, start: {row['start'].date()}, end: {row['end'].date()}")
                
                # Find the open price at start time
                start_data = option_data[option_data['timestamp'] >= row['start']]

                if len(start_data) == 0:
                    logger.info("No data found for this start time")
                    continue
                
                entry_price = start_data['open'].iloc[0]
                
                end_time = row['end']
                end_time = end_time.replace(hour=23, minute=59, second=59)

                # Filter data between start and end time
                mask = (option_data['timestamp'] >= row['start']) & (option_data['timestamp'] <= end_time)
                period_data = option_data[mask].copy()
                
                if len(period_data) == 0:
                    logger.info("No data found for this period")
                    continue

                # Calculate Phase Index
                phase_indices = self.calculate_phase_index(period_data, entry_price)
                period_data['phase_index'] = phase_indices

                # Calculate short trading signals
                short_entry_prices, short_exit_prices, short_pnls = self.calculate_short_trading_signals(period_data)
                period_data['short_entry_price'] = short_entry_prices
                period_data['short_exit_price'] = short_exit_prices
                period_data['short_pnl'] = short_pnls

                # Add additional columns
                period_data['strike_price'] = row['strike']
                period_data['expiry_date'] = row['expiry']
                period_data['start_time'] = row['start']
                period_data['end_time'] = row['end']

                # Select and reorder columns
                columns = ['timestamp', 'open', 'high', 'low', 'close', 'volume', 'phase_index', 
                          'strike_price', 'expiry_date', 'short_entry_price', 'short_exit_price', 'short_pnl']
                period_data = period_data[columns]

                all_results.append(period_data)

            if all_results:
                # Combine all results
                final_df = pd.concat(all_results, ignore_index=True)
                
                # Generate output filename
                input_name = self.input_file.split('.')[0]
                output_file = f"{input_name}_{self.timeframe}{self.option_type}{self.phase_index_setting}_e12.xlsx"
                
                # Save to Excel
                final_df.to_excel(output_file, index=False)
                logger.info(f"Results saved to {output_file}")
            else:
                logger.info("No data was retrieved")
            
        except Exception as e:
            logger.error(f"Error processing data: {str(e)}")
            if 'option_data' in locals():
                option_data.to_excel("option_data_error.xlsx")

def main():
    logger.info(f"Starting Engine 12")
    count_args = len(sys.argv)
    logger.info(f"Number of arguments: {count_args}")
    if count_args != 5:
        logger.error("Usage: python engine12.py <timeframe> <option_type> <phase_index_setting> <input_file>")
        logger.error("Example: python engine12.py 1m C 0.05 \"SPY C Weekly.xlsx\"")

        """
        Usage: python engine12.py <timeframe> <option_type> <phase_index_setting> <input_file>
        python engine12.py 1m C 0.05 "SPY C Weekly.xlsx"
        """
        return
    
    try:
        timeframe = sys.argv[1]
        option_type = sys.argv[2]
        phase_index_setting = float(sys.argv[3])
        input_file = sys.argv[4]
        
        # Validate inputs
        if not timeframe.endswith('m'):
            raise ValueError("Timeframe must be specified in minutes (e.g., 1m, 5m)")
        if option_type not in ['C', 'P']:
            raise ValueError("Option type must be 'C' or 'P'")
        
        engine = Engine12(timeframe, option_type, input_file, phase_index_setting)
        engine.process_data()
        
    except Exception as e:
        logger.error(f"Error: {str(e)}")

if __name__ == "__main__":
    main() 