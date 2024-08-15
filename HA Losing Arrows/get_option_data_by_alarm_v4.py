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

class CurKlineTest(CurKlineHandlerBase):
    def on_recv_rsp(self, rsp_pb):
        ret_code, data = super(CurKlineTest,self).on_recv_rsp(rsp_pb)
        if ret_code != RET_OK:
            print("CurKlineTest: error, msg: %s"% data)
            return RET_ERROR, data
        print("CurKlineTest ", data) # CurKlineTest's own processing logic
        return RET_OK, data

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
            handler = CurKlineTest()
            quote_ctx.set_handler(handler) # Set real-time candlestick callback
            ret, data = quote_ctx.subscribe([code_base_name], [SubType.K_5M]) # Subscribe to the candlestick data type, OpenD starts to receive continuous push from the server
            if ret == RET_OK:
                print(data)
            else:
                print('error:', data)
            time.sleep(15) # Set the script to receive OpenD push duration to 15 seconds

        quote_ctx.close()
        
    return result_str