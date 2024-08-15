
https://github.com/artnaz/pine_strategy

We collaborate on GitHub: https://github.com/artnaz/pine_strategy/. A more elaborate description can b efound there, as well as the code that needs to be processed.
Work to be done:

1. Fix exiting of TP with 0% allocation
Currently, when allocation is set to 0% at e.g. TP1 and that level is used to move SL to e.g. breakeven or to activate SuperTrend, the trade is still closed at the TP level.

2. Martingale behaviour
The "Martingale" refers to when the entry size multiplier is set to e.g. 2. The idea is that if you lose a trade, you double up on the next trade to hopefully get your loss of the previous trade back. This works in normal cases, but the following should be implemented now that the 5 TP levels are implemented:
If break-even (BE) even has been activated and current price reaches BE this is not to be counted as a Loss or Win in martingale calculation. Reason is if martingale was set to multiply x 2 for 5 losses and BE was achieved on 3rd consecutive loss the overall return for the martingale string on 3rd loss would be an overall loss, but the return on BE returns the amount placed on that 3rd trade only. So due to BE achieving $0 profit on the 3rd trade only no Loss or Win to be added to martingale string calculation. Reason being is to limit the amount of losses in martingale string.
Break even trades not to be included in Win Loss streak calculation
Partial TP - trades returning less than 100% will be considered a loss

3. Test & improve
I can imagine the code can be done more efficiently here and there using Pine Script's best practices. I find the trade execution part quite messy.

