"""Score forecasts into DAILY rows only (scores.csv). Actuals are fetched in memory and never written to disk or printed.

scores.csv columns: delivery_date, on_time, n_hours, mae_lear, mae_naive1, mae_naive7
(daily mean absolute error over the hours where actual, LEAR, naive-1 and naive-7 are all defined).
Usage: score.py [--dry-run] [--selftest YYYY-MM-DD]
"""
import argparse, datetime as dt, subprocess
from pathlib import Path
import numpy as np, pandas as pd
from fetch_gme import fetch_prices_memory

ROOT = Path(__file__).resolve().parent.parent
COLS = ["delivery_date", "on_time", "n_hours", "mae_lear", "mae_naive1", "mae_naive7"]


def score_day(F, hours, lear, px):
    """Daily MAE row for delivery day F; None if the actuals are not published yet."""
    g = lambda d: np.array([px.get((d, h), np.nan) for h in hours], dtype=float)
    act, n1, n7, lr = g(F), g(F - pd.Timedelta(days=1)), g(F - pd.Timedelta(days=7)), np.asarray(lear, dtype=float)
    ok = ~(np.isnan(act) | np.isnan(n1) | np.isnan(n7) | np.isnan(lr))
    if not ok.any():
        return None
    mae = lambda x: round(float(np.mean(np.abs(x[ok] - act[ok]))), 6)
    return dict(n_hours=int(ok.sum()), mae_lear=mae(lr), mae_naive1=mae(n1), mae_naive7=mae(n7))


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--dry-run", action="store_true"); ap.add_argument("--selftest")
    a = ap.parse_args()
    today = pd.Timestamp(dt.datetime.now(dt.timezone.utc).date())
    px = fetch_prices_memory((today - pd.Timedelta(days=10)).strftime("%Y-%m"), (today + pd.Timedelta(days=1)).strftime("%Y-%m"))
    print("fetched", len(px), "hourly values in memory")  # count only
    if a.selftest:  # pipeline check on a past day: LEAR := naive-1, so mae_lear must equal mae_naive1
        S = pd.Timestamp(a.selftest); hours = list(range(1, 25))
        r = score_day(S, hours, [px.get((S - pd.Timedelta(days=1), h), np.nan) for h in hours], px)
        assert r and r["mae_lear"] == r["mae_naive1"], r
        print("selftest ok", S.date(), r)
    sc_path = ROOT / "scores.csv"
    old = pd.read_csv(sc_path) if sc_path.exists() else pd.DataFrame(columns=COLS)
    assert list(old.columns) == COLS, f"unexpected scores.csv schema {list(old.columns)}"
    done = set(old["delivery_date"]); new = []
    for f in sorted((ROOT / "forecasts").glob("????-??-??.csv")):
        F = pd.Timestamp(f.stem)
        if f.stem in done:
            continue
        fc = pd.read_csv(f)
        r = score_day(F, list(fc["hour"]), fc["lear"], px)
        if r is None:
            print("no published prices yet for", f.stem); continue
        commit = subprocess.run(["git", "log", "--diff-filter=A", "--format=%cI", "--", f"forecasts/{f.name}"],
                                capture_output=True, text=True, cwd=ROOT).stdout.split()
        deadline = (F - pd.Timedelta(days=1)).tz_localize("UTC") + pd.Timedelta(hours=10)
        on_time = bool(commit) and pd.Timestamp(commit[-1]).tz_convert("UTC") < deadline
        new.append(dict(delivery_date=f.stem, on_time=on_time, **r))
    if not new:
        print("nothing new to score")
    else:
        out = pd.concat([old, pd.DataFrame(new)])[COLS]
        if a.dry_run:
            print("dry-run, not writing:"); print(pd.DataFrame(new).to_string(index=False))
        else:
            out.to_csv(sc_path, index=False); print("scored", [n["delivery_date"] for n in new])
