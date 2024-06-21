import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

# Read the CSV file
data = pd.read_csv('BATS_QQQ, 5.csv')

def ta_change(series):
	return series.diff()

def ta_rma(series, length):
	alpha = 1 / length
	return series.ewm(alpha=alpha, adjust=False).mean()

def ta_ema(series, length):
	return series.ewm(span=length, adjust=False).mean()

def is_zero(val, eps):
	return abs(val) <= eps

def sum_with_check(fst, snd):
	EPS = 1e-10
	res = fst + snd
	if is_zero(res, EPS):
		return 0
	elif not is_zero(res, 1e-4):
		return res
	else:
		return 15

def ta_stdev(src, length):
	avg = src.rolling(window=length).mean()
	sum_of_square_deviations = np.zeros_like(src)
	
	for i in range(length - 1, len(src)):
		sum_of_square_deviations[i] = sum(sum_with_check(src[j], -avg[i]) ** 2 for j in range(i - length + 1, i + 1))
	
	stdev = np.sqrt(sum_of_square_deviations / length)
	return stdev

"""
def ta_stdev(series, length):
	return series.rolling(window=length).std()
"""

def ta_tr(data):
	return np.maximum(data['high'] - data['low'], np.maximum(abs(data['high'] - data['close'].shift()), abs(data['low'] - data['close'].shift())))

def dirmov(data, length):
	up = ta_change(data['high'])
	down = -ta_change(data['low'])
	plusDM = np.where((up > down) & (up > 0), up, 0)
	minusDM = np.where((down > up) & (down > 0), down, 0)
	truerange = ta_rma(ta_tr(data), length)
	plus = 100 * ta_rma(pd.Series(plusDM), length) / truerange
	minus = 100 * ta_rma(pd.Series(minusDM), length) / truerange
	return plus, minus, up, down, plusDM, minusDM, truerange

def adx(data, dilen, adxlen):
	plus, minus, up, down, plusDM, minusDM, truerange = dirmov(data, dilen)
	data['plus'] = plus
	data['minus'] = minus
	data['up'] = up
	data['down'] = down
	data['plusDM'] = plusDM
	data['minusDM'] = minusDM
	data['truerange'] = truerange

	sum_dm = plus + minus
	adx_val = 100 * ta_rma(abs(plus - minus) / np.where(sum_dm == 0, 1, sum_dm), adxlen)
	diff = plus - minus
	data['adx_val'] = adx_val

	return adx_val, diff

def adx_v8(data, adxlen, dev1, dev2):
	sig, diff = adx(data, adxlen, adxlen)
	diffema = ta_ema(diff, adxlen)
	std = ta_stdev(diff, adxlen)
	bbup1 = diffema + dev1 * std
	bblo1 = diffema - dev1 * std
	bbup2 = diffema + dev2 * std
	bblo2 = diffema - dev2 * std
	return sig, diff, diffema, std, bbup1, bblo1, bbup2, bblo2

def ADX_Simple_v3_adx_v8(data, adxlen, dev1, dev2):
	sig, diff, diffema, std, bbup1, bblo1, bbup2, bblo2 = adx_v8(data, adxlen, dev1, dev2)
	
	positive = sum([diffema > 0, bbup1 > 0, bblo1 > 0, bbup2 > 0, bblo2 > 0])
	negative = sum([diffema < 0, bbup1 < 0, bblo1 < 0, bbup2 < 0, bblo2 < 0])
	
	positive2 = sum([diff > diffema, diff > bbup1, diff > bblo1, diff > bbup2, diff > bblo2])
	negative2 = sum([diff < diffema, diff < bbup1, diff < bblo1, diff < bbup2, diff < bblo2])
	
	count = positive + positive2 - negative - negative2
	avg = ta_ema(pd.Series(count), adxlen)
	
	return count, avg

# Parameters
adxlen = 14
deviation1 = 1.0
deviation2 = 2.0

# Calculate the indicators
data['count'], data['avg'] = ADX_Simple_v3_adx_v8(data, adxlen, deviation1, deviation2)
print(data)

# Export the up_arrow, down_arrow, upArrow2, and dnArrow2 signals to CSV
output_df = data[['time', 'open', 'high', 'low', 'close', 'Volume', 'up', 'down', 'plusDM', 'minusDM', 'truerange', 'plus', 'minus', 'adx_val', 'count', 'avg']]

# Export the filtered DataFrame to a CSV file
output_df.to_csv('filtered_signals.csv', index=False)

# Plot the results
plt.figure(figsize=(14, 7))
# plt.hist(data['count'], bins=50, color='lime' if data['count'].iloc[-1] >= 0 else 'red', alpha=0.7)
# plt.hist(data['count'], bins=50, color='red', alpha=0.7)
plt.plot(data['count'], color='red', lw=1.5)
plt.plot(data['avg'], color='yellow', lw=1.5)
plt.title('Count and Count EMA')
plt.show()
