import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

# Define inputs
Lots = 1.0
TickSize = 1.0
TickValue = 1.0

ShowHAArrow2 = True

Multiplier = 0.5
XBarsDelay = 1

Multiplier2 = 0.5
XBarsDelay2 = 1

StartDay = 'YYYYMMDD'
StartTime = 'HHmm'
EndDay = 'YYYYMMDD'
EndTime = 'HHmm'

# Define the trading time check function
def is_trading_time(df, start_day, start_time, end_day, end_time):
    """
    df['yyyymmdd'] = df.index.strftime('%Y%m%d').astype(int)
    df['hhmm'] = df.index.strftime('%H%M').astype(int)
    trading_time = (df['yyyymmdd'] >= int(start_day)) & (df['yyyymmdd'] <= int(end_day))
    trading_time &= (df['hhmm'] >= int(start_time)) & ((df['hhmm'] <= int(end_time)) | (int(end_time) == 0))
    """
    return True

# Define entry signal function
def entry_signal(df, x_bars_delay):
    df['upArrow'] = df['close'] > df['open'].shift(x_bars_delay)
    df['downArrow'] = df['close'] < df['open'].shift(x_bars_delay)
    return df

# Define profit calculation functions
def calculate_buy_profit(df, calc, netted_long_avg, netted_long_position):
    df['sum'] = 0.0
    df['totalbuypositions'] = 0.0
    if calc == True:
        df['sum'] = (df['close'] - netted_long_avg) / TickSize * netted_long_position * TickValue
        df['totalbuypositions'] = netted_long_position
    else:
        df['sum'] = df['sum'].shift(1).fillna(0)
        df['totalbuypositions'] = df['totalbuypositions'].shift(1).fillna(0)
    return df

def calculate_sell_profit(df, calc, netted_short_avg, netted_short_position):
    df['sum'] = 0.0
    df['totalsellpositions'] = 0.0
    if calc:
        df['sum'] = (netted_short_avg - df['close']) / TickSize * netted_short_position * TickValue
        df['totalsellpositions'] = netted_short_position
    else:
        df['sum'] = df['sum'].shift(1).fillna(0)
        df['totalsellpositions'] = df['totalsellpositions'].shift(1).fillna(0)
    return df

# Main trading strategy function
def running_4775_dots_v2_reset(df, trading_time, x_bars_delay, multiplier):
    df = entry_signal(df, x_bars_delay)
    df['buy'] = df['upArrow'] & trading_time
    df['sell'] = df['downArrow'] & trading_time

    df['nettedLongPosition'] = 0.0
    df['nettedShortPosition'] = 0.0
    df['nettedLongAvg'] = 0.0
    df['nettedShortAvg'] = 0.0

    df.loc[df['buy'], 'nettedLongPosition'] = df['nettedLongPosition'].shift(1).fillna(0) + Lots
    df.loc[df['buy'], 'nettedLongAvg'] = (df['nettedLongPosition'].shift(1).fillna(0) * df['nettedLongAvg'].shift(1).fillna(0) + Lots * df['close']) / (df['nettedLongPosition'].shift(1).fillna(0) + Lots)

    df['buyProfitCut'] = 0.0
    df.loc[df['nettedLongPosition'].shift(1) == 0, 'buyProfitCut'] = df['close'] * multiplier
    df.loc[df['nettedLongPosition'] == 0, 'buyProfitCut'] = 0

    df.loc[df['sell'], 'nettedShortPosition'] = df['nettedShortPosition'].shift(1).fillna(0) + Lots
    df.loc[df['sell'], 'nettedShortAvg'] = (df['nettedShortPosition'].shift(1).fillna(0) * df['nettedShortAvg'].shift(1).fillna(0) + Lots * df['close']) / (df['nettedShortPosition'].shift(1).fillna(0) + Lots)

    df['sellProfitCut'] = 0.0
    df.loc[df['nettedShortPosition'].shift(1) == 0, 'sellProfitCut'] = df['close'] * multiplier
    df.loc[df['nettedShortPosition'] == 0, 'sellProfitCut'] = 0

    calc = trading_time
    df = calculate_buy_profit(df, calc, df['nettedLongAvg'], df['nettedLongPosition'])
    df = calculate_sell_profit(df, calc, df['nettedShortAvg'], df['nettedShortPosition'])

    df['buyProfitCutoff'] = (df['buyProfitCut'] > 0) & (df['sum'] >= df['buyProfitCut'])
    df['sellProfitCutoff'] = (df['sellProfitCut'] > 0) & (df['sum'] >= df['sellProfitCut'])

    df.loc[df['buyProfitCutoff'] | df['sellProfitCutoff'], ['nettedLongPosition', 'nettedLongAvg', 'nettedShortPosition', 'nettedShortAvg']] = 0

    return df

# Example DataFrame
df = pd.DataFrame({'open': [], 'close': [], 'high': [], 'low': []})
# Add your data loading logic here

# Apply trading logic
df['tradingTime'] = is_trading_time(df, StartDay, StartTime, EndDay, EndTime)
df = running_4775_dots_v2_reset(df, df['tradingTime'], XBarsDelay, Multiplier)
df = running_4775_dots_v2_reset(df, df['tradingTime'], XBarsDelay2, Multiplier2)

# Plot the results
plt.figure(figsize=(12, 6))
plt.plot(df.index, df['close'], label='Close Price')
if ShowHAArrow2:
    plt.scatter(df.index[df['buyProfitCutoff']], df['close'][df['buyProfitCutoff']], color='blue', label='Buy Signal', marker='^')
    plt.scatter(df.index[df['sellProfitCutoff']], df['close'][df['sellProfitCutoff']], color='yellow', label='Sell Signal', marker='v')
plt.legend()
plt.show()
