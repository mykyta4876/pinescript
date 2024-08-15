import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

# Function to check if it's trading time
def is_trading_time(current_time, start_day, start_time, end_day, end_time):
    return True  # Implement the time check logic here

# Function to generate entry signals
def entry_signal(data, x_bars_delay):
    data['up_arrow'] = data['close'] > data['open'].shift(x_bars_delay)
    data['down_arrow'] = data['close'] < data['open'].shift(x_bars_delay)
    return data

# Function to calculate buy profit
def calculate_buy_profit(data, tick_size, tick_value):
    data['buy_profit'] = np.where(
        data['calc'],
        (data['close'] - data['netted_long_avg']) / tick_size * data['netted_long_position'] * tick_value,
        data['buy_profit'].shift(1)
    )
    data['total_buy_positions'] = np.where(
        data['calc'],
        data['netted_long_position'],
        data['total_buy_positions'].shift(1)
    )
    return data

# Function to calculate sell profit
def calculate_sell_profit(data, tick_size, tick_value):
    data['sell_profit'] = np.where(
        data['calc'],
        (data['netted_short_avg'] - data['close']) / tick_size * data['netted_short_position'] * tick_value,
        data['sell_profit'].shift(1)
    )
    data['total_sell_positions'] = np.where(
        data['calc'],
        data['netted_short_position'],
        data['total_sell_positions'].shift(1)
    )
    return data

# Main function
def trading_strategy(data, lots, tick_size, tick_value, x_bars_delay, multiplier, start_day, start_time, end_day, end_time):
    data = entry_signal(data, x_bars_delay)
    data['trading_time'] = is_trading_time(data['timestamp'], start_day, start_time, end_day, end_time)

    # Initialize columns
    data['netted_long_position'] = 0.0
    data['netted_long_avg'] = 0.0
    data['netted_short_position'] = 0.0
    data['netted_short_avg'] = 0.0
    data['buy_profit'] = 0.0
    data['total_buy_positions'] = 0.0
    data['sell_profit'] = 0.0
    data['total_sell_positions'] = 0.0

    for i in range(1, len(data)):
        data.loc[i, 'calc'] = data.loc[i, 'trading_time']

        if data.loc[i, 'calc']:
            # Long position logic
            if data.loc[i, 'up_arrow']:
                data.loc[i, 'netted_long_position'] = data.loc[i - 1, 'netted_long_position'] + lots
                data.loc[i, 'netted_long_avg'] = (data.loc[i - 1, 'netted_long_position'] * data.loc[i - 1, 'netted_long_avg'] + lots * data.loc[i, 'close']) / (data.loc[i - 1, 'netted_long_position'] + lots)
            else:
                data.loc[i, 'netted_long_position'] = data.loc[i - 1, 'netted_long_position']
                data.loc[i, 'netted_long_avg'] = data.loc[i - 1, 'netted_long_avg']

            # Short position logic
            if data.loc[i, 'down_arrow']:
                data.loc[i, 'netted_short_position'] = data.loc[i - 1, 'netted_short_position'] + lots
                data.loc[i, 'netted_short_avg'] = (data.loc[i - 1, 'netted_short_position'] * data.loc[i - 1, 'netted_short_avg'] + lots * data.loc[i, 'close']) / (data.loc[i - 1, 'netted_short_position'] + lots)
            else:
                data.loc[i, 'netted_short_position'] = data.loc[i - 1, 'netted_short_position']
                data.loc[i, 'netted_short_avg'] = data.loc[i - 1, 'netted_short_avg']

    data = calculate_buy_profit(data, tick_size, tick_value)
    data = calculate_sell_profit(data, tick_size, tick_value)

    # Plotting the results
    plt.figure(figsize=(14, 7))
    plt.plot(data['timestamp'], data['close'], label='Close Price')
    #plt.scatter(data[data['up_arrow']].index, data[data['up_arrow']]['close'], marker='^', color='blue', label='Buy Signal', alpha=1)
    #plt.scatter(data[data['down_arrow']].index, data[data['down_arrow']]['close'], marker='v', color='red', label='Sell Signal', alpha=1)
    plt.title('Trading Strategy Signals')
    plt.xlabel('Date')
    plt.ylabel('Price')
    plt.legend()
    plt.show()

    return data

#Example usage with a sample DataFrame
data = pd.read_csv('Sample Data Set.csv')
data['timestamp'] = pd.to_datetime(data['time'])
result = trading_strategy(data, lots=1.0, tick_size=1.0, tick_value=1.0, x_bars_delay=1, multiplier=0.5, start_day=0, start_time=0, end_day=0, end_time=0)
