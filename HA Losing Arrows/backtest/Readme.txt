So we going to need to build a python engine that compiles options historical data from a paid website.
The website is this one:
https://polygon.io/docs/options/getting-started
We are going to use the "Aggregates" endpoint

Basically first step is to pull 1 minute aggregate data for any user-defined symbol, for 1 user-defined strike price and expiration date, for whole period.  

So I will give an input spreadsheet with these parameters:
Symbol, type, Strikeprice, expiration date and period to run.
Symbol will be given in spreadsheet title as first part of title
Type (calls or puts) will be given as "C" or "P" in spreadsheet title directly after symbol
Strikeprice will be given in "strike" column of spreadsheet
Expiration date will be given in "expiry" column of spreadsheet (column D)
Period to run will be "start" column to "expiry" column (column A and column D).

And here is example of query to run in polygon for line 1 of this spreadsheet:

https://api.polygon.io/v2/aggs/ticker/O:SPY220107C00477000/range/1/minute/2022-01-03/2022-01-07?adjusted=true&sort=asc&apiKey=_gClIMBNzOb6jgnPTg4_xvQ08RSnKELi
https://api.polygon.io/v2/aggs/ticker/O:Book1221114C00397000/range/1/minute/2022-11-14/2022-11-14?adjusted=true&sort=asc&apiKey=_gClIMBNzOb6jgnPTg4_xvQ08RSnKELi
Note this is output only for line 1 of input spreadhseet.
As you can see, the query generates all 1 minute bars for SPY contract, 220107 expiry, Calls, 477 strike price from start column (column A) to expiry column (column d).  
(Note: my polygon API key is there so you can pull data by API) 

Output will be spreadsheet that compile all query results for each line in spreadsheet. 

Note: Each line of input spreadsheet will generate many lines of output spreadsheet.  So, the only columns that should be saved from input spreadsheet to output spreadsheet is "strikeprice" and "expiry" columns (column C and D). 

For example if Line 1 of input spreadsheet generate 200 lines of output, then each 200 line of output include the strike and expiry of Line 1 input. 

I will run this python engine on my desktop using CMD.

This is first milestone of this one, but we will build whole backtesting engine from this data we pulling now.  (It's very similar to when you pull historical data from Moomoo for first step of MD2R, but now we pulling this data from polygon and drop it into spreadsheet as first step.)

I will run the python from my desktop using CMD prompt.  so for example I enter this into CMD for folder c:\engine

python engine.py "SPY C weekly.xlsx"  

and XLSX file in engine folder.   And output also save to engine folder.

The "engine" folder is beside "engine.py" file.
The input and output files are in "engine" folder.

Or the "engine" folder is static folder like "C:\engine".


Also to calculate the Weekly VWAP also called "vww" (new column b to add in between current output column a and column b):

1) Calculate the typical price: For each line of spreadsheet, add the high, low, and close price, then divide by three.
2) Multiply the typical price by the volume:  For each line in spreadsheet, multiply the typical price by the volume for that line.
3) Create a running total: Add the price x volume values from each line of spreadsheet to get a cumulative total.
4) Create a running total of volume:  Add the volumes from each line of spreadsheet to get a cumulative volume.
5) Divide the running totals: Divide the cumulative price x volume total by the cumulative volume total to get the "vww" value.
6) start vww calculate fresh for each line of input.

Some small little changes I would like:
1) is it possible to convert timestamp to East Coast time?  (New York time)  Right now it's UTC
2) "vww" column not supposed to overwrite "vw" column.  Should have own column next to vw column.  If can't put in between "start" and "vw" column, put "vww" column after "expiry" column.
3) If input name "SPY C weekly" then output should be "SPY_C_weekly_output"

==================================
on building the trading engine from the output data... 

1) you will make 6 new columns of output sheet:
Long Equity
Long Balance
Long Running Balance
Short Equity
Short Balance
Short Running Balance  

