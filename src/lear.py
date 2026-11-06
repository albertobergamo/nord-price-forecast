"""Frozen H2 LEAR (identical logic to power-it src/h2_lear.py, commit 2ffe00f).

One LassoLarsIC(BIC) model per published hour 1..24; inputs = 24 hourly prices of D-1, D-2, D-3, D-7
plus 7 weekday dummies; asinh after pooled median/MAD scaling on the 728-day calibration window.
"""
import numpy as np, pandas as pd
from sklearn.linear_model import LassoLarsIC

WIN, LAGS = 728, (1, 2, 3, 7)


def load_prices(csv):
    """Return (days DatetimeIndex, R raw days x 24 with NaN, Pi interpolated within day)."""
    px = pd.read_csv(csv, parse_dates=["date"])
    raw = px.pivot(index="date", columns="hour", values="nord").reindex(columns=range(1, 26))
    days = pd.date_range(raw.index.min(), raw.index.max())
    raw = raw.reindex(days)
    R = raw[list(range(1, 25))].to_numpy()
    Pi = pd.DataFrame(R).interpolate(axis=1, limit_direction="both").to_numpy()
    return days, R, Pi


def forecast_day(days, R, Pi, D):
    """Forecast the 24 hourly prices of day D using only days before D."""
    idx = {d: i for i, d in enumerate(days)}
    i = idx[D]
    feats = lambda t: np.concatenate([Pi[t - l] for l in LAGS] + [np.eye(7)[days[t].dayofweek]])
    tr = [t for t in range(i - WIN, i) if t - 7 >= 0]
    win = R[i - WIN:i]; v = win[~np.isnan(win)]
    med = np.median(v); mad = np.median(np.abs(v - med))
    S = lambda x: np.arcsinh((x - med) / mad)
    X = np.array([feats(t) for t in tr]); X[:, :96] = S(X[:, :96])
    x = feats(i)[None, :].copy(); x[:, :96] = S(x[:, :96])
    out = np.full(24, np.nan)
    for h in range(24):
        y = R[tr, h]; ok = ~np.isnan(y)
        m = LassoLarsIC(criterion="bic", fit_intercept=True, max_iter=2500).fit(X[ok], S(y[ok]))
        out[h] = np.sinh(m.predict(x)[0]) * mad + med
    return out
