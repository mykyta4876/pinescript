import pandas as pd
import requests
import sys
from datetime import datetime
import time
import pytz
from tqdm import tqdm
from logger import logger, LOGGING_CONFIG

class Engine7:
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
                logger.error(f"Error fetching data: {response.status_code} - {response.text}")
                return None
        except Exception as e:
            logger.error(f"Error: {str(e)}")
            return None

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
            df['End_Time'] = df['end']
            
            # Process each row
            for idx, row in df.iterrows():
                logger.info(f"Processing row {idx + 1} of {total_rows} ({((idx + 1)/total_rows * 100):.1f}%)")
                
                # Create unique key for caching
                cache_key = f"{symbol}_{row['strike']}_{row['expiry'].date()}"
                
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
                        option_data = option_data.rename(columns={'c': 'close', 'o': 'open'})
                        self.cached_data[cache_key] = option_data
                        logger.info(f"Cached {len(option_data)} bars of data")
                    else:
                        logger.info("No data found from polygon")
                        df.at[idx, 'Open_Price'] = 0
                        df.at[idx, 'Exit_Price'] = 0
                        continue
                else:
                    logger.info(f"Using cached data for strike: {row['strike']}, expiry: {row['expiry'].date()}, start: {row['start'].date()}, end: {row['end'].date()}")
                
                # Find the open price at start time
                start_data = option_data[option_data['timestamp'] >= row['start']]
                
                if len(start_data) == 0:
                    logger.info("No data found for this start time")
                    df.at[idx, 'Open_Price'] = 0
                    df.at[idx, 'Exit_Price'] = 0
                    continue
                
                entry_price = start_data['open'].iloc[0]
                df.at[idx, 'Open_Price'] = entry_price
                
                # Calculate target price
                target_price = entry_price * self.multiplier
                
                # Filter data between start and end time
                mask = (option_data['timestamp'] >= row['start']) & (option_data['timestamp'] <= row['end'])
                period_data = option_data[mask]
                
                if len(period_data) == 0:
                    logger.info("No data found for this period")
                    df.at[idx, 'Open_Price'] = 0
                    df.at[idx, 'Exit_Price'] = 0
                    continue

                # Check if price exceeded multiplier
                exceeded_target = period_data[period_data['close'] > target_price]
                
                if len(exceeded_target) > 0:
                    # Price exceeded target, use first occurrence
                    first_exceed = exceeded_target.iloc[0]
                    df.at[idx, 'Exit_Price'] = first_exceed['close']
                    df.at[idx, 'Exit_Time'] = first_exceed['timestamp']
                else:
                    # Price didn't exceed target, use last open price
                    last_price = period_data.iloc[-1]
                    df.at[idx, 'Exit_Price'] = last_price['open']
                    df.at[idx, 'Exit_Time'] = last_price['timestamp']
            
            # Generate output filename
            input_name = self.input_file.split('.')[0]
            output_file = f"{input_name}_{self.timeframe}{self.option_type}{self.multiplier}_e7.xlsx"
            
            # Select only needed columns
            result_df = df[['start', 'strike', 'expiry', 'Open_Price', 'Exit_Price', 'Exit_Time', 'End_Time']]
            
            # Save to Excel
            result_df.to_excel(output_file, index=False)
            logger.info(f"Results saved to {output_file}")
            
        except Exception as e:
            logger.error(f"Error processing data: {str(e)}")
            option_data.to_excel("option_data_line6.xlsx")

def main():
    if len(sys.argv) != 5:
        logger.error("Usage: python engine7.py <timeframe> <option_type> <multiplier> <input_file>")
        logger.error("Example: python engine7.py 1m C 2 'SPY_Weekly.xlsx'")
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
        
        engine = Engine7(timeframe, option_type, multiplier, input_file)
        engine.process_data()
        
    except Exception as e:
        logger.error(f"Error: {str(e)}")

if __name__ == "__main__":
    main()