from datetime import datetime
import pytz
import time

symbol_last_time = datetime.now().astimezone(pytz.timezone('US/Eastern'))
print(symbol_last_time)

time.sleep(10)

delta_time = datetime.now().astimezone(pytz.timezone('US/Eastern')) - symbol_last_time
print(delta_time)