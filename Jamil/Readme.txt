I want a tradingview indicator where It looks at the last 22 days - (Not 22 periods - 22 days)

• If the local max occurs before the local min in that period, anchor an AVWAP to the local Min
• If the local max occurs after the local min in that period, anchor an AVWAP to the local Max

Please make the 22 days editable - such that I can do 50 days for instance

theres a built in AVWAP function

but if you cant use it - this is the calculation methodology:

Steps to Calculate AVWAP with HLC3

Calculate HLC3: Compute the average of the High, Low, and Close prices for each period (HLC3).
HLC3 = (High + Low +Close)/3

Select Anchor Date: Choose an anchor date from which you want to start the AVWAP calculation. This could be any significant date based on your analysis. (Max_1 & Min_1)

Calculate Cumulative Volume: Compute the cumulative sum of the volume from the anchor date to each day.

Calculate Cumulative Volume x HLC3: Compute the cumulative sum of the product of volume and HLC3 from the anchor date to each day

Calculate AVWAP: Divide the cumulative volume x HLC3 by the cumulative volume for each period to get the AVWAP.