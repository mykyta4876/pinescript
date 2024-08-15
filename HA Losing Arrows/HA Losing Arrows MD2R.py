"""
python "HA Losing Arrows v6.py" -f "BATS_QQQ, 5.csv" -sd 20240501 -st 1200 -ed 20240511 -et 2300 -m1 0.5 -m2 0.3
python "HA Losing Arrows MD2R.py" -f "BATS_QQQ, 5.csv" -sd 20240301 -m 0.5 -r 14
python "HA Losing Arrows MD2R.py" -f "US.NVDA240726P123000.csv" -m 0.001
https://chatgpt.com/share/ad5e24b1-d173-4332-bbf5-e74a1d6fe86b
"""


import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import argparse
import os
from datetime import datetime

# Input parameters
Lots = 1.0
TickSize = 1.0
TickValue = 1.0
ShowHAArrow2 = True

Multiplier = 0.5
XBarsDelay = 0


StartDay = 0  # YYYYMMDD
StartTime = 0  # HHmm
EndDay = 0  # YYYYMMDD
EndTime = 0  # HHmm

"""
def is_trading_time(df, start_day, start_time, end_day, end_time):
    df['yyyymmdd'] = df['time'].dt.year * 10000 + df['time'].dt.month * 100 + df['time'].dt.day
    df['hhmm'] = df['time'].dt.hour * 100 + df['time'].dt.minute

    v1 = (start_day > 0) & ((df['yyyymmdd'] >= start_day) & (df['hhmm'] >= start_time)) | (start_day == 0)
    v2 = (end_day > 0) & ((df['yyyymmdd'] <= end_day) & ((end_time == 0) | (df['hhmm'] <= end_time))) | (start_day == 0)

    trading_time = v1 & v2
    return trading_time
"""

def is_trading_time(df, start_day, start_time, end_day, end_time):
    df['yyyymmdd'] = df['time'].dt.year * 10000 + df['time'].dt.month * 100 + df['time'].dt.day
    df['hhmm'] = df['time'].dt.hour * 100 + df['time'].dt.minute

    df['calc'] = True
    if start_day > 0:
        df['calc'] = (df['yyyymmdd'] >= start_day)

    trading_time = df['calc']
    return trading_time

def entry_signal(df, xbars_delay):
    df['up_arrow'] = 0
    df['down_arrow'] = 0

    for i in range(1, len(df)):
        df.at[i, 'up_arrow'] = df['close'].iloc[i] > df['open'].iloc[i - xbars_delay]
        df.at[i, 'down_arrow'] = df['close'].iloc[i] < df['open'].iloc[i - xbars_delay]

    return df

"""
def entry_signal(df, xbars_delay):
    df['up_arrow'] = df['close'] > df['open'].shift(xbars_delay)
    df['down_arrow'] = df['close'] < df['open'].shift(xbars_delay)
    return df
"""

def calculate_buy_profit(df, index):
    global TickSize
    global TickValue

    i = index
    if df['calc'].iloc[i]:
        df.at[i, 'buy_profit'] = (df['close'].iloc[i] - df['netted_long_avg'].iloc[i]) / TickSize * df['netted_long_position'].iloc[i] * TickValue
        #print(df['close'].iloc[i], df['netted_long_avg'].iloc[i], df['netted_long_position'].iloc[i], df['buy_profit'].iloc[i])
        #input()
    else:
        df.at[i, 'buy_profit'] = df['buy_profit'].iloc[i-1]

    return df
    

def calculate_sell_profit(df, index):
    global TickSize
    global TickValue

    i = index
    if df['calc'].iloc[i]:
        df.at[i, 'sell_profit'] = (df['netted_short_avg'].iloc[i] - df['close'].iloc[i]) / TickSize * df['netted_short_position'].iloc[i] * TickValue
    else:
        df.at[i, 'sell_profit'] = df['sell_profit'].iloc[i-1]

    return df
    
