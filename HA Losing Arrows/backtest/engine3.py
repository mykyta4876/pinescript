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
    
    return df_group

def main():
    if len(sys.argv) < 5:
        print("Usage: python engine2.py <max_positions> <timeframe> <vwap_type> <use_exit1> <input_excel_file>")
        print("Example: python engine2.py 10 10m vw n 'SPY C weekly.xlsx'")
        return
    
    try:
        max_positions = int(sys.argv[1])
        vwap_type = sys.argv[2]
        use_exit3 = sys.argv[3].lower() == 'y'
        stop_loss_percentage = float(sys.argv[4])
        input_file = sys.argv[5]
        
        # Validate inputs
        if vwap_type not in ['vw', 'vww']:
            raise ValueError("VWAP type must be either 'vw' or 'vww'")
        
        # Read input Excel file
        df_input = pd.read_excel(input_file)
        
        # Initialize list to store all results
        all_results = []
        
        # Initialize columns
        df_input['Long_Equity'] = 0.0
        df_input['Long_Balance'] = 0.0
        df_input['Long_Running_Balance'] = 0.0
        df_input['Short_Equity'] = 0.0
        df_input['Short_Balance'] = 0.0
        df_input['Short_Running_Balance'] = 0.0
        df_input['Long_Positions'] = 0.0
        df_input['Short_Positions'] = 0.0
        df_input['Long_Entry_Price'] = 0.0
        df_input['Short_Entry_Price'] = 0.0
        df_input['Avg_Long_Entry_Price'] = 0.0
        df_input['Avg_Short_Entry_Price'] = 0.0
        
        # Trading state variables
        long_positions = []  # List of (entry_close, entry_open) tuples
        short_positions = []  # List of (entry_close, entry_open) tuples
        first_long_entry_open = 0.0  # Track first entry open price for Exit1
        first_short_entry_open = 0.0  # Track first entry open price for Exit1
        long_pending_entry = False
        short_pending_entry = False
    
        # Select which VWAP to use for entry conditions
        vwap_column = vwap_type  # 'vw' or 'vww'
        expiry_date = df_input['expiry_date'].iloc[0]
        strike_price = df_input['strike_price'].iloc[0]

        for i in range(len(df_input) - 1):
            current_bar = df_input.iloc[i]
            
            # Update equity for open positions
            if long_positions:
                avg_entry_price = sum(pos[0] for pos in long_positions) / len(long_positions)
                df_input.at[df_input.index[i], 'Long_Equity'] = (current_bar['close'] - avg_entry_price) * len(long_positions)
            
            if short_positions:
                avg_entry_price = sum(pos[0] for pos in short_positions) / len(short_positions)
                df_input.at[df_input.index[i], 'Short_Equity'] = (avg_entry_price - current_bar['close']) * len(short_positions)
            
            # Check for Exit3 conditions
            if use_exit3:
                if long_positions:
                    avg_entry_price = sum(pos[0] for pos in long_positions) / len(long_positions)
                    if current_bar['close'] < avg_entry_price * (1 - stop_loss_percentage):
                        df_input.at[df_input.index[i], 'Long_Balance'] += df_input.at[df_input.index[i], 'Long_Equity']
                        long_positions = []
                        first_long_entry_open = 0.0
                        long_pending_entry = False
                    
                if short_positions:
                    avg_entry_price = sum(pos[0] for pos in short_positions) / len(short_positions)
                    if current_bar['close'] > avg_entry_price * (1 + stop_loss_percentage):
                        df_input.at[df_input.index[i], 'Short_Balance'] += df_input.at[df_input.index[i], 'Short_Equity']
                        short_positions = []
                        first_short_entry_open = 0.0
                        short_pending_entry = False

            # Execute pending long entry at current bar's open if signal was given in previous bar
            if long_pending_entry and len(long_positions) < max_positions:
                long_positions.append((current_bar['open'], current_bar['close']))
                avg_entry_price = sum(pos[0] for pos in long_positions) / len(long_positions)
                df_input.at[df_input.index[i], 'Long_Equity'] = (current_bar['close'] - avg_entry_price) * len(long_positions)
                if not first_long_entry_open:
                    first_long_entry_open = df_input.at[df_input.index[i-1], 'open']
                df_input.at[df_input.index[i], 'Long_Entry_Price'] = current_bar['open']
                long_pending_entry = False

            # Execute pending short entry at current bar's open if signal was given in previous bar
            if short_pending_entry and len(short_positions) < max_positions:
                short_positions.append((current_bar['open'], current_bar['close']))
                avg_entry_price = sum(pos[0] for pos in short_positions) / len(short_positions)
                df_input.at[df_input.index[i], 'Short_Equity'] = (avg_entry_price - current_bar['close']) * len(short_positions)
                if not first_short_entry_open:
                    first_short_entry_open = df_input.at[df_input.index[i-1], 'open']
                df_input.at[df_input.index[i], 'Short_Entry_Price'] = current_bar['open']
                short_pending_entry = False

            if long_positions:
                df_input.at[df_input.index[i], 'Avg_Long_Entry_Price'] = sum(pos[0] for pos in long_positions) / len(long_positions)
            if short_positions:
                df_input.at[df_input.index[i], 'Avg_Short_Entry_Price'] = sum(pos[0] for pos in short_positions) / len(short_positions)

            # Entry conditions using selected VWAP
            is_bull_bar = current_bar['close'] > current_bar['open']
            is_bear_bar = current_bar['close'] < current_bar['open']
            
            if len(long_positions) < max_positions and is_bull_bar and current_bar['close'] > current_bar[vwap_column]:
                long_pending_entry = True
            
            if len(short_positions) < max_positions and is_bear_bar and current_bar['close'] < current_bar[vwap_column]:
                short_pending_entry = True
            
            # Update position counts
            df_input.at[df_input.index[i], 'Long_Positions'] = len(long_positions)
            df_input.at[df_input.index[i], 'Short_Positions'] = len(short_positions)
            
            if strike_price != df_input['strike_price'].iloc[i] or expiry_date != df_input['expiry_date'].iloc[i]:
                strike_price = df_input['strike_price'].iloc[i]
                expiry_date = df_input['expiry_date'].iloc[i]
                first_long_entry_open = 0.0
                first_short_entry_open = 0.0
                long_pending_entry = False
                short_pending_entry = False

                # Handle Exit2 (last bar)
                if long_positions:
                    df_input.at[df_input.index[i-1], 'Long_Balance'] += df_input.at[df_input.index[i-1], 'Long_Equity']
                    df_input.at[df_input.index[i], 'Long_Equity'] = 0
                
                if short_positions:
                    df_input.at[df_input.index[i-1], 'Short_Balance'] += df_input.at[df_input.index[i-1], 'Short_Equity']
                    df_input.at[df_input.index[i], 'Short_Equity'] = 0
        
                long_positions = []
                short_positions = []

        # Calculate Running Balance (cumulative sum of balances)
        df_input['Long_Running_Balance'] = df_input['Long_Balance'].cumsum()
        df_input['Short_Running_Balance'] = df_input['Short_Balance'].cumsum()

        # Update columns list to include new trading columns
        columns = ['timestamp', 'vw', 'vww', 'volume', 'open', 'close', 'high', 'low',
                'transactions', 'strike_price', 'expiry_date',
                'Long_Equity', 'Long_Balance', 'Long_Running_Balance',
                'Short_Equity', 'Short_Balance', 'Short_Running_Balance', 'Long_Positions', 'Short_Positions', 'Long_Entry_Price', 'Short_Entry_Price']
        
        input_file_name = input_file.split('/')[-1]

        # Generate output filename
        output_file = f"{input_file_name.split('.')[0]}_result.xlsx"
        
        # Save to Excel
        df_input.to_excel(output_file, index=False)
        print(f"Data saved to {output_file}")
            
    except Exception as e:
        print(f"Error: {str(e)}")

if __name__ == "__main__":
    main()