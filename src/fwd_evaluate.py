"""Pre-registered forward evaluation (PREREG_FWD.md): 60 delivery days from 2026-11-08, same PASS rule as H2.
Computed from the daily rows of scores.csv only (pooled hourly MAE = n_hours-weighted mean of the daily MAEs)."""
import json
from pathlib import Path
import numpy as np, pandas as pd, statsmodels.api as sm
from scipy.stats import norm

ROOT = Path(__file__).resolve().parent.parent
FIRST, N_DAYS, MAX_MISSING = pd.Timestamp("2026-11-08"), 60, 6
dates = [FIRST + pd.Timedelta(days=i) for i in range(N_DAYS)]
for d in dates:  # no DST transition day in the window: every delivery day has exactly 24 hours
    assert (d + pd.Timedelta(days=1)).tz_localize("Europe/Rome") - d.tz_localize("Europe/Rome") == pd.Timedelta(hours=24), f"DST day {d.date()} in window"
window = [d.strftime("%Y-%m-%d") for d in dates]
sc = pd.read_csv(ROOT / "scores.csv")
assert list(sc.columns) == ["delivery_date", "on_time", "n_hours", "mae_lear", "mae_naive1", "mae_naive7"]
sc = sc[sc.delivery_date.isin(window) & (sc.on_time == True)].drop_duplicates("delivery_date").sort_values("delivery_date")
missing = [d for d in window if d not in set(sc.delivery_date)]
res = dict(window=[window[0], window[-1]], valid_days=len(sc), missing_days=len(missing), missing=missing)
if len(missing) > MAX_MISSING:
    res["verdict"] = "INVALID"
else:
    w = sc.n_hours.to_numpy(float)
    mae = {c: float(np.average(sc[f"mae_{c}"], weights=w)) for c in ["lear", "naive1", "naive7"]}
    best = min(["naive1", "naive7"], key=lambda c: mae[c])
    d = (sc[f"mae_{best}"] - sc["mae_lear"]).to_numpy()
    T = len(d); lag = int(np.floor(4 * (T / 100) ** (2 / 9)))
    r = sm.OLS(d, np.ones(T)).fit(cov_type="HAC", cov_kwds=dict(maxlags=lag))
    p = float(norm.sf(r.tvalues[0])); imp = 1 - mae["lear"] / mae[best]
    res.update(mae=mae, best_naive=best, improvement=imp, dm=dict(T=T, maxlags=lag, mean_d=float(d.mean()), stat=float(r.tvalues[0]), p_one_sided=p),
               rows_used=int(w.sum()), verdict="PASS" if (imp >= 0.10 and p < 0.05) else "FAIL")
print(json.dumps(res, indent=1))