def running_4775_dots_v2_reset(df, trading_time, xbars_delay, multiplier, i):
    if df['buy'].iloc[i]:
        df.at[i, 'netted_long_position'] = df['netted_long_position'].iloc[i-1] + Lots
        df.at[i, 'netted_long_avg'] = (df['netted_long_position'].iloc[i-1] * df['netted_long_avg'].iloc[i-1] + Lots * df['close'].iloc[i]) / (df['netted_long_position'].iloc[i-1] + Lots)
    else:
        df.at[i, 'netted_long_position'] = df['netted_long_position'].iloc[i-1]
        df.at[i, 'netted_long_avg'] = df['netted_long_avg'].iloc[i-1]

    if df['netted_long_position'].iloc[i-1] == 0 and df['netted_long_position'].iloc[i] > 0:
        df.at[i, 'buy_profit_cut'] = df['close'].iloc[i] * multiplier
    elif df['netted_long_position'].iloc[i] == 0:
        df.at[i, 'buy_profit_cut'] = 0
    else:
        df.at[i, 'buy_profit_cut'] = df['buy_profit_cut'].iloc[i - 1]

    if df['sell'].iloc[i]:
        df.at[i, 'netted_short_position'] = df['netted_short_position'].iloc[i-1] + Lots
        df.at[i, 'netted_short_avg'] = (df['netted_short_position'].iloc[i-1] * df['netted_short_avg'].iloc[i-1] + Lots * df['close'].iloc[i]) / (df['netted_short_position'].iloc[i-1] + Lots)
    else:
        df.at[i, 'netted_short_position'] = df['netted_short_position'].iloc[i-1]
        df.at[i, 'netted_short_avg'] = df['netted_short_avg'].iloc[i-1]

    if df['netted_short_position'].iloc[i-1] == 0 and df['netted_short_position'].iloc[i] > 0:
        df.at[i, 'sell_profit_cut'] = df['close'].iloc[i] * multiplier
    elif df['netted_short_position'].iloc[i] == 0:
        df.at[i, 'sell_profit_cut'] = 0
    else:
        df.at[i, 'sell_profit_cut'] = df['sell_profit_cut'].iloc[i - 1]
        
    df = calculate_buy_profit(df, i)
    df = calculate_sell_profit(df, i)
    
    df.at[i, 'buy_profit_cutoff'] = df['buy_profit_cut'].iloc[i] > 0 and (df['buy_profit'].iloc[i] >= df['buy_profit_cut'].iloc[i])
    df.at[i, 'sell_profit_cutoff'] = df['sell_profit_cut'].iloc[i] > 0 and (df['sell_profit'].iloc[i] >= df['sell_profit_cut'].iloc[i])
    
    if df['buy_profit_cutoff'].iloc[i] | df['sell_profit_cutoff'].iloc[i]:
        df.at[i, 'netted_long_position'] = 0
        df.at[i, 'netted_long_avg'] = 0
        df.at[i, 'netted_short_position'] = 0
        df.at[i, 'netted_short_avg'] = 0
        """
        """

    return df

def ta_change(series):
    return series.diff()

def ta_rma(series, length):
    alpha = 1 / length
    return series.ewm(alpha=alpha, adjust=False).mean()

def ta_ema(series, length):
    return series.ewm(span=length, adjust=False).mean()

def is_zero(val, eps):
    return abs(val) <= eps

def sum_with_check(fst, snd):
    EPS = 1e-10
    res = fst + snd
    if is_zero(res, EPS):
        return 0
    elif not is_zero(res, 1e-4):
        return res
    else:
        return 15

def ta_stdev(src, length):
    avg = src.rolling(window=length).mean()
    sum_of_square_deviations = np.zeros_like(src)
    
    for i in range(length - 1, len(src)):
        sum_of_square_deviations[i] = sum(sum_with_check(src[j], -avg[i]) ** 2 for j in range(i - length + 1, i + 1))
    
    stdev = np.sqrt(sum_of_square_deviations / length)
    return stdev