Entries will be long and short (means buy and sell).  Must keep long/buy position calculations separate from short/sell position calculations because sometimes can have both buy and sell positions open at same time.

2) Each line of input sheet will have own calculations based on entries and exits using output lines for that 1 input line.  Reset equity and balance to 0 when processing each new line of input.

3) Entry rules are as follows:
Buy:  any "bull bar" with close price > vww (bull bar means any bar with Close > Open)
Sell:  any "bear bar" with close price < vww (bear bar means any bar with Close < Open)

4) Exit rules as follows (2 different exit):
a) Exit1:
Keep track of bull bar OPEN price for long entry.  For example, vww = 2.0 and Bull Bar Open = 1.95 and Close = 2.05, means Long Entry because Bull bar with Close price > vww.  Open price of long entry = 1.95.
Exit1 rule = exit long any time close price < 1.95 (open price of long position).
Also same idea for Exit1 short exit. Keep track of short entry open price and exit if any bar close price > open price of short entry. 

b) Exit2:
If no any Exit1, then Exit2 = last bar close price of output sheet for that expiration (means last output line close price before processing next line on input sheet).   

Note: 
a) Equity calculation for long (buying) is Exit1 or Exit2 close price minus entry close price.
b) After any time Exit1 means can still enter position again if new entry condition met.     
c) Equity calculation for short (selling) is entry close price minus Exit1 or Exit2 close price.  

5) Each Exit will affect the balance--means shift "equity" to "balance" on exit.  
For example after Exit1 Long Equity = -1.5, so means exit will shift Long Equity to Long Balance now -1.5.  Now equity 0 again.  

6)  Keep "Balance" column and "Running Balance" column separate.  "Balance" column will keep balance for each line of input processed and reset with new line processing.  "Running Balance" will be total of all final balance for each input line processed (means shift "Balance" to "Running Balance" on last output line for each input line processed).       

Right now I explain for just 1 position maximum open each side (1 position max buying if buy condition met and 1 position max selling if sell condition met), then we can discuss handling multiple positions later (netting equity for multiple positions and how to handle Exit1 for multiple positions).

Sorry I was not clear, equity will change each new line of output sheet depending if any long or sell position open.  

Equity calculation update each line of sheet if any position open:
Long equity: Output line close price - Long position entry close price
Short Equity:  Short position entry close price - Output line close price.      

And then equity shifted to balance for any exit and equity zeroed.

======================================
now we only need to add calculation for multi position in engine2....

When we run the "c:\engine: py engine.py" I will include now a number after the "engine.py", for example 1 or 10 and it means it the equity calculation engine that it can take maximum position each direction (long and short).  So for example I will make it run command in CMD:

"c:\engine: py engine.py 10 "SPY C weekly.xlsx"

means can enter max 10 positions long, 1 long entry each time long entry condition met upto max positions.
also means can enter max 10 positions short too.

To modify the long equity calculation for multi position, then you must do 2 things:

1) you need to net the entry price for the positions. So if 1 entry at 1.80 and 1 entry at 1.82, means 2 entry at 1.81.
2) Exit1 will exit for multi-position same time as 1 position exit....it means only Exit1 ALL open long positions if close price < open price of first open long position.

========================================
1) after the 10 (meaning max positions each side long and short),  I want to add a for example 10m or 5m means we will do 5 minute bar aggregate or 10 minute bar aggregate.  
2) I also want to add "vw" or "vww", if "vww" then runs as current, but if "vw" then it means it runs using entry rules based on "vw" column not "vww" column (but same rule:  long if bull bar close > vw and short if bear bar close < vw).  
3) "y" or "n", if y, then means use Exit1, and if "n" then means disable Exit1 (Exit2 only).

python engine2.py 10 10m vw n "SPY C weekly.xlsx"
python engine2_long.py 10 10m vw n "SPY C weekly.xlsx"
python engine2_short.py 10 10m vw n "SPY C weekly.xlsx"
========================================

Here is next main milestone:

1) Fix the IP address in the backend, update ryanoakes and enlixir account.  

2) We will do one change to the current project.  So "engine.py" will change function to only pulling bars using polygon API, for example "SPY C weekly.xlsx".   Note: this engine will not do ANY long or short position processing.  
So this engine.py will have command like this "py engine.py 10m 'SPY C Weekly.xlsx'"  Only setting will be bar size.  Output sheet name for this example will be:  "SPY_C_Weekly_10m_output.xlsx".  Note it will include the bar size specified in the setting like "10m" or "1m".

3) Input sheet will change slightly.  I will add a new column next to "start" column which will be "end" column.  "start" and "end" will define the time range to pull for each input line on spreadsheet, but "expiry" column will still be used for finding the correct expiry date, meaning the correct option name to pull correct data from.  Up until now all engines had "end" range = "expiry" range.  Now we break these into separate things:  "end" column separate from "expiry" column.  I attach an example of the new spreadsheet.

4) After pulling the data and save as output sheet, I will now use separate CMD prompt command "py engine2.py" or "py engine2_long.py" or "py engine2_short.py" and THESE engine will do the trade processing of the "...output.xlsx" sheet.  (py engine2.py will be both long and short process together.)   Separate the data pulling and the trade processing into separate engines is better because I don't need to pull all the data each time before testing new trade setting, just pull data once and test more settings easy.  

5) The command syntax for the engine2 trade processing will be like this: 
py engine2_long.py 10 vw n "SPY_C_Weekly_10m_output.xlsx"  
It's same as before but we remove the time setting like "10m" because it's now already include in the initial output sheet processing.  You can also see it match the name of your output sheet.
 
This above should all be done by end of Monday.  That is 1 milestone.

Then Tuesday we need to test a new strategy component on the paper trade as 2nd milestone.  Main addition will be to include a stop loss parameter in the alert.  I will include a stop loss based on percentage of entry price.  For example say we enter a short position filled at $1.50 per share and stop loss parameter in alert is like "20%".  It means if price of the option sold rise to $1.80 at any minute close (0.30 is 20% of 1.50 so 1.50 + 0.30 is stop loss = 1.80), then it means to close that position.  So you will need to keep in memory entry price of the position and need to make an exit order in the backend if price close any minute > stop loss.  This needs to be done Wednesday latest and ready to test on paper by Thursday morning latest.  

python engine_only_data.py 10m "SPY C weekly.xlsx"
python engine2.py 10 vw n "SPY_C_Weekly_10m_output.xlsx"
python engine2.py 10 vw y "SPY_C_Weekly_10m_output.xlsx"
python engine2_long.py 10 vw n "SPY_C_Weekly_10m_output.xlsx"
python engine2_short.py 10 vw n "SPY_C_Weekly_10m_output.xlsx"

========================================
Build engine3.py, same as engine2.py, except:
Remove Exit 1,
Keep Exit 2,
Add Exit 3:
Exit 3 means we will add a stop loss parameter in percentage.  For example "20%", meaning
if after any long entry, any closing price < entry price * (0.8), then exit that position (not all long position, just that long position).
if after any short entry, any closing price > entry price *1.2, then exit that position (not all short position, just that short position).
Note: we use 0.8 in this example because it means 1 - 0.2 (20% parameter) = .8
Note: we use 1.2 in this example because it means 1 + 0.2 (20% parametet) - 1.2

Syntax will be similar to engine2:
python engine3.py 10 vw y 0.2 "SPY_C_Weekly_10m_output.xlsx"

use average entry price
and if close price exceeds average entry price +/- stop loss, then exit all.
========================================
Next milestone should be easy one:

Part A, make the engine4.py, same as engine3.py, except:
1) Add option for reverse entry:  It means 
long entry if close price < vw/vww (depend on the setting).  
short entry if close price > vw/vww (depend on the setting).

