#34.127.53.74
import functions_framework
from moomoo import *
from time import sleep
from datetime import datetime
import pytz
import json

def get_row_by_code(df, code):
    result = df[df['code'] == code]
    if not result.empty:
        row = result.iloc[0].to_dict()  # Convert the first matching row to a dictionary
        return json.dumps(row)  # Convert the dictionary to a JSON string
    else:
        return None

@functions_framework.http
def hello_http(request):
    print("hello_http tests")
    request_json = request.get_json(silent=True)
    request_args = request.args

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
        
        ret1, data1 = quote_ctx.get_option_expiration_date(code=code_base_name)

        filter1 = OptionDataFilter()
        filter1.delta_min = 0
        filter1.delta_max = 0.1

        json_row = None
        if ret1 == RET_OK:
            str_date = datetmp[:4] + "-" + datetmp[4:6] + "-" + datetmp[6:]
            expiration_date_list = data1['strike_time'].values.tolist()
            print(expiration_date_list)
            if str_date in expiration_date_list:
                ret2, data2 = quote_ctx.get_option_chain(code=code_base_name, start=str_date, end=str_date)
                if ret2 == RET_OK:
                    result_str = result_str + str(data2)
                    print(data2)
                    print(data2['code'][0])  # Take the first stock code
                    print(data2['code'].values.tolist())  # Convert to list
                    json_row = get_row_by_code(data2, code_name)
                else:
                    print('error:', data2)
                time.sleep(3)
        else:
            print('error:', data1)

        print("Row found(" + code_name + "): ", json_row)
        
        if json_row != None:
            ret_sub, err_message = quote_ctx.subscribe([code_name], [SubType.K_5M], subscribe_push=False)
            # First subscribe to the candlestick type. After the subscription is successful, OpenD will continue to receive pushes from the server, False means that there is no need to push to the script temporarily
            if ret_sub == RET_OK:  # Successfully subscribed
                ret, data = quote_ctx.get_cur_kline(code_name, 1000, SubType.K_5M, AuType.QFQ)  # Get the latest 2 candlestick data of HK.00700
                if ret == RET_OK:
                    #print(data)
                    data_len = data.shape[0]
                    column_names = data.columns
                    for i in range(data_len):
                        print("index= ", i)
                        for column_name in column_names:
                            print(column_name, "= ", data[column_name][i])

                else:
                    print('error:', data)
            else:
                print('subscription failed', err_message)
        quote_ctx.close()
        
    return result_str