def ta_tr(data):
    return np.maximum(data['high'] - data['low'], np.maximum(abs(data['high'] - data['close'].shift()), abs(data['low'] - data['close'].shift())))

def dirmov(data, length):
    up = ta_change(data['high'])
    down = -ta_change(data['low'])
    plusDM = np.where((up > down) & (up > 0), up, 0)
    minusDM = np.where((down > up) & (down > 0), down, 0)
    truerange = ta_rma(ta_tr(data), length)
    plus = 100 * ta_rma(pd.Series(plusDM), length) / truerange
    minus = 100 * ta_rma(pd.Series(minusDM), length) / truerange

    return plus, minus

def adx(data, dilen, adxlen):
    plus, minus = dirmov(data, dilen)
    sum_dm = plus + minus
    adx_val = 100 * ta_rma(abs(plus - minus) / np.where(sum_dm == 0, 1, sum_dm), adxlen)
    diff = plus - minus
    return adx_val, diff

def adx_v8(data, adxlen, dev1, dev2):
    sig, diff = adx(data, adxlen, adxlen)
    diffema = ta_ema(diff, adxlen)
    std = ta_stdev(diff, adxlen)
    bbup1 = diffema + dev1 * std
    bblo1 = diffema - dev1 * std
    bbup2 = diffema + dev2 * std
    bblo2 = diffema - dev2 * std
    return sig, diff, diffema, std, bbup1, bblo1, bbup2, bblo2

def ADX_Simple_v3_adx_v8(data, adxlen, dev1, dev2):
    sig, diff, diffema, std, bbup1, bblo1, bbup2, bblo2 = adx_v8(data, adxlen, dev1, dev2)
    
    positive = sum([diffema > 0, bbup1 > 0, bblo1 > 0, bbup2 > 0, bblo2 > 0])
    negative = sum([diffema < 0, bbup1 < 0, bblo1 < 0, bbup2 < 0, bblo2 < 0])
    
    positive2 = sum([diff > diffema, diff > bbup1, diff > bblo1, diff > bbup2, diff > bblo2])
    negative2 = sum([diff < diffema, diff < bbup1, diff < bblo1, diff < bbup2, diff < bblo2])
    
    count = positive + positive2 - negative - negative2
    avg = ta_ema(pd.Series(count), adxlen)
    
    return count, avg

def parse_arguments():
    parser = argparse.ArgumentParser(description="HA Losig Arrows")

    # Add arguments
    parser.add_argument("--file", "-f", help="name of historical data file", required=True)
    parser.add_argument("--start_day", "-sd", help="Start Day (yyyymmdd)", type=int)
    parser.add_argument("--multiplier", "-m", help="Multiplier", type=float)
    parser.add_argument("--restriction_len", "-r", help="restriction length", type=int, default=0)

    """
    parser.add_argument("--end_day", "-ed", help="Start Day (yyyymmdd)", type=int)
    parser.add_argument("--start_time", "-st", help="Start Time (hhmm)", type=int)
    parser.add_argument("--end_time", "-et", help="Start Time (hhmm)", type=int)
    parser.add_argument("--multiplier2", "-m2", help="Multiplier 1", type=float)
    """

    args = parser.parse_args()

    return args

# Adx simple Parameters
adxlen = 14
deviation1 = 1.0
deviation2 = 2.0

# Parse command-line arguments
args = parse_arguments()

if args.restriction_len != None:
    adxlen = args.restriction_len

if args.start_day != None:
    StartDay = args.start_day

"""
if args.start_time != None:
    StartTime = args.start_time
    
if args.end_day != None:
    EndDay = args.end_day
    
if args.end_time != None:
    EndTime = args.end_time
"""

if args.multiplier != None:
    Multiplier = args.multiplier
"""    
if args.multiplier2 != None:
    XBarsDelay2 = args.multiplier2
"""

datetime_start = None

