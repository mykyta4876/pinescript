The custom indicator will involve 3 MACD indicators with different timeframes. MACD 1 sets the trend direction, and MACD 2 & 3 act as entry condition checkpoints.
Once MACD 2 & 3 align with the trend from MACD 1, an entry signal will be sent to the backend system to trigger a trade.
Additional entry signals (2nd, 3rd, and 4th) will be configured to trigger based on price movement or other conditions after the first signal has taken profit.

Responsibilities:
Develop the custom indicator in Pine Script based on provided logic.
Ensure the indicator is flexible, with adjustable timeframes and MACD settings for each MACD (1, 2, and 3).
Implement logic for sending multiple entry signals (2nd, 3rd, 4th) based on predefined activation conditions (price percentage or dollar thresholds).
Test the indicator for accuracy and functionality.

Remarks: The developer is required to provide their expertise if they identify any functions that are not working properly or can offer better solutions to any issues found. The client may modify parts of the logic after milestone 1 testing, as certain issues or logic may become clearer during actual product testing. The client will only accept the final product if it meets the required logic and functionality.

Kindly refer to the attached document. actually only a little bit modify compare to previous.

Please take a look. The MACD Style and Entry Signal document remain unchanged. The top part of the Multi Indicator section has been modified. Please read the last document, which clearly explains the logic

These is the original EMA and Month/week pine scripts. as we are using its original scripts.
Actually the logic is the same as before. the only different is we replace new order signal from MACD to others. Kindly start the coding asap. thanks

1. Signal Pause Period After a New Trend
This setting allows us to define a “cooldown” period after a new trend signal is detected. During this period, the indicator won’t issue any new signals to avoid over-alerting or acting on potential noise in the market.
* On/Off Toggle: Enables or disables the signal pause period.
* Timeframe Selection: Defines the duration of the pause period (e.g., 12 hours). After a trend signal is detected, no additional signals will be sent for the selected duration.

2. Non-Alert Window
This setting allows us to set specific timeframes where alerts should not be sent, avoiding notifications during certain hours (e.g., non-trading hours or personal downtime).
* On/Off Toggle: Enables or disables the non-alert window feature.
* Day and Time Selection: Let us choose specific days (e.g., Monday) and time ranges (e.g., 12:00 to 15:00) to block alerts. Multiple time windows can be set up, as shown with the example rows labeled "1" and "2."
