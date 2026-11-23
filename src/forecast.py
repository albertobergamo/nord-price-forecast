"""Forecast delivery day F (default: see below) with the frozen H2 LEAR; write forecasts/F.csv (never overwrites).

Default F = (last day in data/gme_nord.csv with all 24 hours) + 1. A non-dry run is refused from 10:00 UTC on F-1 (see PREREG_FWD2.md).
"""
import argparse, datetime as dt, json, os, sys
from zoneinfo import ZoneInfo
from pathlib import Path
import numpy as np, pandas as pd
from lear import load_prices, forecast_day

ROOT = Path(__file__).resolve().parent.parent
ap = argparse.ArgumentParser()
ap.add_argument("--date"); ap.add_argument("--dry-run", action="store_true")
a = ap.parse_args()
now = dt.datetime.now(dt.timezone.utc)
days, R, Pi = load_prices(ROOT / "data" / "gme_nord.csv")
if a.date:
    F = pd.Timestamp(a.date)
else:  # day after the last complete day (non-NaN hours == expected: 23 on spring-forward in Europe/Rome, else 24); a partial last day is itself the target
    rome = lambda d: d.tz_localize(ZoneInfo("Europe/Rome"))
    expected = np.array([min(24, int((rome(d + pd.Timedelta(days=1)) - rome(d)) / pd.Timedelta(hours=1))) for d in days])
    F = days[(~np.isnan(R)).sum(axis=1) == expected][-1] + pd.Timedelta(days=1)
out = ROOT / "forecasts" / f"{F:%Y-%m-%d}.csv"
if out.exists():
    print(f"already forecast, skip: {out.name} exists (first-write-wins, never overwritten)"); sys.exit(0)
deadline = (F - pd.Timedelta(days=1)).tz_localize("UTC") + pd.Timedelta(hours=10)
if not a.dry_run and pd.Timestamp(now) >= deadline:
    sys.exit(f"refusing: {now:%Y-%m-%d %H:%M} UTC is not before {deadline:%Y-%m-%d %H:%M} UTC; forecast for {F.date()} would not be provably pre-auction")
if a.date and days[-1] != F - pd.Timedelta(days=1):
    sys.exit(f"data ends {days[-1].date()}, need {(F - pd.Timedelta(days=1)).date()} for delivery day {F.date()}")
keep = days < F  # drop a partial day F (and anything later) so F is only appended once; no-op when data ends at F-1
days, R, Pi = days[keep], R[keep], Pi[keep]
days = days.append(pd.DatetimeIndex([F]))
R = np.vstack([R, np.full((1, 24), np.nan)]); Pi = np.vstack([Pi, np.full((1, 24), np.nan)])
p = forecast_day(days, R, Pi, F)
df = pd.DataFrame(dict(delivery_date=F.date(), hour=range(1, 25), lear=p.round(4), generated_utc=now.strftime("%Y-%m-%dT%H:%M:%SZ")))
if a.dry_run:
    print(df.to_string(index=False)); sys.exit()
df.to_csv(out, index=False); print("wrote", out)
meta = dict(delivery_date=str(F.date()), generated_at_utc=now.strftime("%Y-%m-%dT%H:%M:%SZ"), run_id=os.environ.get("GITHUB_RUN_ID", "local"))
out.with_suffix(".meta.json").write_text(json.dumps(meta, indent=2) + "\n"); print("wrote", out.with_suffix(".meta.json"))