2) Add option to reverse the exit.  It means for example if percent setting 0.5:
after any long entry, any closing price > average entry price * 1.5, then exit all long position.
after any short entry, any closing price < average entry price * 0.5, then exit all short position.

3) Syntax will be similar to engine3.py
py engine4.py 10 r vw y 0.2 r "[data only output file]"
Note:  "r" after 10 means reverse the entry.
Note: "r" after the 0.2  mean reverse the exit.  
If no r, then no reverse.  (or must make it "nr"?) 

4) Please make the engine4_short.py and engine4_long.py also.  

Budget is 2 hours, $60. $50 plus $10 bonus if can finish by tomorrow morning.

instead of output file have "_result" at end, can you add the settings "_10rvw0.2r" for example? 

python engine4.py 10 r vw y 0.2 r "SPY_C_weekly_10m_output.xlsx"
python engine4_long.py 10 r vw y 0.2 r "SPY_C_weekly_10m_output.xlsx"
python engine4_short.py 10 r vw y 0.2 r "SPY_C_weekly_10m_output.xlsx"
python engine4_short.py 10 r vw y 0.1 r "QQQ_P_daily+1_3m_output.xlsx"

========================================
[engine5]
Once I confirm that the backend is working properly again, then we can make some type of hourly arrangement to compensate you for any ongoing support to backend.  I don't add compensation right now because:
1) I already paid you in earlier milestone to fix backend after google update
2) some issues with backend caused by your mix up, which backend version we used.
Once it get working 100% again, we can talk s=about bonus

Also we still need too test the engine3 paper version on the moomoo.  We didn't do it as of yet, that's the only reason I didn't complete the milestone.


I also need to make one rule change to the Engine3.py, to build as Engine5.py.

Engine5 same as Engine3, EXCEPT:
If any Exit3 happen during that day, then no more entries that day (block any new entry that day).

All else same. 

If you can add that rule and send the Engine5.py, then I can add $50 bonus to the current milestone when complete.
========================================
[engine6]

if you have extra time and want to add next milestone while we wait for the engine4 to execute, here is next milestone (will add additional $50 payment for this milestone, also will give $200 of the $1000 bonus now), means:
$300 original engine4 milestone execution on backend
$50 bonus engine5 creation
$50 bonus this engine6 creation
$200 of $1000 bonus for engine4 upon successful engine4 execution.
----
$600 upon single order successful execution engine4 (and $800 more when ordertag0 and engine4 successful 1 full week).   

Next milestone:
Build engine6.py same as engine4.py except:

1) Add exact same rule as engine5 to engine6, if any Exit3, no more new entries that day.
2) Add 2 new rule options:  
If any Long Exit3, also exit any open short positions.
If any Short Exit3, also exit any open long positions.
3) Syntax for Engine6 will be same as Engine4 but have 2 new "y or n" (yes or no) options at the end after minimum price for turning on/off the 2 new rule options above.

For example:

engine6.py 10 r vw y 0.2 r 5 y y "TSLA_C_daily_1m_output.xlsx"

Please note:
1) Input file will still be your same output files from "engine_data_only.py".
2) Since we have option rules like long exit3 affecting short side positions, therefore do not build "engine6_long.py", "engine6_short.py", only full engine6.py needed.    
3) Output file name should be similar to Engine4.  Include the settings at the end of the name.  For example:
  "TSLA_C_daily_1m_output_10rvwy0.2r5yy.xlsx"

y and y = longexit3, exit short.  shortexit3, exit long--no new trades that day long or short.
n and n = longexit3, no short exit, shortexit3, no long exit--no new trades that day long or short.
n and y = longexit3, no exit short.  shortexit3, exit long--no new trades that day long or short.
y and n = longexit3, exit short, shortexit3, no long exit--no new trades that day long or short.  
=======================================
[engine7]
Exact same as "engine_only_data.py", first thing engine7.py is going to read each line of the input spreadsheet and it's going to pull all the aggregate bar data from "start" to "end" using the expiry and strike price given and the time frame given in the syntax (for example "1m" means pull each minute).  