str_start_date = ""
if StartDay > 0:
    str_start_date = str(StartDay)

    if StartTime == 0:
        str_start_date = str_start_date + " 0000"
    else:
        str_start_date = str_start_date + " " + str(StartTime)

    print(f"[-] Start Date: {str_start_date}")
    
    # Convert the string to a datetime object
    datetime_start = datetime.strptime(str_start_date, "%Y%m%d %H%M")

    # Print the datetime object
    print(datetime_start)

datetime_end = None
str_end_date = ""
if EndDay > 0:
    str_end_date = str(EndDay)

    if EndTime == 0:
        str_end_date = str_end_date + " 0000"
    else:
        str_end_date = str_end_date + " " + str(EndTime)

    print(f"[-] End Date: {str_end_date}")

    # Convert the string to a datetime object
    datetime_end = datetime.strptime(str_end_date, "%Y%m%d %H%M")

    # Print the datetime object
    print(datetime_end)

filepath = args.file
if not os.path.isfile(filepath):
    print(f"[-] error: don't exist file ({filepath})")
    exit(0)

# Load historical data
df = pd.read_csv(filepath)

for i in range(0, len(df)):
    str_time = df['time'].iloc[i]
    str_time = str_time.replace("T", " ")

    p = str_time.find(":")

    if p != -1:
        str_before = str_time[:p]
        str_next = str_time[p:]
        p = str_next.find("-")

        str_tmp = str_next
        if p != -1:
            str_tmp = str_next[:p]

        str_time = str_before + str_tmp

    df.at[i, 'time'] = str_time



df['time'] = pd.to_datetime(df['time'])
"""
# Filter the DataFrame
filtered_df = df[(df['time'] > datetime_start) & (df['time'] < datetime_end)]
if len(filtered_df) > 0:
    print(filtered_df)
"""

# Apply the strategy
trading_time = is_trading_time(df, StartDay, StartTime, EndDay, EndTime)

df = entry_signal(df, XBarsDelay)

df['count'] = 0.0
df['avg'] = 0.0

if adxlen > 0:
    # Calculate the indicators
    df['count'], df['avg'] = ADX_Simple_v3_adx_v8(df, adxlen, deviation1, deviation2)

    for i in range(adxlen * 2):
        df.at[i, 'count'] = 0
        df.at[i, 'avg'] = 0

df['buy'] = df['up_arrow'] & trading_time
df['sell'] = df['down_arrow'] & trading_time

df['netted_long_position'] = 0.0
df['netted_short_position'] = 0.0

df['netted_long_avg'] = 0.0
df['netted_short_avg'] = 0.0

df['buy_profit_cut'] = 0.0
df['sell_profit_cut'] = 0.0

df['buy_profit_cutoff'] = False
df['sell_profit_cutoff'] = False

df['buy_profit'] = 0.0
df['sell_profit'] = 0.0

df['calc'] = trading_time


last_profit_cut1 = 0

# Calculate upArrow2 and dnArrow2
df['lastDotAbove1Open'] = np.nan
df['lastDotBelow1Open'] = np.nan

df['upArrow2'] = False
df['dnArrow2'] = False

df['upArrow2r'] = False
df['dnArrow2r'] = False

df.at[0, 'dotbelow1'] = False
df.at[0, 'dotabove1'] = False

