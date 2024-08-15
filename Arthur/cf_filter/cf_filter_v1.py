import numpy as np

from statsmodels.tools.validation import PandasWrapper, array_like
import matplotlib.pyplot as plt

# the data is sampled quarterly, so cut-off frequency of 18

# Wn is normalized cut-off freq
#Cutoff frequency is that frequency where the magnitude response of the filter
# is sqrt(1/2.). For butter, the normalized cutoff frequency Wn must be a
# number between  0 and 1, where 1 corresponds to the Nyquist frequency, p
# radians per sample.


# NOTE: uses a loop, could probably be sped-up for very large datasets
def cffilter(x, low=6, high=32, drift=True):
    if low < 2:
        raise ValueError("low must be >= 2")
    pw = PandasWrapper(x)
    x = array_like(x, 'x', ndim=2)
    nobs, nseries = x.shape
    a = 2*np.pi/high
    b = 2*np.pi/low

    if drift:  # get drift adjusted series
        x = x - np.arange(nobs)[:, None] * (x[-1] - x[0]) / (nobs - 1)

    J = np.arange(1, nobs + 1)
    print(J)
    Bj = (np.sin(b * J) - np.sin(a * J)) / (np.pi * J)
    B0 = (b - a) / np.pi
    Bj = np.r_[B0, Bj][:, None]
    y = np.zeros((nobs, nseries))

    for i in range(nobs):
        B = -.5 * Bj[0] - np.sum(Bj[1:-i - 2])
        A = -Bj[0] - np.sum(Bj[1:-i - 2]) - np.sum(Bj[1:i]) - B
        y[i] = (Bj[0] * x[i] + np.dot(Bj[1:-i - 2].T, x[i + 1:-1]) +
                B * x[-1] + np.dot(Bj[1:i].T, x[1:i][::-1]) + A * x[0])
    y = y.squeeze()

    cycle, trend = y.squeeze(), x.squeeze() - y

    return pw.wrap(cycle, append='cycle'), pw.wrap(trend, append='trend')

if __name__ == "__main__":
    import statsmodels.api as sm
    dta = sm.datasets.macrodata.load().data[['infl','tbilrate']][1:]
    print(dta)
    cycle, trend = cffilter(dta, 6, 32, drift=False)

    print("cycle")
    print(cycle.head(10))

    fig = plt.figure(figsize=(14, 10))
    ax = fig.add_subplot(111)
    cycle.plot(ax=ax, style=["r--", "b-"])

    plt.tight_layout()
    plt.show()