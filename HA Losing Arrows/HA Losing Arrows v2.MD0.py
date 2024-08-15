"""
python "HA Losing Arrows v6.py" -f "BATS_QQQ, 5.csv" -sd 20240501 -st 1200 -ed 20240511 -et 2300 -m1 0.5 -m2 0.3
python "HA Losing Arrows v2.MD1.py" -f "BATS_QQQ, 5.csv" -sd 20240301 -m 0.4
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
XBarsDelay = 1

Multiplier2 = 0.5
XBarsDelay2 = 1

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
        df.at[i, 'up_arrow'] = df['close'].iloc[i] > df['open'].iloc[i - 1]
        df.at[i, 'down_arrow'] = df['close'].iloc[i] < df['open'].iloc[i - 1]

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
    
def running_4775_dots_v2_reset(df, trading_time, xbars_delay, multiplier):
    df = entry_signal(df, xbars_delay)
    
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

    for i in range(1, len(df)):
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

    return df[['buy_profit_cutoff', 'sell_profit_cutoff', 'netted_long_position', 'netted_long_avg', 'buy_profit_cut', 'buy_profit']]

def parse_arguments():
    parser = argparse.ArgumentParser(description="HA Losig Arrows")

    # Add arguments
    parser.add_argument("--file", "-f", help="name of historical data file", required=True)
    parser.add_argument("--start_day", "-sd", help="Start Day (yyyymmdd)", type=int)
    parser.add_argument("--multiplier", "-m", help="Multiplier 1", type=float)

    """
    parser.add_argument("--end_day", "-ed", help="Start Day (yyyymmdd)", type=int)
    parser.add_argument("--start_time", "-st", help="Start Time (hhmm)", type=int)
    parser.add_argument("--end_time", "-et", help="Start Time (hhmm)", type=int)
    parser.add_argument("--multiplier2", "-m2", help="Multiplier 1", type=float)
    """

    args = parser.parse_args()

    return args

# Parse command-line arguments
args = parse_arguments()

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
    XBarsDelay2 = args.multiplier

"""    
if args.multiplier2 != None:
    XBarsDelay2 = args.multiplier2
"""

print(Multiplier)
print(XBarsDelay2)
print(type(Multiplier))
print(type(Multiplier2))
input()
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
df1 = running_4775_dots_v2_reset(df, trading_time, XBarsDelay, Multiplier)
df2 = running_4775_dots_v2_reset(df, trading_time, XBarsDelay2, Multiplier2)
"""
df['netted_long_position1'] = df1['netted_long_position']
df['netted_long_position2'] = df2['netted_long_position']

df['netted_long_avg1'] = df1['netted_long_avg']
df['netted_long_avg2'] = df2['netted_long_avg']

df['buy_profit_cut1'] = df1['buy_profit_cut']
df['buy_profit_cut2'] = df2['buy_profit_cut']

df['buy_profit1'] = df1['buy_profit']
df['buy_profit2'] = df2['buy_profit']
"""

last_profit_cut1 = 0

# Calculate upArrow2 and dnArrow2
df['lastDotAbove1Open'] = np.nan
df['lastDotBelow1Open'] = np.nan

df['upArrow2'] = False
df['dnArrow2'] = False

df.at[0, 'dotbelow1'] = df1['sell_profit_cutoff'].iloc[0]
df.at[0, 'dotabove1'] = df1['buy_profit_cutoff'].iloc[0]
for i in range(1, len(df1)):
    df.at[i, 'dotbelow1'] = df1['sell_profit_cutoff'].iloc[i]
    df.at[i, 'dotabove1'] = df1['buy_profit_cutoff'].iloc[i]

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

    if df2['sell_profit_cutoff'].iloc[i]:
        if not np.isnan(df['lastDotAbove1Open'].iloc[i]) and df['close'].iloc[i] <= df['lastDotAbove1Open'].iloc[i]:
            df.at[i, 'dnArrow2'] = True
    
    if df2['buy_profit_cutoff'].iloc[i]:
        if not np.isnan(df['lastDotBelow1Open'].iloc[i]) and df['close'].iloc[i] >= df['lastDotBelow1Open'].iloc[i]:
            df.at[i, 'upArrow2'] = True


# Export the up_arrow, down_arrow, upArrow2, and dnArrow2 signals to CSV
output_df = df[['time', 'open', 'high', 'low', 'close', 'Volume', 'upArrow2', 'dnArrow2']]

# Filter rows where upArrow2 or dnArrow2 is True
filtered_df = output_df[(output_df['upArrow2']) | (output_df['dnArrow2'])]

# Export the filtered DataFrame to a CSV file
filtered_df.to_csv('filtered_signals.csv', index=False)

output_filename = filepath
p = filepath.rfind(".")
if p != -1:
    output_filename = filepath[:p]

output_filename = output_filename + ",-m " +  str(Multiplier) + ".csv"

filtered_df.to_csv(output_filename, index=False)
print(filtered_df)

print("[-] saved Arrow2 in arrow_signals.csv successfully.")

"""
"""
# Plot the results
plt.figure(figsize=(10, 6))
plt.plot(df['time'], df['close'], label='Close Price')
plt.scatter(df['time'][df['upArrow2']], df['close'][df['upArrow2']], marker='^', color='blue', label='Buy Signal')
plt.scatter(df['time'][df['dnArrow2']], df['close'][df['dnArrow2']], marker='v', color='yellow', label='Sell Signal')
plt.legend()
plt.show()
