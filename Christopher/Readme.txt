I want the range table to look like the color coded version I sent.

The original script allows input of a ticker, but does not display the asset name of the ticker like the color coded version does, so if you don't know what the ticker represents, you have no idea what the asset is. That needs to be changed.

The original script is inputting 10 tickers. I want to be able to customize it to 5-15 tickers.

I want to keep the Keltner channel and zscore parameters for the trading range itself. I want to keep the "top of the range" and "bottom of the range".

I want to keep the Z-Score in the table along with the parameters. I want to add two additional metrics to the table.

1) TACVOL Score - This is a custom indicator. You pay for it if you create it and add it as a standalone indicator to Table Plus.

Average 4h frame z-score and 1d time frame z-score.

For example 4h z-score is 2, 1d is 1 and tacvol score is 1.5. I want to customize the parameters.

It's just adding the 4 hour timeframe zscore to the 1d timeframe zscore and divide by 2

2) %up/%down - this is risk compensation. It just tells you how far the ticker price is from the highest and lowest range.

As for momentum. Use dmi +/- plus ADX.

So we will color the trading range like this:

DMI + adx 20-24.99 - light green

DMI + adx 25+ - dark green

DMI - adx 20-24.99 - light red

DMI - adx 25+ - dark red

DMI +/- adx 19.99 and below - gray

The script also has a little table with volume etc., which I don't want.