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

def calculate_trading_signals(df_group, max_positions, vwap_type, use_exit1):
    """Calculate trading signals with configurable parameters"""
    
    # Initialize columns
    df_group['Long_Equity'] = 0.0
    df_group['Long_Balance'] = 0.0
    df_group['Long_Running_Balance'] = 0.0
    df_group['Short_Equity'] = 0.0
    df_group['Short_Balance'] = 0.0
    df_group['Short_Running_Balance'] = 0.0
    df_group['Long_Positions'] = 0.0
    df_group['Short_Positions'] = 0.0
    df_group['Long_Entry_Price'] = 0.0
    df_group['Short_Entry_Price'] = 0.0
    
    # Trading state variables
    long_positions = []  # List of (entry_close, entry_open) tuples
    short_positions = []  # List of (entry_close, entry_open) tuples
    first_long_entry_open = 0.0  # Track first entry open price for Exit1
    first_short_entry_open = 0.0  # Track first entry open price for Exit1
    
    # Select which VWAP to use for entry conditions
    vwap_column = vwap_type  # 'vw' or 'vww'
    
    for i in range(len(df_group)):
        current_bar = df_group.iloc[i]
        
        # Update equity for open positions
        if long_positions:
            avg_entry_price = sum(pos[0] for pos in long_positions) / len(long_positions)
            df_group.at[df_group.index[i], 'Long_Equity'] = (current_bar['close'] - avg_entry_price) * len(long_positions)
            
        if short_positions:
            avg_entry_price = sum(pos[0] for pos in short_positions) / len(short_positions)
            df_group.at[df_group.index[i], 'Short_Equity'] = (avg_entry_price - current_bar['close']) * len(short_positions)
        
        # Check for Exit1 conditions only if enabled
        if use_exit1:
            if long_positions and current_bar['close'] < first_long_entry_open:
                df_group.at[df_group.index[i], 'Long_Balance'] += df_group.at[df_group.index[i], 'Long_Equity']
                long_positions = []
                first_long_entry_open = 0.0
                
            if short_positions and current_bar['close'] > first_short_entry_open:
                df_group.at[df_group.index[i], 'Short_Balance'] += df_group.at[df_group.index[i], 'Short_Equity']
                short_positions = []
                first_short_entry_open = 0.0
        
        # Entry conditions using selected VWAP
        is_bull_bar = current_bar['close'] > current_bar['open']
        is_bear_bar = current_bar['close'] < current_bar['open']
        
        if len(long_positions) < max_positions and is_bull_bar and current_bar['close'] > current_bar[vwap_column]:
            long_positions.append((current_bar['close'], current_bar['open']))
            if not first_long_entry_open:
                first_long_entry_open = df_group.at[df_group.index[i-1], 'open']
            df_group.at[df_group.index[i], 'Long_Entry_Price'] = current_bar['open']
        
        if len(short_positions) < max_positions and is_bear_bar and current_bar['close'] < current_bar[vwap_column]:
            short_positions.append((current_bar['close'], current_bar['open']))
            if not first_short_entry_open:
                first_short_entry_open = df_group.at[df_group.index[i-1], 'open']
            df_group.at[df_group.index[i], 'Short_Entry_Price'] = current_bar['open']
        
        # Update position counts
        df_group.at[df_group.index[i], 'Long_Positions'] = len(long_positions)
        df_group.at[df_group.index[i], 'Short_Positions'] = len(short_positions)
    
    # Handle Exit2 (last bar)
    if long_positions:
        df_group.at[df_group.index[-1], 'Long_Balance'] += df_group.at[df_group.index[-1], 'Long_Equity']
        df_group.at[df_group.index[-1], 'Long_Equity'] = 0
    
    if short_positions:
        df_group.at[df_group.index[-1], 'Short_Balance'] += df_group.at[df_group.index[-1], 'Short_Equity']
        df_group.at[df_group.index[-1], 'Short_Equity'] = 0
    
    return df_group

def process_option_data(results, strike_price, expiry_date, max_positions, vwap_type, use_exit1):
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
    
    # Add trading calculations with new parameters
    df = calculate_trading_signals(df, max_positions, vwap_type, use_exit1)
    
    # Update columns list to include new trading columns
    columns = ['timestamp', 'vw', 'vww', 'volume', 'open', 'close', 'high', 'low',
              'transactions', 'strike_price', 'expiry_date',
              'Long_Equity', 'Long_Balance', 'Long_Running_Balance',
              'Short_Equity', 'Short_Balance', 'Short_Running_Balance', 'Long_Positions', 'Short_Positions', 'Long_Entry_Price', 'Short_Entry_Price']
    
    # Drop intermediate calculation columns
    df = df.drop(['typical_price', 'price_volume', 'cum_price_volume', 'cum_volume'], axis=1)
    
    return df[columns]

def main():
    if len(sys.argv) < 6:
        print("Usage: python engine2.py <max_positions> <timeframe> <vwap_type> <use_exit1> <input_excel_file>")
        print("Example: python engine2.py 10 10m vw n 'SPY C weekly.xlsx'")
        return
    
    try:
        max_positions = int(sys.argv[1])
        timeframe = sys.argv[2]
        vwap_type = sys.argv[3]
        use_exit1 = sys.argv[4].lower() == 'y'
        input_file = sys.argv[5]
        
        # Validate inputs
        if not timeframe.endswith('m'):
            raise ValueError("Timeframe must be specified in minutes (e.g., 5m, 10m)")
        if vwap_type not in ['vw', 'vww']:
            raise ValueError("VWAP type must be either 'vw' or 'vww'")
        
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
            
            print(f"Processing {symbol} {option_type} {strike_price} {expiry_date} {start_date}")
            # Format option ticker
            ticker = format_option_ticker(symbol, expiry_date, option_type, strike_price)
            
            print(f"Fetching data for {ticker}")
            
            # Fetch data with timeframe
            results = fetch_option_data(ticker, start_date, expiry_date, timeframe)
            print(f"Fetched {len(results)} rows for {ticker}")
            
            # Process results
            if results:
                df_results = process_option_data(results, strike_price, expiry_date, max_positions, vwap_type, use_exit1)
                print(f"Processed {len(df_results)} rows for {ticker}")
                all_results.append(df_results)
            
            # Add delay to avoid API rate limits
            time.sleep(0.5)
        
        if all_results:
            # Combine all results
            final_df = pd.concat(all_results, ignore_index=True)
            
            # Calculate Running Balance (cumulative sum of balances)
            final_df['Long_Running_Balance'] = final_df['Long_Balance'].cumsum()
            final_df['Short_Running_Balance'] = final_df['Short_Balance'].cumsum()
            
            input_file_name = input_file.split('/')[-1]
            input_file_name = input_file_name.replace(' ', '_')
            # Generate output filename
            output_file = f"{input_file_name.split('.')[0]}_output.xlsx"
            
            # Save to Excel
            final_df.to_excel(output_file, index=False)
            print(f"Data saved to {output_file}")
        else:
            print("No data was retrieved")
            
    except Exception as e:
        print(f"Error: {str(e)}")

if __name__ == "__main__":
    main()