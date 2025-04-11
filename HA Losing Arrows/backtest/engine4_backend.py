import pandas as pd
import requests
import sys
from datetime import datetime
import time
from pathlib import Path

API_KEY = "_gClIMBNzOb6jgnPTg4_xvQ08RSnKELi"
BASE_URL = "https://api.polygon.io/v2/aggs/ticker"

def parse_filename(filename):
    """Extract symbol and option type from filename"""
    parts = filename.split()
    if len(parts) < 2:
        raise ValueError("Filename must contain symbol and option type (C/P)")
    
    symbol = parts[0]
    option_type = parts[1]
    
    if option_type not in ['C', 'P']:
        raise ValueError("Option type must be 'C' or 'P'")
    
    return symbol, option_type

def format_option_ticker(symbol, expiry_date, option_type, strike_price):
    """Format the option ticker symbol for Polygon API"""
    # Convert expiry date to required format (YYMMDD)
    exp_date = datetime.strptime(expiry_date, '%Y-%m-%d')
    formatted_date = exp_date.strftime('%y%m%d')
    
    # Format strike price with required padding
    formatted_strike = f"{float(strike_price):05.0f}"
    
    return f"O:{symbol}{formatted_date}{option_type}{formatted_strike}000"

def fetch_option_data(ticker, start_date, end_date, timeframe):
    """Fetch option data from Polygon API"""
    minutes = int(timeframe.replace('m', ''))
    url = f"{BASE_URL}/{ticker}/range/{minutes}/minute/{start_date}/{end_date}"
    params = {
        "adjusted": "true",
        "sort": "asc",
        "apiKey": API_KEY
    }
    
    response = requests.get(url, params=params)
    
    if response.status_code != 200:
        print(f"Error fetching data for {ticker}: {response.status_code}")
        return None
    
    data = response.json()
    return data.get('results', [])

def process_option_data(results, strike_price, expiry_date):
    """Process the API results into a pandas DataFrame"""
    if not results:
        return pd.DataFrame()
    
    df = pd.DataFrame(results)
    
    # Rename columns to more meaningful names
    df = df.rename(columns={
        'v': 'volume',
        'o': 'open',
        'c': 'close',
        'h': 'high',
        'l': 'low',
        't': 'timestamp',
        'n': 'transactions'
    })
    
    # Convert timestamp from milliseconds to datetime and convert to US Eastern time
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms').dt.tz_localize('UTC').dt.tz_convert('America/New_York').dt.strftime('%Y-%m-%d %H:%M:%S')
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    
    # Calculate typical price
    df['typical_price'] = (df['high'] + df['low'] + df['close']) / 3
    
    # Calculate price * volume
    df['price_volume'] = df['typical_price'] * df['volume']
    
    # Calculate cumulative sums
    df['cum_price_volume'] = df['price_volume'].cumsum()
    df['cum_volume'] = df['volume'].cumsum()
    
    # Calculate VWAP (vww)
    df['vww'] = df['cum_price_volume'] / df['cum_volume']
    
    # Add strike price and expiry date columns
    df['strike_price'] = strike_price
    df['expiry_date'] = expiry_date
    
    # Update columns list to include new trading columns
    columns = ['timestamp', 'vw', 'vww', 'volume', 'open', 'close', 'high', 'low',
              'transactions', 'strike_price', 'expiry_date']
    
    # Drop intermediate calculation columns
    df = df.drop(['typical_price', 'price_volume', 'cum_price_volume', 'cum_volume'], axis=1)
    
    return df[columns]

def main():
    if len(sys.argv) < 3:
        print("Usage: python engine_only_data.py <timeframe> <input_excel_file>")
        print("Example: python engine_only_data.py 10m 'SPY C weekly.xlsx'")
        return
    
    try:
        timeframe = sys.argv[1]
        input_file = sys.argv[2]
        
        # Validate inputs
        if not timeframe.endswith('m'):
            raise ValueError("Timeframe must be specified in minutes (e.g., 5m, 10m)")
        
        # Parse symbol and option type from filename
        symbol, option_type = parse_filename(input_file)
        
        # Read input Excel file
        df_input = pd.read_excel(input_file)
        
        # Initialize list to store all results
        all_results = []
        
        # Process each row in the input file
        for idx, row in df_input.iterrows():
            strike_price = row['strike']
            expiry_date = row['expiry'].strftime('%Y-%m-%d')
            start_date = row['start'].strftime('%Y-%m-%d')
            end_date = row['end'].strftime('%Y-%m-%d')
            
            print(f"Processing {symbol} {option_type} {strike_price} {expiry_date} {start_date}")
            # Format option ticker
            ticker = format_option_ticker(symbol, expiry_date, option_type, strike_price)
            
            print(f"Fetching data for {ticker}")
            
            # Fetch data with timeframe
            results = fetch_option_data(ticker, start_date, end_date, timeframe)
            print(f"Fetched {len(results)} rows for {ticker}")
            
            # Process results
            if results:
                df_results = process_option_data(results, strike_price, expiry_date)
                print(f"Processed {len(df_results)} rows for {ticker}")
                all_results.append(df_results)
            
            # Add delay to avoid API rate limits
            time.sleep(0.5)
        
        if all_results:
            # Combine all results
            final_df = pd.concat(all_results, ignore_index=True)
            
            input_file_name = input_file.split('/')[-1]
            input_file_name = input_file_name.replace(' ', '_')
            # Generate output filename
            output_file = f"{input_file_name.split('.')[0]}_{timeframe}_output.xlsx"
            
            # Save to Excel
            final_df.to_excel(output_file, index=False)
            print(f"Data saved to {output_file}")
        else:
            print("No data was retrieved")
            
    except Exception as e:
        print(f"Error: {str(e)}")

if __name__ == "__main__":
    main()