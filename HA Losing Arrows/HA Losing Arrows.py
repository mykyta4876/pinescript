# Plotly Chart Demo - By TallTim
#
# What this does: Takes an input .csv file with a single column label row before the data and renders a
# scrollable/zoomable chart
#
# This is NOT set up to do realtime data, though it could be adapted if you are clever. (Basically you'd
# reload the .csv as it updates from another source, and redraw the chart, but its beyond scope of this example.)
#
# This IS a way to tinker around with making indicators or other things with chart data.
#
# This assumes you have a python environment where pandas and plotly are installed. To install them, please refer
# to these websites:
# Pandas -- https://pandas.pydata.org/docs/getting_started/install.html - 'pip install pandas' should work, but details are on
# the site for specific environments. Required dependencies are NumPy, python-dateutil and pytz.
# Plotly -- https://plotly.com/python/getting-started/ - 'pip install plotly==5.15.0' should work, but details are on the site.
#
# Feel free to modify/share, just give me some credit for the template, thanks!

# Importing modules/packages needed for our chart
import os
import pandas as pd
import math # This is useful for 'math.isclose' when comparing floating point numbers - you comment this out if you don't need it.
import plotly.graph_objects as go
from plotly.subplots import make_subplots

totalbuypositions = []
totalsellpositions = []
sum = []
nettedLongPosition = []
nettedShortPosition = []

nettedLongAvg = []
nettedShortAvg = []

buyProfitCut = []

nettedLongPosition.append(0.0)
nettedShortPosition.append(0.0)

nettedLongAvg.append(0.0)
nettedShortAvg.append(0.0)

buyProfitCut.append(0.0)

def EntrySignal(close, open, bar_index, XBarsDelay):
    upArrow = close[bar_index] > open[bar_index - XBarsDelay]
    downArrow = close[bar_index] < open[bar_index - XBarsDelay]

    return upArrow, downArrow

def CalculateBuyProfit(calc, nettedLongAvg, nettedLongPosition, close, sum, bar_index):
    if calc == True:
        sum0 = (close[bar_index] - nettedLongAvg[bar_index]) / TickSize * nettedLongPosition * TickValue
        totalbuypositions0 = nettedLongPosition[bar_index]
    else:
        sum0 = sum[bar_index - 1]
        totalbuypositions0 = totalbuypositions[bar_index - 1]

    return sum0, totalbuypositions0

def CalculateSellProfit(calc, nettedShortAvg, nettedShortPosition, close, sum, bar_index):
    if calc == True:
        sum0 = (nettedShortAvg[bar_index] - close[bar_index]) / TickSize * nettedShortPosition * TickValue
        totalsellpositions0 = nettedShortPosition[bar_index]
    else:
        sum0 = sum[bar_index - 1]
        totalsellpositions0 = totalsellpositions[bar_index - 1]

    return sum0, totalsellpositions0

def Running_4775_Dots_v2_Reset(tradingTime, XBarsDelay, multiplier, bar_index):
    upArrow, downArrow = EntrySignal(XBarsDelay)

    buy = upArrow and tradingTime
    sell = downArrow and tradingTime

    buyProfitCutoff = false
    sellProfitCutoff = false

    x = buy ? nettedLongPosition[bar_index - 1] + Lots : nettedLongPosition[bar_index - 1]
    nettedLongPosition.append(x)

    x = buy ? (nettedLongPosition[bar_index - 1] * nettedLongAvg[bar_index - 1] + Lots * close[bar_index]) / (nettedLongPosition[bar_index - 1] + Lots) : nettedLongAvg[bar_index - 1]
    nettedLongAvg.append(x)

    x = nettedLongPosition[bar_index - 1] == 0 and nettedLongPosition[bar_index] > 0 ? close[bar_index] * multiplier : nettedLongPosition[bar_index] == 0 ? 0 : buyProfitCut[bar_index - 1]
    buyProfitCut.append(x)

    nettedShortPosition := sell ? nz(nettedShortPosition[1], 0) + Lots : nz(nettedShortPosition[1], 0)
    nettedShortAvg := sell ? (nz(nettedShortPosition[1], 0) * nz(nettedShortAvg[1], 0) + Lots * close) / (nz(nettedShortPosition[1], 0) + Lots) : nz(nettedShortAvg[1], 0)

    sellProfitCut = 0.0
    sellProfitCut := nettedShortPosition[1] == 0 and nettedShortPosition > 0 ? close * multiplier : nettedShortPosition == 0 ? 0 : nz(sellProfitCut[1])



    calc = tradingTime
    [buyProfit, totalbuypositions] = CalculateBuyProfit(calc, nettedLongAvg, nettedLongPosition)
    [sellProfit, totalsellpositions] = CalculateSellProfit(calc, nettedShortAvg, nettedShortPosition)


    buyProfitCutoff := buyProfitCut > 0 and buyProfit >= buyProfitCut
    sellProfitCutoff := sellProfitCut > 0 and sellProfit >= sellProfitCut

    exitbuy = buyProfitCutoff
    exitsell = sellProfitCutoff


    nettedLongPosition := exitbuy or exitsell ? 0 : nettedLongPosition
    nettedLongAvg := exitbuy or exitsell ? 0 : nettedLongAvg

    nettedShortPosition := exitbuy or exitsell ? 0 : nettedShortPosition
    nettedShortAvg := exitbuy or exitsell ? 0 : nettedShortAvg

    [buyProfitCutoff, sellProfitCutoff]


