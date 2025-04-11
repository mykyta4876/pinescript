from datetime import datetime, timedelta


code_name = 'US.RUTW250130C2310000'
#code_name = 'US.QQQ250203C538000'

str_day = code_name[-10:-8]
str_month = code_name[-12:-10]
str_year = code_name[-14:-12]
if code_name[-7] == 'C' or code_name[-7] == 'P':
    str_day = code_name[-9:-7]
    str_month = code_name[-11:-9]
    str_year = code_name[-13:-11]

date_str = f"20{str_year}-{str_month}-{str_day}"
date_obj = datetime.strptime(date_str, "%Y-%m-%d")
date_obj = date_obj + timedelta(days=1)
print(date_obj)

now_time = datetime.now()


if date_obj > now_time:
    print("same")
else:
    print("not same")