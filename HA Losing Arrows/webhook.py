import functions_framework
import json
import requests
from datetime import datetime
import pytz

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
    url = "https://alerts.badabrook.com/"
    response = "Nothing"

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

        # Send the POST request with the JSON data
        response = requests.post(url, data=json_data, headers={'Content-Type': 'application/json'})

        # Print the response from the server
        print("json_data= " + json_data)
        print("alerts.badabrook.com response= " + str(response.status_code))
        
    return ""
