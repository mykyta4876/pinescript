#http:// 208.109.233.174/hello_http
#pip install -r "get_option_data_by_alarm_flask_requirements.txt"
from quart import Quart, request, jsonify
from moomoo import *
import asyncio
from datetime import datetime, timedelta
import pytz
import json
import pandas as pd
import numpy as np
import argparse
import os
import requests
import threading

code_list = []
# ==============================MD2R=======================
Lots = 1.0
TickSize = 1.0
TickValue = 1.0
g_flag_exit_call = False
g_flag_exit_put = False
quote_ctx = None

def is_trading_time(df, start_day, start_time, end_day, end_time):
    df['yyyymmdd'] = df['time'].dt.year * 10000 + df['time'].dt.month * 100 + df['time'].dt.day
    df['hhmm'] = df['time'].dt.hour * 100 + df['time'].dt.minute

    df['calc'] = True
    if start_day > 0:
        df['calc'] = (df['yyyymmdd'] >= start_day)

    trading_time = df['calc']
    return trading_time

def entry_signal(df, xbars_delay):
    df['up_arrow'] = False
    df['down_arrow'] = False

    for i in range(1, len(df)):
        df.at[i, 'up_arrow'] = df['close'].iloc[i] > df['open'].iloc[i - xbars_delay]
        df.at[i, 'down_arrow'] = df['close'].iloc[i] < df['open'].iloc[i - xbars_delay]

    return df

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

def get_signal(df, Multiplier, XBarsDelay, adxlen, start_price, start_time):
    deviation1 = 1.0
    deviation2 = 2.0
    trading_time = True

    df = entry_signal(df, XBarsDelay)

    df['count'] = 0.0
    df['avg'] = 0.0

    if adxlen > 0:
        # Calculate the indicators
        df['count'], df['avg'] = ADX_Simple_v3_adx_v8(df, adxlen, deviation1, deviation2)

        for i in range(adxlen * 2):
            df.at[i, 'count'] = 0
            df.at[i, 'avg'] = 0

    df['buy'] = df['up_arrow']
    df['sell'] = df['down_arrow']

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

                if df['dnArrow2r'].iloc[i] and df['time'].iloc[i] > start_time:
                    if df['close'].iloc[i] <= start_price:
                        return "Sell"
                    else:
                        return "None"

        if buy_profit_cutoff2:
            if not np.isnan(df['lastDotBelow1Open'].iloc[i]) and df['close'].iloc[i] >= df['lastDotBelow1Open'].iloc[i]:
                df.at[i, 'upArrow2'] = True

                if adxlen > 0:
                    if df['count'].iloc[i] > df['avg'].iloc[i]:
                        df.at[i, 'upArrow2r'] = True
                else:
                    df.at[i, 'upArrow2r'] = True


                if df['upArrow2r'].iloc[i] and df['time'].iloc[i] > start_time:
                    if df['close'].iloc[i] >= start_price:
                        return "Buy"
                    else:
                        return "None"

    return ""

def get_signal_thread(quote_ctx, alert_json, code_name, Multiplier, XBarsDelay, adxlen):
    global g_flag_exit_call
    global g_flag_exit_put

    df = get_option_data(quote_ctx, code_name, 1000)
    df['time'] = pd.to_datetime(df['time_key'])

    df_len = len(df)
    start_price = df['close'].iloc[df_len - 1]
    start_time = df['time'].iloc[df_len - 1]

    last_time = datetime.now() + timedelta(minutes=1)
    df_merge_outer = df

    position_type = ""
    df1 = None
    while True:
        if g_flag_exit_call and code_name.find("C") != -1:
            g_flag_exit_call = False
            break

        if g_flag_exit_put and code_name.find("P") != -1:
            g_flag_exit_put = False
            break

        entry_signal_code = ""
        while True:
            while True:
                now_time = datetime.now()
                if now_time > last_time:
                    break

                time.sleep(5)

            last_time = datetime.now() + timedelta(minutes=1)
            df1 = get_option_data(quote_ctx, code_name, 1)
            df1['time'] = pd.to_datetime(df1['time_key'])

            df_merge_outer = df_merge_outer._append(df1, ignore_index=True)
            #df_merge_outer = pd.merge(df_merge_outer, df1, on='time', how='outer')

            print("[-] =====================df_merge_outer===========================")
            print(df_merge_outer)

            entry_signal_code = get_signal(df_merge_outer, Multiplier, XBarsDelay, adxlen, start_price, start_time)

            if len(entry_signal_code) > 0 and entry_signal_code != "None":
                break

        print(f"[-] entry signal= {entry_signal_code}")

        result_json = alert_json
        if len(position_type) > 0:
            result_json['quantity'] = str(int(alert_json['quantity']) * 2)

        result_json['side'] = entry_signal_code
        json_data = json.dumps(result_json)
        url = "https://alerts.badabrook.com/"

        print("[-] sending entry signal => " + json_data)

        """
        # Send the POST request with the JSON data
        response = requests.post(url, data=json_data, headers={'Content-Type': 'application/json'})

        # Print the response from the server
        print("[-] alerts.badabrook.com response= " + str(response.status_code))

        start_price = df1['close'].iloc[0]
        start_time = df1['time'].iloc[0]
        """

    code_list.remove(code_name)


def parse_arguments():
    parser = argparse.ArgumentParser(description="HA Losig Arrows")

    # Add arguments
    parser.add_argument("--multiplier", "-m", help="Multiplier", type=float, default=0.5)
    parser.add_argument("--delay", "-d", help="delay", type=int, default=0)
    parser.add_argument("--restriction_len", "-r", help="restriction length", type=int, default=0)

    args = parser.parse_args()

    return args


