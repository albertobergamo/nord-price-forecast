"""Pre-registered forward evaluation (PREREG_FWD.md): 60 delivery days from 2026-11-08, same PASS rule as H2."""
import json
from pathlib import Path
import numpy as np, pandas as pd, statsmodels.api as sm
from scipy.stats import norm

ROOT = Path(__file__).resolve().parent.parent
FIRST, N_DAYS, MAX_MISSING = pd.Timestamp("2026-11-08"), 60, 6
window = [(FIRST + pd.Timedelta(days=i)).strftime("%Y-%m-%d") for i in range(N_DAYS)]
sc = pd.read_csv(ROOT / "scores.csv")
valid_days = sorted(set(sc[sc.on_time & sc.delivery_date.isin(window)].delivery_date))
missing = [d for d in window if d not in valid_days]
res = dict(window=[window[0], window[-1]], valid_days=len(valid_days), missing_days=len(missing), missing=missing)
if len(missing) > MAX_MISSING:
    res["verdict"] = "INVALID"
else:
    df = sc[sc.delivery_date.isin(valid_days)].dropna(subset=["actual", "lear", "naive1", "naive7"])
    mae = {c: float(df[f"ae_{c}"].mean()) for c in ["lear", "naive1", "naive7"]}
    best = min(["naive1", "naive7"], key=lambda c: mae[c])
    d = (df.groupby("delivery_date")[f"ae_{best}"].mean() - df.groupby("delivery_date")["ae_lear"].mean()).sort_index()
    T = len(d); lag = int(np.floor(4 * (T / 100) ** (2 / 9)))
    r = sm.OLS(d.values, np.ones(T)).fit(cov_type="HAC", cov_kwds=dict(maxlags=lag))
    p = float(norm.sf(r.tvalues[0])); imp = 1 - mae["lear"] / mae[best]
    res.update(mae=mae, best_naive=best, improvement=imp, dm=dict(T=T, maxlags=lag, mean_d=float(d.mean()), stat=float(r.tvalues[0]), p_one_sided=p),
               rows_used=len(df), verdict="PASS" if (imp >= 0.10 and p < 0.05) else "FAIL")
print(json.dumps(res, indent=1))