# Read into pandas dataframe
df_Input = pd.read_csv("Sample Data Set.csv")

# For reference, my .csv looked something like this:
#
# BarTimestamp,FancyIndicator,Open,High,Low,Close
# 6/11/2023 7:30:00 AM,0.0208,25803.72,25804.04,25788.47,25797.74
#
# Because of how pandas dataframes work, it doesn't matter the order of the columns since you can select/assign them to
# variables by their column names

# Debug - This is a useful thing that tells you what your dataframe consists of, and other stats
#print(df_Input.info())

# Debug - This prints the dataframe contents - useful if you need to confirm things are being loaded correctly
#print("Dataframe Input File Contents:" + df_Input.to_string())

# Get number of dataframe rows and columns
dataDimensions = df_Input.shape
dataRows = dataDimensions[0]
dataCols = dataDimensions[1]

## Debug - Gives the dimensions of your dataframe
print("\nInput dataframe - Rows: " + str(dataRows) + " Columns: " + str(dataCols))

# Here is where we define our plots - the top section takes up 70% of the display, the indicator uses the remainder
fig = make_subplots(rows=2, row_heights=[0.70,0.30], cols=1, shared_xaxes=True, vertical_spacing=0.02) # Heights must add up to 1

# Plotly Candlestick Chart - you could substitute here for other types...
# Line Charts -- https://plotly.com/python/line-charts/ and there are more...
fig.add_trace(
				go.Candlestick(
				x=df_Input['time'], # X-axis has our date/times
				open=df_Input['open'],
				high=df_Input['high'],
				low=df_Input['low'],
				close=df_Input['close'],
				name="Price"), # Name on legend
				row=1, col=1 # Top section, so first row/col
)

# Add Fancy Indicator subplot with go.Scatter
fig.add_trace(go.Scatter(x=df_Input['time'], y=df_Input['open'], name="Fancy Indicator", line=dict(color='rgb(235,140,52)')), row=2, col=1) # Dark orange

# Example of vertical line on a chart
fig.add_vline(x=54, line=dict(color='rgb(52,183,235)', width=2, dash='dot')) # Light blue

# Note: The fig.update_layout statements could be consolidated, but its just easier to read what each one does this way...

# Remove rangeslider
fig.update_layout(xaxis_rangeslider_visible=False)

# Background color - Note, this is the plot background, not the 'Paper' or chart background
fig.update_layout(plot_bgcolor='rgb(0,0,0)')

# Axes line color -- Named color reference: (CSS colors) https://community.plotly.com/t/plotly-colours-list/11730/3
fig.update_xaxes(showline=True, linewidth=1, linecolor='dimgray') # You can use named colors or rgb like below
fig.update_yaxes(showline=True, linewidth=1, linecolor='dimgray')

# Tick value display format - yaxis<num> is for subplots
fig.update_layout(yaxis={"tickformat" : ','}, yaxis2={"tickformat" : '.2f'}) # Displays thousands,hundreds without scientific 'K' notation

# Grid line color
fig.update_xaxes(showgrid=True, gridwidth=1, gridcolor='dimgray')
fig.update_yaxes(showgrid=True, gridwidth=1, gridcolor='dimgray')

# Font color
fig.update_layout(font = dict(color='rgb(160,166,184)')) # Light Gray

# Chart title
fig.update_layout(title="HA Losing Arrows", title_x=0.5, yaxis_title="Price", yaxis2_title="Indicator")

# Legend Background Transparent Color, 'Paper' background color - plot canvas, sets pan enabled on load
# If you don't like pan enabled - just remove it
fig.update_layout(legend=dict(bgcolor='rgba(0,0,0,0)'), paper_bgcolor='rgb(12,12,12)', dragmode='pan')

# Mouse wheel zoom -- if you prefer not to have zoom enabled, then remove this line
config = dict({'scrollZoom' : True})

# Render Chart -- remove config = config if you removed the above line
fig.show(config = config)