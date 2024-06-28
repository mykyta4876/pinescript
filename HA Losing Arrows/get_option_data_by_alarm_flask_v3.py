#http:// 208.109.233.174/hello_http
#pip install -r "get_option_data_by_alarm_flask_requirements.txt"
from quart import Quart, request, jsonify
from moomoo import *
import asyncio
from datetime import datetime, timedelta
import pytz
import json

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

    ret_sub, err_message = quote_ctx.subscribe([code_name], [SubType.K_5M], subscribe_push=False)
    # First subscribe to the candlestick type. After the subscription is successful, OpenD will continue to receive pushes from the server, False means that there is no need to push to the script temporarily
    if ret_sub == RET_OK:  # Successfully subscribed
        for i in range(10):
            time.sleep(5 * 60)
            now = datetime.now()
            now_str = now.strftime("%Y-%m-%d %H:%M:%S")

            ret, data = quote_ctx.get_cur_kline(code_name, 1, SubType.K_5M, AuType.QFQ)  # Get the latest 2 candlestick data
            if ret == RET_OK:
                print(f"get_option_data_every_5mins ({now_str}): data")
                print(data)
            else:
                print('get_option_data_every_5mins: error:', data)
    else:
        print('subscription failed', err_message)

    quote_ctx.close()
        


@app.route('/hello_http', methods=['POST'])
async def hello_http():
    print("hello_http tests")
    request_json = await request.get_json(silent=True)

    result_str = ""
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
        
        SysConfig.enable_proto_encrypt(True)
        rsa_path = "private_rsa_key.pem"
        SysConfig.set_init_rsa_file(rsa_path)   # rsa private key file path
        
        datetmp = request_json['date']
        option_value = request_json["option"]
        code_name = "US." + request_json['symbol'] + datetmp[2:]
        if option_value == "put":
            code_name = code_name + "P"
        if option_value == "call":
            code_name = code_name + "C"
        
        code_name = code_name + request_json["strikeprice"] + "000"
        print("code_name= " + code_name)

        quote_ctx = OpenQuoteContext(host='34.127.53.74', port=11111)

        code_base_name = "US." + request_json['symbol']
        
        ret1, data1 = await asyncio.to_thread(quote_ctx.get_option_expiration_date, code_base_name)

        ret_sub, err_message = await asyncio.to_thread(quote_ctx.subscribe, [code_name], [SubType.K_5M], False)
        # First subscribe to the candlestick type. After the subscription is successful, OpenD will continue to receive pushes from the server, False means that there is no need to push to the script temporarily
        if ret_sub == RET_OK:  # Successfully subscribed
            ret, data = await asyncio.to_thread(quote_ctx.get_cur_kline, code_name, 1000, SubType.K_5M, AuType.QFQ)  # Get the latest 2 candlestick data
            if ret == RET_OK:
                print(f"1000 option data")
                print(data)
                get_option_data_every_5mins(code_name)
            else:
                print('error:', data)
        else:
            print('subscription failed', err_message)

        quote_ctx.close()
        
    return result_str

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=80)
