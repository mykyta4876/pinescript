import datetime
import pytz

# Get the current time in UTC
utc_now = datetime.datetime.now(pytz.utc)

# Convert UTC time to EST
est_timezone = pytz.timezone('America/New_York')
est_now = utc_now.astimezone(est_timezone)

# Get the hour part of the time
hour = est_now.hour

print("Current hour in EST:", hour)