# Parse command-line arguments
args = parse_arguments()

Multiplier = args.multiplier
XBarsDelay = args.delay

# Adx simple Parameters
adxlen = args.restriction_len

# ========================================================

app = Quart(__name__)

def get_row_by_code(df, code):
    result = df[df['code'] == code]
    if not result.empty:
        row = result.iloc[0].to_dict()  # Convert the first matching row to a dictionary
        return json.dumps(row)  # Convert the dictionary to a JSON string
    else:
        return None

def get_option_data_every_5mins(code_name):
    quote_ctx = OpenQuoteContext(host='34.127.53.74', port=11111)

    ret_sub, err_message = quote_ctx.subscribe([code_name], [SubType.K_1M], subscribe_push=False)
    # First subscribe to the candlestick type. After the subscription is successful, OpenD will continue to receive pushes from the server, False means that there is no need to push to the script temporarily
    if ret_sub == RET_OK:  # Successfully subscribed
        for i in range(10):
            time.sleep(5 * 60)
            now = datetime.now()
            now_str = now.strftime("%Y-%m-%d %H:%M:%S")

            ret, data = quote_ctx.get_cur_kline(code_name, 1, SubType.K_1M, AuType.QFQ)  # Get the latest 2 candlestick data
            if ret == RET_OK:
                print(f"get_option_data_every_5mins ({now_str}): data")
                print(data)
            else:
                print('get_option_data_every_5mins: error:', data)
    else:
        print('subscription failed', err_message)

    quote_ctx.close()

def get_option_data(quote_ctx, code_name, count):

    ret_sub, err_message = quote_ctx.subscribe([code_name], [SubType.K_1M], subscribe_push=False)
    # First subscribe to the candlestick type. After the subscription is successful, OpenD will continue to receive pushes from the server, False means that there is no need to push to the script temporarily
    if ret_sub == RET_OK:  # Successfully subscribed
        ret, data = quote_ctx.get_cur_kline(code_name, count, SubType.K_1M, AuType.QFQ)  # Get the latest 2 candlestick data
        if ret == RET_OK:
            now = datetime.now()
            now_str = now.strftime("%Y-%m-%d %H:%M:%S")
            print(f"get_option_data ({now_str}): data")
            print(data)
        else:
            print('get_option_data: error:', data)
    else:
        print('subscription failed', err_message)


    return data


@app.route('/hello_http', methods=['POST'])
async def hello_http():
    global Multiplier
    global XBarsDelay
    global adxlen
    global g_flag_exit_call
    global g_flag_exit_put
    global quote_ctx

    print("hello_http tests")
    request_json = await request.get_json(silent=True)

    result_str = ""
    if request_json and "action" in request_json:
        action_str = request_json['action']
        if action_str == "exit_puts":
            g_flag_exit_put = True

        if action_str == "exit_calls":
            g_flag_exit_call = True

        # Get the current UTC time
        now_utc = datetime.now(pytz.utc)

        # Convert to EST (Eastern Standard Time)
        est_tz = pytz.timezone('US/Eastern')
        now_est = now_utc.astimezone(est_tz)

        # Format the time as a string
        now_est_str = now_est.strftime("%Y-%m-%d %H:%M:%S %Z%z")

        request_json['timestamp'] = now_est_str

        # Convert the Python dictionary to a JSON string
        json_data = json.dumps(request_json)

        # Print the response from the server
        print("alert_data= " + json_data)
        
        """
        # Send the POST request with the JSON data
        response = requests.post(url, data=json_data, headers={'Content-Type': 'application/json'})

        # Print the response from the server
        print("[-] alerts.badabrook.com response= " + str(response.status_code))
        """

        return ""

    if request_json and "symbol" in request_json and "option" in request_json:
        # Get the current UTC time
        now_utc = datetime.now(pytz.utc)

        # Convert to EST (Eastern Standard Time)
        est_tz = pytz.timezone('US/Eastern')
        now_est = now_utc.astimezone(est_tz)

        # Format the time as a string
        now_est_str = now_est.strftime("%Y-%m-%d %H:%M:%S %Z%z")

        request_json['timestamp'] = now_est_str
        
        # Convert the Python dictionary to a JSON string
        json_data = json.dumps(request_json)

        # Print the response from the server
        print("alert_data= " + json_data)
        
        datetmp = request_json['date']
        option_value = request_json["option"]
        code_name = "US." + request_json['symbol'] + datetmp[2:]
        if option_value == "put":
            code_name = code_name + "P"
        if option_value == "call":
            code_name = code_name + "C"
        
        code_name = code_name + request_json["strikeprice"] + "000"
        print("code_name= " + code_name)

        if code_name in code_list:
            return ""

        code_list.append(code_name)

        threading.Thread(target=get_signal_thread, args=(quote_ctx, request_json, code_name, Multiplier, XBarsDelay, adxlen))
        
        #get_signal_thread(request_json, code_name, Multiplier, XBarsDelay, adxlen)

    return result_str

if __name__ == '__main__':
    SysConfig.enable_proto_encrypt(True)
    rsa_path = "private_rsa_key.pem"
    SysConfig.set_init_rsa_file(rsa_path)   # rsa private key file path
    
    quote_ctx = OpenQuoteContext(host='34.127.53.74', port=11111)
    app.run(host='0.0.0.0', port=80)
    #quote_ctx.close()