for i in range(1, len(df)):
    df = running_4775_dots_v2_reset(df, trading_time, XBarsDelay, Multiplier, i)
    buy_profit_cutoff1 = df.at[i, 'buy_profit_cutoff']
    sell_profit_cutoff1 = df.at[i, 'sell_profit_cutoff']

    buy_profit_cutoff2 = buy_profit_cutoff1
    sell_profit_cutoff2 = sell_profit_cutoff1

    df.at[i, 'dotbelow1'] = sell_profit_cutoff1
    df.at[i, 'dotabove1'] = buy_profit_cutoff1

    if last_profit_cut1 > 0:
        df.at[i, 'dotabove1'] = False

    if last_profit_cut1 < 0:
        df.at[i, 'dotbelow1'] = False

    if df['dotabove1'].iloc[i] == True:
        last_profit_cut1 = 1

    if df['dotbelow1'].iloc[i] == True:
        last_profit_cut1 = -1

    if df['dotabove1'].iloc[i-1]:
        df.at[i, 'lastDotAbove1Open'] = df['open'].iloc[i]
    else:
        df.at[i, 'lastDotAbove1Open'] = df['lastDotAbove1Open'].iloc[i-1]
        
    if df['dotbelow1'].iloc[i-1]:
        df.at[i, 'lastDotBelow1Open'] = df['open'].iloc[i]
    else:
        df.at[i, 'lastDotBelow1Open'] = df['lastDotBelow1Open'].iloc[i-1]

    if sell_profit_cutoff2:
        if not np.isnan(df['lastDotAbove1Open'].iloc[i]) and df['close'].iloc[i] <= df['lastDotAbove1Open'].iloc[i]:
            df.at[i, 'dnArrow2'] = True

            if adxlen > 0:
                if df['count'].iloc[i] < df['avg'].iloc[i]:
                    df.at[i, 'dnArrow2r'] = True
            else:
                df.at[i, 'dnArrow2r'] = True

    if buy_profit_cutoff2:
        if not np.isnan(df['lastDotBelow1Open'].iloc[i]) and df['close'].iloc[i] >= df['lastDotBelow1Open'].iloc[i]:
            df.at[i, 'upArrow2'] = True

            if adxlen > 0:
                if df['count'].iloc[i] > df['avg'].iloc[i]:
                    df.at[i, 'upArrow2r'] = True
            else:
                df.at[i, 'upArrow2r'] = True


# Export the up_arrow, down_arrow, upArrow2, and dnArrow2 signals to CSV
# output_df = df[['time', 'open', 'high', 'low', 'close', 'Volume', 'upArrow2', 'dnArrow2']]
output_df = df[['time', 'open', 'high', 'low', 'close', 'count', 'avg', 'upArrow2', 'dnArrow2', 'upArrow2r', 'dnArrow2r']]

output_filename = filepath
p = filepath.rfind(".")
if p != -1:
    output_filename = filepath[:p]

output_dbg_df = df[['time', 'open', 'high', 'low', 'close', 'buy', 'sell', 'netted_long_position', 'netted_short_position', 'netted_long_avg', 'netted_short_avg', 'buy_profit_cut', 'sell_profit_cut', 'buy_profit_cutoff', 'sell_profit_cutoff', 'buy_profit', 'sell_profit', 'lastDotAbove1Open', 'lastDotBelow1Open', 'count', 'avg', 'upArrow2', 'dnArrow2', 'upArrow2r', 'dnArrow2r']]
output_dbg_filename = output_filename + ",MD2R,-m " +  str(Multiplier) + "_dbg.csv"
output_dbg_df.to_csv(output_dbg_filename, index=False)

# Filter rows where upArrow2 or dnArrow2 is True
filtered_df = output_df[(output_df['upArrow2']) | (output_df['dnArrow2'])]

output_filename = output_filename + ",MD2R,-m " +  str(Multiplier) + ".csv"

filtered_df.to_csv(output_filename, index=False)
#output_df.to_csv(output_filename, index=False)
print(filtered_df)

print("[-] saved Arrow2 in arrow_signals.csv successfully.")

"""
# Plot the results
plt.figure(figsize=(10, 6))
plt.plot(df['time'], df['close'], label='Close Price')
plt.scatter(df['time'][df['upArrow2']], df['close'][df['upArrow2']], marker='^', color='blue', label='Buy Signal')
plt.scatter(df['time'][df['dnArrow2']], df['close'][df['dnArrow2']], marker='v', color='yellow', label='Sell Signal')
plt.legend()
plt.show()
"""
