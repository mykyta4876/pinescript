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
    #if request_json and "symbol" in request_json:
    # Get the current UTC time
    now_utc = datetime.now(pytz.utc)

    # Convert to EST (Eastern Standard Time)
    est_tz = pytz.timezone('US/Eastern')
    now_est = now_utc.astimezone(est_tz)

    # Format the time as a string
    now_est_str = now_est.strftime("%Y-%m-%d %H:%M:%S %Z%z")

    """
    request_json['timestamp'] = now_est_str
    
    # Convert the Python dictionary to a JSON string
    json_data = json.dumps(request_json)

    # Print the response from the server
    print("alert_data= " + json_data)
    """
     
    SysConfig.enable_proto_encrypt(True)
    rsa_path = "private_rsa_key.pem"
    SysConfig.set_init_rsa_file(rsa_path)   # rsa private key file path
    
    """
    datetmp = request_json['date']
    code_name = "US." + request_json['symbol'] + datetmp[2:]
    if request_json["option"] == "put":
        code_name = code_name + "P"
    if request_json["option"] == "call":
        code_name = code_name + "C"
    
    code_name = code_name + request_json["strikeprice"] + "000"
    print("code_name= " + code_name)
    """

    #str_date = datetmp[:4] + "-" + datetmp[4:6] + "-" + datetmp[6:]

    quote_ctx = OpenQuoteContext(host='34.127.53.74', port=11111)
    """
    ret, data = quote_ctx.get_stock_basicinfo(Market.HK, SecurityType.STOCK)
    if ret == RET_OK:
        print(data)
    else:
        print('error:', data)
    print('******************************************')
    """

    """
    ret, data = quote_ctx.get_market_state(['SZ.000001', 'HK.00700'])
    if ret == RET_OK:
        print(data)
    else:
        print('error:', data)
    quote_ctx.close() # After using the connection, remember to close it to prevent the number of connections from running out

    """
    #code_name = "US." + request_json['symbol']
    code_name = "US.SPY"
    
    ret1, data1 = quote_ctx.get_option_expiration_date(code=code_name)

    filter1 = OptionDataFilter()
    filter1.delta_min = 0
    filter1.delta_max = 0.1

    json_row = None
    if ret1 == RET_OK:
        expiration_date_list = data1['strike_time'].values.tolist()
        print(expiration_date_list)
        for date in expiration_date_list:
            ret2, data2 = quote_ctx.get_option_chain(code=code_name, start=date, end=date, data_filter=filter1)
            if ret2 == RET_OK:
                result_str = result_str + str(data2)
                print(data2)
                print(data2['code'][0])  # Take the first stock code
                print(data2['code'].values.tolist())  # Convert to list
                json_row = get_row_by_code(data2, "US.SPY240626C620000")
                if json_row != None:
                    break
            else:
                print('error:', data2)
            time.sleep(3)
    else:
        print('error:', data1)

    print("Row found: ", json_row)
    
    quote_ctx.close()
        
    return result_str