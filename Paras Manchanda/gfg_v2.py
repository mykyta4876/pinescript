import functions_framework
import pandas as pd
from io import StringIO
import gspread
import json
from oauth2client.service_account import ServiceAccountCredentials
import numpy as np
import os

credentials_filename = "valid-shuttle-430323-i9-cbcf106f3422.json"
sheet_name = "gfg-demo-sheet"
email = "pmdatareserve1@gmail.com"

def get_sheet_number():
	file_path = 'number.txt'

	number = "0"
	if os.path.exists(file_path):
		with open(file_path, 'r') as file:
			number = file.read()
	else:
		with open(file_path, 'w') as file:
			file.write(number)

	return number

def update_sheet_number(number):
	file_path = 'number.txt'

	with open(file_path, 'w') as file:
		file.write(number)

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

def update_google_sheet_base(credentials_filename, sheet_name, ticker, number):
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
		try:
			sh = client.open(ticker + "-" + sheet_name)
		except:
			sh = client.create(ticker + "-" + sheet_name)
			sh.share(email, perm_type='user', role='writer')

		df_mtf = None
		try:
			worksheet = sh.worksheet("mtf-" + number)
			df_mtf = pd.DataFrame(worksheet.get_all_records())
		except:
			pass

		df_macd = None
		try:
			worksheet = sh.worksheet("macd-" + number)
			df_macd = pd.DataFrame(worksheet.get_all_records())
		except:
			pass

		df_zig1 = None
		try:
			worksheet = sh.worksheet("zig1-" + number)
			df_zig1 = pd.DataFrame(worksheet.get_all_records())
		except:
			pass

		df_zig15 = None
		try:
			worksheet = sh.worksheet("zig15-" + number)
			df_zig15 = pd.DataFrame(worksheet.get_all_records())
		except:
			pass

		df_zig2 = None
		try:
			worksheet = sh.worksheet("zig2-" + number)
			df_zig2 = pd.DataFrame(worksheet.get_all_records())
		except:
			pass

		df_list = []
		df_list = add_df_and_spacer(df_mtf, df_macd, df_list)
		df_list = add_df_and_spacer(df_macd, df_zig1, df_list)
		df_list = add_df_and_spacer(df_zig1, df_zig15, df_list)
		df_list = add_df_and_spacer(df_zig15, df_zig2, df_list)

		if df_zig2 is not None:
			df_list.append(df_zig2)


		# Concatenate all the DataFrames and spacers if the list is not empty
		if df_list:
			df_concatenated = pd.concat(df_list, axis=1)
			# Replace NaN values with empty string
			df_concatenated.fillna('', inplace=True)
			#print(df_concatenated)
			try:
				sh_base = client.open(ticker + "-" + "DataLog")
			except:
				sh_base = client.create(ticker + "-" + "DataLog")
				sh.share(email, perm_type='user', role='writer')

			try:
				worksheet = sh_base.worksheet(ticker + "-" + number)
			except:
				worksheet = sh_base.add_worksheet(title=ticker + "-" + number, rows=100, cols=30)

			worksheet.clear()
			worksheet.update([df_concatenated.columns.values.tolist()] + df_concatenated.values.tolist())

		print("[-] update_google_sheet_base: update Google Sheet base successfully.")
	except gspread.exceptions.APIError as e:
		print("[-] update_google_sheet_base: error: gspread.exceptions.APIError " + str(e))

def update_google_sheet_mtf(dataframe, credentials_filename, sheet_name, ticker, number):
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
		try:
			sh = client.open(ticker + "-" + sheet_name)
		except:
			sh = client.create(ticker + "-" + sheet_name)
			sh.share(email, perm_type='user', role='writer')

		try:
			worksheet = sh.worksheet("mtf" + "-" + number)
		except:
			worksheet = sh.add_worksheet(title="mtf" + "-" + number, rows=100, cols=30)

		df1 = pd.DataFrame(worksheet.get_all_records())

		df_len = len(df1)
		if df_len == 0:
			df1 = dataframe
		else:
			if df_len > 10000:
				n = int(number)
				n = n + 1
				number = str(n)
				update_sheet_number(number)

				return 0
			# empty_row = pd.Series([np.nan]*len(dataframe.columns), index=dataframe.columns)
			# dataframe = dataframe._append(empty_row, ignore_index=True)

			df1 = df1._append(dataframe, ignore_index=True)

		worksheet.update([df1.columns.values.tolist()] + df1.values.tolist())

		return 1

		print("[-] update_google_sheet_mtf: update Google Sheet successfully.")
	except gspread.exceptions.APIError as e:
		print("[-] update_google_sheet_mtf:  error: gspread.exceptions.APIError " + str(e))

