#https://openapi.moomoo.com/moomoo-api-doc/en/quote/get-option-chain.html
import functions_framework
import moomoo as ft

@functions_framework.http
def hello_http(request):
    """HTTP Cloud Function.
    Args:
        request (flask.Request): The request object.
        <https://flask.palletsprojects.com/en/1.1.x/api/#incoming-request-data>
    Returns:
        The response text, or any set of values that can be turned into a
        Response object using `make_response`
        <https://flask.palletsprojects.com/en/1.1.x/api/#flask.make_response>.
    """
    request_json = request.get_json(silent=True)
    request_args = request.args

    print("getData: start")
    RET_OK = 1
    quote_ctx = ft.OpenQuoteContext(host='127.0.0.1', port=11111)
    print("getData: OpenQuoteContext")
    ret, data, page_req_key = quote_ctx.request_history_kline('HK.00700', start='2019-09-11', end='2019-09-18', max_count=5) # 5 per page, request the first page
    if ret == RET_OK:
        print(data)
        print(data['code'][0]) # Take the first stock code
        print(data['close'].values.tolist()) # The closing price of the first page is converted to a list
    else:
        print('error:', data)
    while page_req_key != None: # Request all results after
        print('*************************************')
        ret, data, page_req_key = quote_ctx.request_history_kline('HK.00700', start='2019-09-11', end='2019-09-18', max_count=5,page_req_key=page_req_key) # Request the page after turning data
        if ret == RET_OK:
            print(data)
        else:
            print('error:', data)
    print('All pages are finished!')
    quote_ctx.close() # After using the connection, remember to close it to prevent the number of connections from running out

    return 'Hello {}!'.format(name)

