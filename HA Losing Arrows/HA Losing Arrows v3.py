import pandas as pd
import numpy as np

# Load data from CSV
data = pd.read_csv('Sample Data Set.csv')

# Ensure data is sorted by time
data['time'] = pd.to_datetime(data['time'])
data.sort_values('time', inplace=True)
data.reset_index(drop=True, inplace=True)

# Extract columns
open_ = data['open']
close = data['close']

# Inputs
Lots = 1.0
TickSize = 1.0
TickValue = 1.0
ShowHAArrow2 = True

Multiplier = 0.5
XBarsDelay = 1
Multiplier2 = 0.5
XBarsDelay2 = 1

StartDay = 0
StartTime = 0
EndDay = 0
EndTime = 0

def is_trading_time(row):
    yyyymmdd = row.time.year * 10000 + row.time.month * 100 + row.time.day
    hhmm = row.time.hour * 100 + row.time.minute
    v1 = StartDay > 0 and (yyyymmdd >= StartDay and hhmm >= StartTime)
    v2 = EndDay > 0 and (yyyymmdd <= EndDay and (EndTime == 0 or hhmm <= EndTime))
    return v1 and v2

data['tradingTime'] = data.apply(is_trading_time, axis=1)

def entry_signal(df, XBarsDelay):
    upArrow = df['close'] > df['open'].shift(XBarsDelay)
    downArrow = df['close'] < df['open'].shift(XBarsDelay)
    return upArrow, downArrow

def calculate_profit(df, calc, netted_avg, netted_position, side):
    sum_ = 0.0
    total_positions = 0.0
    if calc:
        if side == 'buy':
            sum_ = (df['close'] - netted_avg) / TickSize * netted_position * TickValue
        else:
            sum_ = (netted_avg - df['close']) / TickSize * netted_position * TickValue
        total_positions = netted_position
    return sum_, total_positions

def running_4775_dots_reset(df, tradingTime, XBarsDelay, multiplier):
    upArrow, downArrow = entry_signal(df, XBarsDelay)
    df['buy'] = upArrow & tradingTime
    df['sell'] = downArrow & tradingTime

    df['buyProfitCutoff'] = False
    df['sellProfitCutoff'] = False

    df['nettedLongPosition'] = 0.0
    df['nettedShortPosition'] = 0.0

    df['nettedLongAvg'] = 0.0
    df['nettedShortAvg'] = 0.0

    df.loc[df['buy'], 'nettedLongPosition'] = df['nettedLongPosition'].shift(1).fillna(0) + Lots
    df.loc[df['buy'], 'nettedLongAvg'] = (
        df['nettedLongPosition'].shift(1).fillna(0) * df['nettedLongAvg'].shift(1).fillna(0) +
        Lots * df['close']
    ) / (df['nettedLongPosition'].shift(1).fillna(0) + Lots)

    df['buyProfitCut'] = np.where(
        (df['nettedLongPosition'].shift(1).fillna(0) == 0) & (df['nettedLongPosition'] > 0),
        df['close'] * multiplier,
        0
    )

    df.loc[df['sell'], 'nettedShortPosition'] = df['nettedShortPosition'].shift(1).fillna(0) + Lots
    df.loc[df['sell'], 'nettedShortAvg'] = (
        df['nettedShortPosition'].shift(1).fillna(0) * df['nettedShortAvg'].shift(1).fillna(0) +
        Lots * df['close']
    ) / (df['nettedShortPosition'].shift(1).fillna(0) + Lots)

    df['sellProfitCut'] = np.where(
        (df['nettedShortPosition'].shift(1).fillna(0) == 0) & (df['nettedShortPosition'] > 0),
        df['close'] * multiplier,
        0
    )

    df['buyProfit'], df['totalbuypositions'] = zip(*df.apply(
        lambda row: calculate_profit(row, tradingTime, row['nettedLongAvg'], row['nettedLongPosition'], 'buy'),
        axis=1
    ))
    df['sellProfit'], df['totalsellpositions'] = zip(*df.apply(
        lambda row: calculate_profit(row, tradingTime, row['nettedShortAvg'], row['nettedShortPosition'], 'sell'),
        axis=1
    ))

    df['buyProfitCutoff'] = df['buyProfitCut'] > 0 & (df['buyProfit'] >= df['buyProfitCut'])
    df['sellProfitCutoff'] = df['sellProfitCut'] > 0 & (df['sellProfit'] >= df['sellProfitCut'])

    df['exitbuy'] = df['buyProfitCutoff']
    df['exitsell'] = df['sellProfitCutoff']

    df.loc[df['exitbuy'] | df['exitsell'], 'nettedLongPosition'] = 0
    df.loc[df['exitbuy'] | df['exitsell'], 'nettedLongAvg'] = 0

    df.loc[df['exitbuy'] | df['exitsell'], 'nettedShortPosition'] = 0
    df.loc[df['exitbuy'] | df['exitsell'], 'nettedShortAvg'] = 0

    return df['buyProfitCutoff'], df['sellProfitCutoff']

data['buyProfitCutoff1'], data['sellProfitCutoff1'] = running_4775_dots_reset(data, data['tradingTime'], XBarsDelay, Multiplier)
data['buyProfitCutoff2'], data['sellProfitCutoff2'] = running_4775_dots_reset(data, data['tradingTime'], XBarsDelay2, Multiplier2)

lastProfitCut1 = 0

UpToDown1 = True
data['dotbelow1'] = data['sellProfitCutoff1']
data['dotabove1'] = data['buyProfitCutoff1']

lastProfitCut2 = 0

UpToDown2 = False
data['dotbelow2'] = data['sellProfitCutoff2']
data['dotabove2'] = data['buyProfitCutoff2']

if UpToDown2:
    if lastProfitCut2 > 0:
        data['dotabove2'] = False
    if lastProfitCut2 < 0:
        data['dotbelow2'] = False

data['lastDotAbove1Open'] = np.nan
data['lastDotBelow1Open'] = np.nan

data.loc[data['dotabove1'].shift(1), 'lastDotAbove1Open'] = data['open']
data.loc[data['dotbelow1'].shift(1), 'lastDotBelow1Open'] = data['open']

data['upArrow2'] = False
data['dnArrow2'] = False

data.loc[(data['dotabove2'] & ~data['lastDotBelow1Open'].isna() & (data['close'] >= data['lastDotBelow1Open'])), 'upArrow2'] = True
data.loc[(data['dotbelow2'] & ~data['lastDotAbove1Open'].isna() & (data['close'] <= data['lastDotAbove1Open'])), 'dnArrow2'] = True

# Plotting
import matplotlib.pyplot as plt

plt.figure(figsize=(14, 7))

plt.plot(data['time'], data['close'], label='Close Price', color='black')
plt.scatter(data[data['upArrow2'].shift(1)]['time'], data[data['upArrow2'].shift(1)]['close'], marker='^', color='blue', label='Up Arrow', s=100)
plt.scatter(data[data['dnArrow2'].shift(1)]['time'], data[data['dnArrow2'].shift(1)]['close'], marker='v', color='yellow', label='Down Arrow', s=100)

plt.legend()
plt.show()