def update_google_sheet_mtf_dialy(dataframe, credentials_filename, ticker):
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
		try:
			sh = client.open(ticker + "-" + "DailyS")
		except:
			sh = client.create(ticker + "-" + "DailyS")
			sh.share(email, perm_type='user', role='writer')

		try:
			worksheet = sh.worksheet("mtf")
		except:
			worksheet = sh.add_worksheet(title="mtf", rows=100, cols=30)

		#print(dataframe)
		worksheet.clear()
		worksheet.update([dataframe.columns.values.tolist()] + dataframe.values.tolist())

		print("[-] update_google_sheet_mtf_dialy: update Google Sheet successfully.")
	except gspread.exceptions.APIError as e:
		print("[-] update_google_sheet_mtf_dialy: error: gspread.exceptions.APIError " + str(e))

def update_google_sheet(dataframe, credentials_filename, sheet_name, ticker, signal, number):
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
		try:
			sh = client.open(ticker + "-" + sheet_name)
		except:
			sh = client.create(ticker + "-" + sheet_name)
			sh.share(email, perm_type='user', role='writer')

		try:
			worksheet = sh.worksheet(signal + "-" + number)
		except:
			worksheet = sh.add_worksheet(title=signal + "-" + number, rows=100, cols=20)

		df1 = pd.DataFrame(worksheet.get_all_records())
		df_len = len(df1)

		if df_len == 0:
			df1 = dataframe
		else:
			if signal == "zig1":
				if dataframe['Type - 1 Min'].iloc[0] == df1['Type - 1 Min'].iloc[df_len - 1]:
					df1 = df1.iloc[:-1]
			elif signal == "zig15":
				if dataframe['Type - 15 Min'].iloc[0] == df1['Type - 15 Min'].iloc[df_len - 1]:
					df1 = df1.iloc[:-1]
			elif signal == "zig2":
				if dataframe['Type - 2 Hour'].iloc[0] == df1['Type - 2 Hour'].iloc[df_len - 1]:
					df1 = df1.iloc[:-1]
			elif signal == "macd":
				if dataframe['Type'].iloc[0] == df1['Type'].iloc[df_len - 1]:
					df1 = df1.iloc[:-1]

			df1 = df1._append(dataframe, ignore_index=True)
		worksheet.update([df1.columns.values.tolist()] + df1.values.tolist())

		print("[-] update_google_sheet: update Google Sheet successfully.")
	except gspread.exceptions.APIError:
		print("[-] update_google_sheet: error: gspread.exceptions.APIError")

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
	#print(content_type)
	#print(request_json)

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

		number = get_sheet_number()

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
			output_df = df[['time', 'Interval', 'SELL OB-3 Number', 'SELL OB-3 Price', 'SELL OB-2 Number', 'SELL OB-2 Price', 'SELL OB-1 Number', 'SELL OB-1 Price', 'BUY OB-1 Number', 'BUY OB-1 Price', 'BUY OB-2 Number', 'BUY OB-2 Price', 'BUY OB-3 Number', 'BUY OB-3 Price']]

			update_google_sheet_mtf_dialy(output_df, credentials_filename, ticker)
			if update_google_sheet_mtf(output_df, credentials_filename, sheet_name, ticker, number) == 0:
				update_google_sheet_mtf(output_df, credentials_filename, sheet_name, ticker, number)
			update_google_sheet_base(credentials_filename, sheet_name, ticker, number)
		elif signal == "zig1":
			content = "Type - 1 Min,time,price,macd,signal,ema21,ema100,ema200,vwap\n" + arr_line[1]

			# Convert the CSV string to a file-like object
			data = StringIO(content)

			# Create DataFrame
			df = pd.read_csv(data)
			update_google_sheet(df, credentials_filename, sheet_name, ticker, signal, number)
			update_google_sheet_base(credentials_filename, sheet_name, ticker, number)
		elif signal == "zig15":
			content = "Type - 15 Min,time,price,macd,signal,ema21,ema100,ema200,vwap\n" + arr_line[1]

			# Convert the CSV string to a file-like object
			data = StringIO(content)

			# Create DataFrame
			df = pd.read_csv(data)
			update_google_sheet(df, credentials_filename, sheet_name, ticker, signal, number)
			update_google_sheet_base(credentials_filename, sheet_name, ticker, number)
		elif signal == "zig2":
			content = "Type - 2 Hour,time,price,macd,signal,ema21,ema100,ema200,vwap\n" + arr_line[1]

			# Convert the CSV string to a file-like object
			data = StringIO(content)

			# Create DataFrame
			df = pd.read_csv(data)
			update_google_sheet(df, credentials_filename, sheet_name, ticker, signal, number)
			update_google_sheet_base(credentials_filename, sheet_name, ticker, number)
		elif signal == "macd":
			content = "Type,time,price,macd,signal\n" + arr_line[1]

			# Convert the CSV string to a file-like object
			data = StringIO(content)

			# Create DataFrame
			df = pd.read_csv(data)
			update_google_sheet(df, credentials_filename, sheet_name, ticker, signal, number)

	return ''
