import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

# Input parameters
Lots = 1.0
TickSize = 1.0
TickValue = 1.0
ShowHAArrow2 = True

Multiplier = 0.5
XBarsDelay = 1

Multiplier2 = 0.5
XBarsDelay2 = 1

StartDay = 0  # YYYYMMDD
StartTime = 0  # HHmm
EndDay = 0  # YYYYMMDD
EndTime = 0  # HHmm

def is_trading_time(df, start_day, start_time, end_day, end_time):
    df['yyyymmdd'] = df['time'].dt.year * 10000 + df['time'].dt.month * 100 + df['time'].dt.day
    df['hhmm'] = df['time'].dt.hour * 100 + df['time'].dt.minute
    
    v1 = (start_day > 0) & ((df['yyyymmdd'] >= start_day) & (df['hhmm'] >= start_time)) | (start_day == 0)
    v2 = (end_day > 0) & ((df['yyyymmdd'] <= end_day) & ((end_time == 0) | (df['hhmm'] <= end_time))) | (start_day == 0)

    trading_time = v1 & v2
    return trading_time

def entry_signal(df, xbars_delay):
    df['up_arrow'] = df['close'] > df['open'].shift(xbars_delay)
    df['down_arrow'] = df['close'] < df['open'].shift(xbars_delay)
    return df

def calculate_buy_profit(df, tick_size, tick_value):
    df['sum'] = 0.0
    df['totalbuypositions'] = 0.0
    
    for i in range(1, len(df)):
        if df['calc'].iloc[i]:
            df.at[i, 'sum'] = (df['close'].iloc[i] - df['netted_long_avg'].iloc[i]) / tick_size * df['netted_long_position'].iloc[i] * tick_value
            df.at[i, 'totalbuypositions'] = df['netted_long_position'].iloc[i]
        else:
            df.at[i, 'sum'] = df['sum'].iloc[i-1]
            df.at[i, 'totalbuypositions'] = df['totalbuypositions'].iloc[i-1]
    
    return df[['sum', 'totalbuypositions']]

def calculate_sell_profit(df, tick_size, tick_value):
    df['sum'] = 0.0
    df['totalsellpositions'] = 0.0
    
    for i in range(1, len(df)):
        if df['calc'].iloc[i]:
            df.at[i, 'sum'] = (df['netted_short_avg'].iloc[i] - df['close'].iloc[i]) / tick_size * df['netted_short_position'].iloc[i] * tick_value
            df.at[i, 'totalsellpositions'] = df['netted_short_position'].iloc[i]
        else:
            df.at[i, 'sum'] = df['sum'].iloc[i-1]
            df.at[i, 'totalsellpositions'] = df['totalsellpositions'].iloc[i-1]
    
    return df[['sum', 'totalsellpositions']]

def running_4775_dots_v2_reset(df, trading_time, xbars_delay, multiplier):
    df = entry_signal(df, xbars_delay)
    
    df['buy'] = df['up_arrow'] & trading_time
    df['sell'] = df['down_arrow'] & trading_time
    
    df['netted_long_position'] = 0.0
    df['netted_short_position'] = 0.0
    
    df['netted_long_avg'] = 0.0
    df['netted_short_avg'] = 0.0
    
    df['buy_profit_cutoff'] = False
    df['sell_profit_cutoff'] = False
    
    for i in range(1, len(df)):
        if df['buy'].iloc[i]:
            df.at[i, 'netted_long_position'] = df['netted_long_position'].iloc[i-1] + Lots
            df.at[i, 'netted_long_avg'] = (df['netted_long_position'].iloc[i-1] * df['netted_long_avg'].iloc[i-1] + Lots * df['close'].iloc[i]) / (df['netted_long_position'].iloc[i-1] + Lots)
        
        if df['sell'].iloc[i]:
            df.at[i, 'netted_short_position'] = df['netted_short_position'].iloc[i-1] + Lots
            df.at[i, 'netted_short_avg'] = (df['netted_short_position'].iloc[i-1] * df['netted_short_avg'].iloc[i-1] + Lots * df['close'].iloc[i]) / (df['netted_short_position'].iloc[i-1] + Lots)
    
    df['calc'] = trading_time
    buy_profit = calculate_buy_profit(df, TickSize, TickValue)
    sell_profit = calculate_sell_profit(df, TickSize, TickValue)
    
    df['buy_profit'] = buy_profit['sum']
    df['totalbuypositions'] = buy_profit['totalbuypositions']
    df['sell_profit'] = sell_profit['sum']
    df['totalsellpositions'] = sell_profit['totalsellpositions']
    
    df['buy_profit_cutoff'] = df['buy_profit_cut'] > 0 & (df['buy_profit'] >= df['buy_profit_cut'])
    df['sell_profit_cutoff'] = df['sell_profit_cut'] > 0 & (df['sell_profit'] >= df['sell_profit_cut'])
    
    return df

# Load historical data
df = pd.read_csv('BATS_QQQ, 5.csv')
df['time'] = pd.to_datetime(df['time'])

# Apply the strategy
trading_time = is_trading_time(df, StartDay, StartTime, EndDay, EndTime)
df = running_4775_dots_v2_reset(df, trading_time, XBarsDelay, Multiplier)
df = running_4775_dots_v2_reset(df, trading_time, XBarsDelay2, Multiplier2)

# Export the up_arrow and down_arrow signals to CSV
output_df = df[['time', 'up_arrow', 'down_arrow']]
output_df.to_csv('arrow_signals.csv', index=False)

# Plot the results
plt.figure(figsize=(10, 6))
plt.plot(df['time'], df['close'], label='Close Price')
plt.scatter(df['time'][df['up_arrow']], df['close'][df['up_arrow']], marker='^', color='blue', label='Buy Signal')
plt.scatter(df['time'][df['down_arrow']], df['close'][df['down_arrow']], marker='v', color='yellow', label='Sell Signal')
plt.legend()
plt.show()