Please note one important new step:
In each sheet there will be multiple times each day that the same strike price and expiry is being called (same strike and expiry means same option.  For example, Line 1 of input sheet may say "10:20am strikeprice 420 expiry 1/15/25" and then Line 4 "10:27am" with same strikeprice and expiry.  Since Line 1 will already pull all data each minute from start time to end time, then you don't need to pull the aggregate bar data again on the second input sheet line since it's already included in the first line data.  So it's only needed for the first time each day that each unique strike price and expiry is called.

The input syntax will only include the minute timeframe like engine_only_data.py.  So for example:  
python engine7.py 1m C 2 "[input sheet name with symbol name first.xlsx]"
python engine7.py 1m C 2 "SPY C daily1.xlsx"
python engine_only_data.py 1m 'SPY C daily1.xlsx'
python engine7.py 1m C 2 "QQQ C 10m white daily test.xlsx"

Then there will an additional processing that goes on after all the data is pulled.  

entry_price: open price of the option at start time. then note it in "Entry_Price" Column.
exit_price: 
  when close price exceeds multiplier * entry_price, then note the close price in "Exit_Price" Column and time stamp in "Exit_Time" Column.  
  when not hit multiplier, then note open price of end time in "Exit_Price" Column and time stamp in "Exit_Time" Column.

output sheet name should be input sheet name with 3 parameters added "1mC2_e7" at the end.

Add the "End Time" column in.  I need it to check all multiplier hit and not hit < or = end time.
=========================================
[engine8]
upgrade will be to build engine8, same as engine7, except:

1) now we modify it, "Exit price" will always be open price of end time.
2) now we add a new column "Oscillations", in order to calculate oscillations we do the following.
We count the total number of times between start time and end time that price went from open price at to > multiplier x open price, back to open price (any bar close price again < or = to open price at start time), and again back to price > multiplier  x open price--*however many times it go back and forth between open price and exceeding the multiplier price between start time and end time* then add one to oscillations count for that item.

For example open price = 15, and multiplier = 2, then for each time it go from open price to > 30, add 1 to oscillation column for that row, and if it go back down to open price, then add another 1, and keep going like this until end time for each input sheet line until end time and then note the down the open price at end time.

Note: each input line have own total oscillations, don't add them together from one line to next! 
Note:  I don't need any other change to engine7, just build this one engine8.

python engine8.py 1m C 2 "RUTW 3m purple calls.xlsx"

===========================================
[engine9]
# Modify engine7.  please add one column which will be final close price of the day for each input item on the sheet. Set it as engin9
python engine9.py 1m C 2 "AAPL P test.xlsx"

The exceptions:
1) No data found from polygon: Open price = 0, Exit price = 0, Final Close Price = 0
2) No data found for this start time: Open price = 0, Exit price = 0
3) No data found for this period (start time to end time): Open price = 0, Exit price = 0

Updates:
1) We always use the open price of the Exit Timestamp when the exit happens without hitting multiplier exit.
2) We always use close price anytime the multiplier exit gets exceeded.  
3) We always use close price for the "Final closing price" column.

===========================================
[engine10]
# Build engine10, same as engine7 except:
Now we going to check when any close price < open price * multiplier (will use fraction multipliers less than 1, like 0.5) then note down the close price and the time stamp, same as engine7.  only change is from > to <.  all else same.  

I said engine8 already doing this, but from coding viewpoint maybe not the same exact idea.  because maybe 8 is still reading the end time and then just dumping the close price at end time in that column.  engine7 new column not based on endtime.  just last close price of the each input line item.  (endtime may or may not be last close price.) 


over the weekend we will need to do update of backend.  we can use elixir real and paper if you need to update openD as well....  

1) Now memory will keep track of entry price of the sell position for all ordertag0.
2) Each minute backend will check moomoo close price for each sell position, check if minute close price > 2 * sell position price.
3) if minute close price > 2 * sell position price, then exit position

