"""Check src/lear.py reproduces the frozen H2b predictions (power-it/data/h2b_predictions.csv) to 1e-6.
Usage: python tests/test_equivalence.py PRICES_CSV PREDICTIONS_CSV [N_DAYS]"""
import sys
from pathlib import Path
import numpy as np, pandas as pd
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
from lear import load_prices, forecast_day

days, R, Pi = load_prices(sys.argv[1])
ref = pd.read_csv(sys.argv[2], parse_dates=["date"])
n = int(sys.argv[3]) if len(sys.argv) > 3 else 5
sample = sorted(ref.date.unique())[::len(ref.date.unique()) // n][:n]
worst = 0
for D in sample:
    # emulate live mode: truncate data at D-1 and append a NaN row for D
    k = list(days).index(D)
    d2 = days[:k].append(pd.DatetimeIndex([D])); R2 = np.vstack([R[:k], np.full((1, 24), np.nan)]); P2 = np.vstack([Pi[:k], np.full((1, 24), np.nan)])
    p = forecast_day(d2, R2, P2, D)
    r = ref[ref.date == D].sort_values("hour")["lear"].to_numpy()
    worst = max(worst, float(np.max(np.abs(p - r)))); print(D.date(), "max abs diff", np.max(np.abs(p - r)))
assert worst < 1e-6, worst
print("EQUIVALENT")
