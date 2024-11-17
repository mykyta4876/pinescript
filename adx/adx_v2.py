import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from binance import Client

def calculate_adx_di(df, length=14):
    # Calculate True Range (TR)
    df['TR'] = np.maximum(df['high'] - df['low'],
                          np.maximum(np.abs(df['high'] - df['close'].shift(1)),
                                     np.abs(df['low'] - df['close'].shift(1))))
    
    # Calculate Directional Movement (DM+ and DM-)
    df['DM+'] = np.where((df['high'] - df['high'].shift(1)) > (df['low'].shift(1) - df['low']),
                         np.maximum(df['high'] - df['high'].shift(1), 0), 0)
    df['DM-'] = np.where((df['low'].shift(1) - df['low']) > (df['high'] - df['high'].shift(1)),
                         np.maximum(df['low'].shift(1) - df['low'], 0), 0)
    # Smooth TR, DM+, and DM-
    df['TR_smoothed'] = 0.0
    df['DM+_smoothed'] = 0.0 
    df['DM-_smoothed'] = 0.0

    for i in range(1 + length, len(df)):
        df.at[i, 'TR_smoothed'] = df['TR_smoothed'].iloc[i - 1] - (df['TR_smoothed'].iloc[i - 1] / length) + df['TR'].iloc[i]
        df.at[i, 'DM+_smoothed'] = df['DM+_smoothed'].iloc[i - 1] - (df['DM+_smoothed'].iloc[i - 1] / length) + df['DM+'].iloc[i]
        df.at[i, 'DM-_smoothed'] = df['DM-_smoothed'].iloc[i - 1] - (df['DM-_smoothed'].iloc[i - 1] / length) + df['DM-'].iloc[i]

    df['DI+'] = 100 * (df['DM+_smoothed'] / df['TR_smoothed'])
    df['DI-'] = 100 * (df['DM-_smoothed'] / df['TR_smoothed'])

    # Calculate DX (Directional Index)
    df['DX'] = 100 * (np.abs(df['DI+'] - df['DI-']) / (df['DI+'] + df['DI-']))

    # Calculate ADX
    df['ADX'] = df['DX'].rolling(window=length).mean()

    # Generate buy and sell signals
    df['Buy Signal'] = (df['DI+'] > df['DI-']) & (df['DI+'].shift(1) <= df['DI-'].shift(1))
    df['Sell Signal'] = (df['DI-'] > df['DI+']) & (df['DI-'].shift(1) <= df['DI+'].shift(1))

    # Print DI+ and DI- values for the most recent data
    print(f"DI+: {df['DI+'].values[-1]}")
    print(f"DI-: {df['DI-'].values[-1]}")

    return df

def plot_adx_di(df,Threshold):
    plt.figure(figsize=(14, 8))

    # Plot DI+ and DI-
    plt.plot(df['timestamp'], df['DI+'], label='DI+', color='green', linewidth=1.5)
    plt.plot(df['timestamp'], df['DI-'], label='DI-', color='red', linewidth=1.5)
    plt.plot(df['timestamp'], df['ADX'], label='ADX', color='blue', linewidth=1.5)

    # Mark Buy and Sell signals
    plt.scatter(df['timestamp'][df['Buy Signal']], df['DI+'][df['Buy Signal']], marker='^', color='green', label='Buy Signal', s=100)
    plt.scatter(df['timestamp'][df['Sell Signal']], df['DI-'][df['Sell Signal']], marker='v', color='red', label='Sell Signal', s=100)

    plt.axhline(y=Threshold, color='black', linestyle='--', label='Threshold')

    # Add labels and legend
    plt.title('ADX, DI+, and DI- with Buy/Sell Signals')
    plt.xlabel('Time')
    plt.ylabel('Value')
    plt.legend(loc='best')
    plt.grid(True)
    plt.show()

# Initialize Binance client (replace with your own API key and secret)
api_key = ''
api_secret = ''
client = Client(api_key, api_secret)

def fetch_ohlc_data(symbol, interval, limit):
    """
    Fetch OHLC data from Binance and return it as a pandas DataFrame.
    
    :param symbol: Trading pair symbol, e.g., 'BTCUSDT'
    :param interval: Time interval for the candlesticks, e.g., '1d' for daily
    :param limit: Number of data points to fetch
    :return: DataFrame with OHLC data
    """
    # Fetch OHLC data from Binance API
    klines = client.get_klines(symbol=symbol, interval=interval, limit=limit)
    
    # Convert to DataFrame
    df = pd.DataFrame(klines, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume', 'close_time', 'quote_asset_volume', 'number_of_trades', 'taker_buy_base_asset_volume', 'taker_buy_quote_asset_volume', 'ignore'])
    
    # Convert timestamp to datetime
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
    
    # Set timestamp as index and convert other columns to numeric
    # df.set_index('timestamp', inplace=True)
    df['open'] = df['open'].astype(float)
    df['high'] = df['high'].astype(float)
    df['low'] = df['low'].astype(float)
    df['close'] = df['close'].astype(float)
    df['volume'] = df['volume'].astype(float)
    df = df[['timestamp', 'open', 'high', 'low', 'close', 'volume']]
    
    return df

# Example usage
symbol = 'BTCUSDT'
df = fetch_ohlc_data(symbol, interval='1h', limit=200)

# # Call the function to calculate ADX and DI
result_df = calculate_adx_di(df)

# Save to CSV
result_df.to_csv('data.csv')

# # Plot ADX and DI values
plot_adx_di(result_df,20)
