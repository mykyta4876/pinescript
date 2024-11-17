import pandas as pd
import csv
import coral
from binance import Client
import time
import logging

# Initialize logging
logging.basicConfig(filename='errors.log', level=logging.ERROR)

# Binance API connection
api_key = 'YnKn2krHuEn7hIWjgHNIZ74pqJDSUxhoZoIXQ3duGJlwctmocTRN693kLiXE0l0E'
api_secret = 'OzoThLm5yY5J31rGCsAUG9mAIVAf8ehvRYkHYJRZKDMLbasOxx0sJdc4FJRTvWfN'
client = Client(api_key,api_secret)


# Fetch top 10 coins based on percentage gain
def get_symbol():
    tickers = client.get_ticker()
    usdt_gainers = sorted(
        [ticker for ticker in tickers if ticker['symbol'].endswith('USDT')],
        key=lambda x: float(x['priceChangePercent']),
        reverse=True
    )
    top_gainers = [gainer['symbol'] for gainer in usdt_gainers[:10]]
    return top_gainers

# set defaults for csv file
top_gainer=get_symbol()
posframe=pd.DataFrame(top_gainer)
posframe.columns=['Currency']
posframe['Position']= 0
posframe['Quantity']= 0
posframe.to_csv('position_check.csv',index=False)


# Write data to CSV
def write_to_csv(data):
    with open('position_check.csv', 'a', newline='') as file:
        writer = csv.writer(file)
        writer.writerow(data)
        print(f"Added {data[0]} to CSV file")

# Change position in CSV for buy/sell
def change_position(posframe, curr, order, sell=True):
    if sell:
        posframe.loc[posframe.Currency == curr, 'Position'] = 1
        posframe.loc[posframe.Currency == curr, 'Quantity'] = float(order['executedQty'])
        posframe.to_csv('position_check.csv', index=False)
    else:
        posframe.loc[posframe.Currency == curr, 'Position'] = 0
        posframe.loc[posframe.Currency == curr, 'Quantity'] = 0
        posframe.drop(posframe.loc[posframe.Currency == curr].index, inplace=True)
        posframe.to_csv('position_check.csv', index=False)
        #write_to_csv([curr, 0, 0])


def trader(posframe, investment=5):
    df2 = pd.read_csv('position_check.csv')

    # Ensure the filter returns a proper list or index for iteration
    coins_in_position = posframe[posframe.Position == 0].Currency.tolist()

    for coin in coins_in_position:
        df = coral.get_ohlc(coin, "15m", 200)
        status = coral.coral_trend_indicator(df, smoothing_period=21, constant_d=0.5)

        if status.upper() == 'SELL':
            order = client.create_order(symbol=coin, side='SELL', type='MARKET',
                                        quantity=posframe.loc[posframe.Currency == coin, 'Quantity'].values[0])
            change_position(posframe, coin, order, sell=True)
            print(f"Sold {coin}\n{order}")

    coins_not_in_position = posframe[posframe.Position == 0].Currency.tolist()

    for coin in coins_not_in_position:
        df = coral.get_ohlc(coin, "15m", 200)
        lenth_csv = df2[(df2['Currency'] == coin) & (df2['Position'] == 0)].shape[0]

        if df2['Position'].sum() >= 4:
            posframe = pd.DataFrame(get_symbol(), columns=['Currency'])
            posframe.to_csv('position_check.csv', index=False)

        status = coral.coral_trend_indicator(df, smoothing_period=21, constant_d=0.5)

        if status.upper() == 'BUY' and lenth_csv == 0:
            order = client.create_order(symbol=coin, side='BUY', type='MARKET', quoteOrderQty=investment)
            change_position(posframe, coin, order, sell=False)
            print(f"Bought {coin}\n{order}")
        else:
            print(f'Buying Condition for {coin} is not fulfilled')


# Run bot with error handling and pass posframe
while True:
    try:
        trader(posframe)  # Pass posframe explicitly to trader function
    except Exception as e:
        print(e)
        time.sleep(60)  # Delay before retrying
        continue
