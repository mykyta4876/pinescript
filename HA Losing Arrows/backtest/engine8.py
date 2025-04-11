import pandas as pd
import requests
import sys
from datetime import datetime
import time
import pytz
from tqdm import tqdm
from logger import logger, LOGGING_CONFIG

class Engine8:
    def __init__(self, timeframe, option_type, multiplier, input_file):
        self.API_KEY = "_gClIMBNzOb6jgnPTg4_xvQ08RSnKELi"
        self.BASE_URL = "https://api.polygon.io/v2/aggs/ticker"
        self.timeframe = timeframe
        self.option_type = option_type
        self.multiplier = multiplier
        self.input_file = input_file
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
        #print(url)
        params = {
            "adjusted": "true",
            "sort": "asc",
            "apiKey": self.API_KEY
        }
        
        try:
            response = requests.get(url, params=params)
            if response.status_code == 200:
                data = response.json()
                #print(data)
                return data.get('results', [])
            else:
                print(f"Error fetching data: {response.status_code} - {response.text}")
                return None
        except Exception as e:
            print(f"Error: {str(e)}")
            return None

    def calculate_oscillations(self, data, open_price, target_price):
        """Calculate number of oscillations between open price and target price"""
        oscillations = 0
        above_target = False
        at_open = True
        
        for _, row in data.iterrows():
            close_price = row['close']
            
            if at_open and close_price > target_price:
                # Price moved from open to above target
                oscillations += 1
                above_target = True
                at_open = False
            elif above_target and close_price <= open_price:
                # Price moved from above target back to open
                oscillations += 1
                above_target = False
                at_open = True
        
        return oscillations

    def process_data(self):
        """Process the input file and generate results"""
        try:
            # Extract symbol from filename
            symbol = self.input_file.split('.')[0].split()[0]
            
            # Read input Excel file
            df = pd.read_excel(self.input_file)
            total_rows = len(df)
            logger.info(f"Processing {total_rows} rows...")
            # Convert datetime columns to pandas datetime
            df['start'] = pd.to_datetime(df['start'])
            df['end'] = pd.to_datetime(df['end'])
            df['expiry'] = pd.to_datetime(df['expiry'])
            
            # Initialize results columns
            df['Open_Price'] = 0.0
            df['Exit_Price'] = 0.0
            df['Exit_Time'] = pd.NaT
            df['Oscillations'] = 0
            df['End_Time'] = df['end']

            # Process each row
            for idx, row in df.iterrows():
                logger.info(f"Processing row {idx + 1} of {total_rows} ({((idx + 1)/total_rows * 100):.1f}%)")
                try:
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
                            if not option_data.empty:
                                option_data['timestamp'] = pd.to_datetime(option_data['t'], unit='ms').dt.tz_localize('UTC').dt.tz_convert('America/New_York').dt.strftime('%Y-%m-%d %H:%M:%S')
                                option_data['timestamp'] = pd.to_datetime(option_data['timestamp'])
                                option_data = option_data.rename(columns={'c': 'close', 'o': 'open'})
                                self.cached_data[cache_key] = option_data
                                logger.info(f"Cached {len(option_data)} bars of data")
                            else:
                                logger.info("No data found from polygon api")
                                continue
                    else:
                        logger.info(f"Using cached data for strike: {row['strike']}, expiry: {row['expiry'].date()}, start: {row['start'].date()}, end: {row['end'].date()}")
                    
                    if cache_key in self.cached_data:
                        option_data = self.cached_data[cache_key]
                        
                        # Find the open price at start time
                        start_data = option_data[option_data['timestamp'] >= row['start']]
                        if not start_data.empty:
                            entry_price = start_data.iloc[0]['open']
                            df.at[idx, 'Open_Price'] = entry_price
                            
                            # Calculate target price
                            target_price = entry_price * self.multiplier
                            
                            # Filter data between start and end time
                            mask = (option_data['timestamp'] >= row['start']) & (option_data['timestamp'] <= row['end'])
                            period_data = option_data[mask]
                            
                            if not period_data.empty:
                                # Get end time open price
                                end_data = option_data[option_data['timestamp'] <= row['end']]
                                if not end_data.empty:
                                    df.at[idx, 'Exit_Price'] = end_data.iloc[-1]['open']
                                    df.at[idx, 'Exit_Time'] = end_data.iloc[-1]['timestamp']
                                
                                # Calculate oscillations
                                oscillations = self.calculate_oscillations(period_data, entry_price, target_price)
                                df.at[idx, 'Oscillations'] = oscillations
                            else:
                                logger.info("No data found for this period")
                        else:
                            logger.info("No data found for this start time")
                            
                except Exception as e:
                    logger.error(f"\nError processing row {idx + 1}: {str(e)}")
                    continue
            
            # Generate output filename
            input_name = self.input_file.split('.')[0]
            output_file = f"{input_name}_{self.timeframe}{self.option_type}{self.multiplier}_e8.xlsx"
            
            # Select only needed columns
            result_df = df[['start', 'strike', 'expiry', 'Open_Price', 'Exit_Price', 'Exit_Time', 'Oscillations', 'End_Time']]
            
            # Save to Excel
            result_df.to_excel(output_file, index=False)
            logger.info(f"\nResults saved to {output_file}")
            
        except Exception as e:
            logger.error(f"\nError processing data: {str(e)}")

def main():
    if len(sys.argv) != 5:
        logger.error("Usage: python engine8.py <timeframe> <option_type> <multiplier> <input_file>")
        logger.error("Example: python engine8.py 1m C 2 'SPY_Weekly.xlsx'")
        return
    
    try:
        timeframe = sys.argv[1]
        option_type = sys.argv[2]
        multiplier = float(sys.argv[3])
        input_file = sys.argv[4]
        
        # Validate inputs
        if not timeframe.endswith('m'):
            raise ValueError("Timeframe must be specified in minutes (e.g., 1m, 5m)")
        if option_type not in ['C', 'P']:
            raise ValueError("Option type must be 'C' or 'P'")
        
        engine = Engine8(timeframe, option_type, multiplier, input_file)
        engine.process_data()
        
    except Exception as e:
        logger.error(f"\nError: {str(e)}")

if __name__ == "__main__":
    main() 