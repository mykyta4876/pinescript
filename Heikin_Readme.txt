1. Import the 15-minute Heikin candle data into the general 15-minute candle chart.
2. When the current Heikin negative candle is present,
1. After excluding the current Heikin candle and the second recent Heikin candle
2. Running a for loop from the 3rd to the 10th most recent
1. What if the ‘closing price’ of the nth Heikin Ash candle is located between 1/2 of the body of the current HikinAsh negative candle and the open price?
1. Buy short


1. - The repetition number in the for statement refers to the 3rd to 10th most recent repetition. (For reference, the index is the current candle number 1.)



This is the standard for the second recent Heiken candle. ▼
- The second ‘closing price’ of the negative Hikinashi candle can be lower than the opening price of the ‘nth standard candle,
and can be higher than the ‘closing price’ of the current candle.



(However, the ‘closing price’ of the negative Hikinashi candle must not be lower than the ‘closing price’ of the current candle)



- or the second ‘closing price’ of the negative Hikinashi candle may be higher than the opening price of the ‘nth standard candle.

If there is anything ambiguous or difficult to understand, please let me know at any time.


The reason I use the for loop is to prevent entry like the above.



Since it has already broken through the 9th candle, there is no need to break again based on the 23rd candle.



So, if you go through the for loop and find the first candle that breaks through, you enter a short.

While running the for loop, if a breakout occurs at the 9th candle, buy short, and there is no need to run the for loop for the 10th candle to the 23rd candle.


When the current Heikin negative candle is present, 
Running a for loop from the 3rd to the 10th most recent
if the ‘closing price’ of the nth Heikin Ash candle is located between 1/2 of the body of the current HikinAsh negative candle and the open price, open short position.





================================================
When there is a standard candle and a current candle, there are two or more middle candles between them.
The closing price of the middle candle must be higher than the closing price of the current candle.



And the important thing here is
this code can have 10 or 20 candles or 40 candles

Therefore, there is a limit to continuously adding repeated code using if statements.

So I think we need a nested for loop.

To check whether the close price of the middle candle between the standard candle and the current candle is greater than the 'close' of the current candle,
