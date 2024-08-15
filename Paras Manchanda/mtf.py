import functions_framework
import pandas as pd
from io import StringIO
import gspread
import json
from oauth2client.service_account import ServiceAccountCredentials

credentials_filename = "tvdata-429721-6dc1fa9e18a4.json"
sheet_name = "gfg-demo-sheet"

# Function to add DataFrame and empty spacer
def add_df_and_spacer(df, next_df, df_list):
	if df is not None:
		df_list.append(df)
		# Determine the length for the spacer based on current and next DataFrame
		if next_df is not None:
			length = max(len(df), len(next_df))
		else:
			length = len(df)
		# Add spacer DataFrame
		df_list.append(pd.DataFrame({'': [''] * length}))

	return df_list

def update_google_sheet_base(credentials_filename, sheet_name, ticker):
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
		df_mtf = None
		try:
			worksheet = sh.worksheet("mtf-" + ticker)
			df_mtf = pd.DataFrame(worksheet.get_all_records())
		except:
			pass

		df_macd = None
		try:
			worksheet = sh.worksheet("macd-" + ticker)
			df_macd = pd.DataFrame(worksheet.get_all_records())
		except:
			pass

		df_zig = None
		try:
			worksheet = sh.worksheet("zig-" + ticker)
			df_zig = pd.DataFrame(worksheet.get_all_records())
		except:
			pass

		df_list = []
		df_list = add_df_and_spacer(df_mtf, df_macd, df_list)
		df_list = add_df_and_spacer(df_macd, df_zig, df_list)

		if df_zig is not None:
			df_list.append(df_zig)


		# Concatenate all the DataFrames and spacers if the list is not empty
		if df_list:
			df_concatenated = pd.concat(df_list, axis=1)
			# Replace NaN values with empty string
			df_concatenated.fillna('', inplace=True)
			print(df_concatenated)

			sh_base = client.open("DataLog")
			try:
				worksheet = sh_base.worksheet(ticker)
			except:
				worksheet = sh_base.add_worksheet(title=ticker, rows=100, cols=30)
			worksheet.clear()
			worksheet.update([df_concatenated.columns.values.tolist()] + df_concatenated.values.tolist())

		print("[-]  update Google Sheet base successfully.")
	except gspread.exceptions.APIError:
		print("[-]  error: gspread.exceptions.APIError")

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
			worksheet = sh.worksheet("mtf-" + ticker)
		except:
			worksheet = sh.add_worksheet(title="mtf-" + ticker, rows=100, cols=30)

		print(dataframe)
		worksheet.clear()
		worksheet.update([dataframe.columns.values.tolist()] + dataframe.values.tolist())

		print("[-]  update Google Sheet successfully.")
	except gspread.exceptions.APIError:
		print("[-]  error: gspread.exceptions.APIError")

def update_google_sheet(dataframe, credentials_filename, sheet_name, ticker, signal):
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
		worksheet_name = signal + "-" + ticker
		try:
			worksheet = sh.worksheet(worksheet_name)
		except:
			worksheet = sh.add_worksheet(title=worksheet_name, rows=100, cols=20)

		df1 = pd.DataFrame(worksheet.get_all_records())

		if len(df1) == 0:
			df1 = dataframe
		else:
			df1 = df1._append(dataframe, ignore_index=True)
		worksheet.update([df1.columns.values.tolist()] + df1.values.tolist())

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
	request_json = request.get_json(silent=True)
	request_args = request.args
	content_type = request.content_type
	print(content_type)
	print(request_json)

	if content_type == 'text/plain; charset=utf-8':
		message = request.data.decode('utf-8')  # decode from bytes to string
		arr_line = message.split(";")
		if len(arr_line) == 0:
			return ""
		
		header = arr_line[0]
		arr_node = header.split("^")
		signal = arr_node[0]
		ticker = arr_node[1]
		now_time = arr_node[2]

		if ticker.find("=") == 0:
			ticker = ticker[1:]
			json_object = json.loads(ticker)
			ticker = json_object['symbol']

		content = ""
		if signal == "mtf":
			content = arr_line[1]
			content = content.replace("-,", "0,")
			content = content.replace(",#", "#")
			content = content.replace("#", "\n")
			content = "Interval,SELL OB-3 Number,SELL OB-3 Price,SELL OB-2 Number,SELL OB-2 Price,SELL OB-1 Number,SELL OB-1 Price,BUY OB-1 Number,BUY OB-1 Price,BUY OB-2 Number,BUY OB-2 Price,BUY OB-3 Number,BUY OB-3 Price\n" + content

			# Convert the CSV string to a file-like object
			data = StringIO(content)

			# Create DataFrame
			df = pd.read_csv(data)
			df['time'] = now_time
			"""
			# Convert DataFrame to JSON string
			json_data = df.to_json(orient='records')
			json_object = json.loads(json_data)
			"""
			write_google_sheet(df, credentials_filename, sheet_name, ticker)
			update_google_sheet_base(credentials_filename, sheet_name, ticker)
		elif signal == "zig":
			content = "Type,time,price,macd\n" + arr_line[1]

			# Convert the CSV string to a file-like object
			data = StringIO(content)

			# Create DataFrame
			df = pd.read_csv(data)
			update_google_sheet(df, credentials_filename, sheet_name, ticker, signal)
			update_google_sheet_base(credentials_filename, sheet_name, ticker)
		elif signal == "macd":
			content = "Type,time,price\n" + arr_line[1]

			# Convert the CSV string to a file-like object
			data = StringIO(content)

			# Create DataFrame
			df = pd.read_csv(data)
			update_google_sheet(df, credentials_filename, sheet_name, ticker, signal)
			update_google_sheet_base(credentials_filename, sheet_name, ticker)


	return ''
