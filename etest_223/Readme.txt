This is a very very small job.
I have strategy script though simple behaves in ways that I don't understand and I need some help with that.

I am assuming there is a very basic concept that I am missing, but.. In summary I am getting some weird behaviors like for example a long trade exiting on the basis of the stoploss of another trade.

Note:
- All candles are properly filtered
- All entries are done at the right moment and the right price
- The first few exits are also correct

The problem occurs after the first few exits.

In the video example ( https://www.loom.com/share/9cb23ef5f0c249a584314eb7cace9393 )
long trade L-5532 exit is SL-5607 ( see: https://prnt.sc/HYHnCRagEKva )

what I need help with

- is fixing the problem

- ensuring the code behaves as explained in the video. In particular, once long is triggered, it should exit either on Take Profit, Stop loss or Slope change (see video)

The only thing that is not working is the exit once the slope is negative

https://prnt.sc/TGHf204HvD_L
https://prnt.sc/ot7EkWhLap1K
https://prnt.sc/Q5D0oi8Cyx20