actually we should write the backend code as "check at the open of each minute" because then it means it will also check right at 9:30. 

python engine10.py 1m C 2 "QQQ C 10m white daily test.xlsx"

Updated engine7: when not hit multiplier, then note open price of end time in "Exit_Price" Column and time stamp in "Exit_Time" Column. (30 mins)
engine8: correct the exit price calculation.
engine9: correct the exit price calculation.
engine10: correct the exit price calculation.

Updated all engines: add the "End_Time" column. (1 hour)

=============================================
[engine11]
because I have another test project that may make everything much simpler, but I would need to do some research first.

First you would have to build Engine11, same as engine9, EXCEPT now we going to check a different thing:
1) after the open price, check if any line the HIGH PRICE > 2 x open price (this is different than engine9, checking CLOSE PRICE > 2 x open price).  
2) IF high price > 2 x open price, then 
exit price = 2 x open price and 
exit time = timestamp same line as high price > 2 x open price.
       
If results of engine11 same or better than engine9, then we just make a stoploss order 2*entry price and enter it same time as sell position entry--then no checking needed.

=============================================
[engine12]
Let's say for example Phase Index setting = 0.05 (means 5%), then from open price at start time, if option price any close price increase or decrease by at least 0.05 then phase index will change up +1 or down -1.  then from that close price if any change 0.05 up or down then phase index will again chance +1 if up or -1 if down.  
For example option price at start time = 10.  (Phase Index setting = 0.05 and Phase Index initial value always = 0)
The later some close price 10.60,  Now phase Index value = +1 because price close > 10 + (10 * 0.05)
Now price drop to 10.05, Now Phase Index value = -1 because price drop from 10.60 more than 5%.  
So we just add this = +1 and -1 values to the engine data only.  
Only additional point is that at end of day Phase Index reset to 0.  Means each row of Input sheet start with Phase Index = 0 and calculate from first bar open price.

also you can keep engine_only_data.py the same but make a new version.  engine12.py with the phase index value.


=============================================
[engine12_v1]
Ok for final step of engine12 calculation, needs 3 new columns (all columns added after current output columns):

1) New Column 1:  For each input sheet line, calculate first time phase index =-1 and note down the close price of that in a new column.  Only do note the 1st phase index = -1 for each input line.  You can think of this like opening a short position.

2) New Column 2:  For each input line, after the first time phase index = -1, if any increase in phase index AND close price > close price noted in step 1 above, then note the higher close price in the second new column.   You can think of this like close or stop loss the short position opened in step 1.
Please note:  this rule applies *only* for timestamp when phase index actually increase, so for example:
a) Phase index -1 first time with option closing price = 10.  
b)  Then later phase index increases value to +1 with close price = 9.5.  
c) Now phase index value stays +1 for several rows and even has some rows close price > 10 with phase index = +1, BUT still we don't note down the close price in column 2 because close price was not > step 1 close price *when the phase index increased the value*.   We only looking at timestamps when phase index increase the value.  Only note down in column 2 if phase index increase the value and close price > step 1 close price.
After any exit above, then if there is a new phase index -1 again before end time, then note down the close price in column 1 again.  And then do the same thing for any new column 2 value.  Continue doing step 1 and step 2 until end time for each input row.

3) New Column 3:  At each step 2 above also note down in a new column 3 the difference of:   Close price of Step 2 minus Close Price of Step 1.
 And finally if any open position in column 1 and makes it all the way to end time without any column 2 greater close price, then note this final value in Column 3:   Close price of Step 1 minus Final close price at end time.

=============================================
Also I need one more thing.  I need some way to differentiate the trades.  right now it just gives all in one big sheet.  can we add the trade number at first column and all rows for trade 1 for example have the number "1" in the column, and then all rows for trade 2 have number "2" in the column, etc...

i can add a column with "trade" and just include the number and you can print in in front of all rows related to that trade?

ok and you will print the trade number for all rows for each trade yes?