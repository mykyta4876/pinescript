#34.127.53.74
import functions_framework
import moomoo as ft
from moomoo import RET_OK, SysConfig
from time import sleep
from datetime import datetime
import pytz
import json

@functions_framework.http
def hello_http(request):
    print("hello_http tests")
    request_json = request.get_json(silent=True)
    request_args = request.args

    if request_json:
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

        quote_ctx = ft.OpenQuoteContext(host='34.127.53.74', port=11111)

        ret, data, page_req_key = quote_ctx.request_history_kline('HK.00700', start='2019-09-11', end='2019-09-18', max_count=5) # 5 per page, request the first page
        if ret == RET_OK:
            json_string = data.to_json(orient='records')
            print(json_string)
        else:
            print(RET_OK)
        #print("Close quote context")
        quote_ctx.close()
    return ""