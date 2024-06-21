https://chatgpt.com/g/g-KltZfpAIp-pine-to-python-converter?oai-dm=1&utm_source=gptshunter.com
https://chatgpt.com/share/91b57147-99ca-4bf8-bef2-10558ac99d4d

Basically next step will be pulling live data into python, generating signals using MD2R or MD1R (haven't decided yet) and then issuing alerts to trading server.

I will issue an alert to the server, and then instead of just passing it along, you will pull the chart data for that stock option, then keep a live processing of the data, generate the signals, and then send an alert to the trading server.

but we will have to keep 1 python live instance for each alert you receive, to generate the signals, and then send to trading server

all the trading server is working fine, just need to separate test environment from real environment

so it means you will NOT send this to the trading server.  you will first pull all the chart data for that stock option using API, and put it into python MD1R or MD2R, then generate live signals, then send buy or sell alerts to trading server based on down arrow or up arrow, (I will explain trading rules more later).   

JSON you send will be in same format as this one.  Only thing you will change is "SELL" or "BUY" based on python. 

First we will just test pulling data by API.  I will send you the documentation for pulling data from the server so you can start to understand.  Also will have to explain what these 4 fields in the alert: ("symbol":"QQQ","ExpiryLength":"1","date":"20240621","strikeprice":"483","option":"put" )

These 4 fields will be used to identify the right option to pull the data.


Yes.  But it will need to stay running because we will also have trading rules.  need to make one simple if then (BUY if MD1R up arrow and option price > price at time of alert, SELL if MD1R down arrow option price < price at time of alert).  it means python will have to stay running for all positions until you receive "EXIT" alert from me.  then can close python instance. 
Prateek Goel, Today at 4:07 PM
For example now it can be "BUY", but later in the day it can be "SELL" based on what price is doing

at most we will have 4 or 5 different symbols each trading independent.  at first we will just test 1 then we can know if it's good or not.  we can worry about multiple symbols later. 

first step we can say just to pull the correct chart data into python, 1 instance.  

I can send the documentation about pulling  chart data, but you may also need to talk with the backend programmer to understand the API interface

Also I will need secure way of putting settings into the python (all will use same setting).  But I don't want to share my settings with anyone, so needs to be secure way for me to do so.  for testing can use any setting.

probably will use 3 minute intervals, so you can fetch once on initial alert and then update each 3 minute close

timeframe is 3m

