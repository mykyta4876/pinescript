import functions_framework
import pandas as pd
from io import StringIO
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import json

credentials_filename = "client_key.json"
sheet_name = "tradingview_alert"

def write_google_sheet(dataframe, credentials_filename, sheet_name, ticker):
	#Authorize the API
	scope = [
		'https://www.googleapis.com/auth/drive',
		'https://www.googleapis.com/auth/drive.file'
		]

	file_name = credentials_filename
	creds = ServiceAccountCredentials.from_json_keyfile_name(file_name,scope)
	client = gspread.authorize(creds)
	try:
		#Fetch the sheet
		sh = client.open(sheet_name)
		try:
			worksheet = sh.worksheet("zig-" + ticker)
		except:
			worksheet = sh.add_worksheet(title="zig-" + ticker, rows=100, cols=20)

		worksheet.update([dataframe.columns.values.tolist()] + dataframe.values.tolist())

		print("[-]  update Google Sheet successfully.")
	except gspread.exceptions.APIError:
		print("[-]  error: gspread.exceptions.APIError")

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
    
	content_type = request.content_type
	print(content_type)

    if content_type == 'text/plain; charset=utf-8':
        message = request_json['message']
		arr_line = message.split(";")
		if len(arr_line) == 0:
			return ""
		
		ticker = arr_line[0]
        content = "Type,time,price,macd\n" + arr_line[0]

        # Convert the CSV string to a file-like object
		data = StringIO(content)

		# Create DataFrame
		df = pd.read_csv(data)
		"""
		# Convert DataFrame to JSON string
		json_data = df.to_json(orient='records')
		json_object = json.loads(json_data)
		"""
		write_google_sheet(df, credentials_filename, sheet_name, ticker)

    return 'Hello {}!'.format(name)
