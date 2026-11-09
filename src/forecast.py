"""Forecast delivery day F (default: tomorrow, UTC) with the frozen H2 LEAR; write forecasts/F.csv (never overwrites).

The scheduled workflow is only valid before 10:00 UTC (see PREREG_FWD.md): later runs are refused unless --dry-run.
"""
import argparse, datetime as dt, json, os, sys
from pathlib import Path
import numpy as np, pandas as pd
from lear import load_prices, forecast_day

ROOT = Path(__file__).resolve().parent.parent
ap = argparse.ArgumentParser()
ap.add_argument("--date"); ap.add_argument("--dry-run", action="store_true")
a = ap.parse_args()
now = dt.datetime.now(dt.timezone.utc)
F = pd.Timestamp(a.date) if a.date else pd.Timestamp(now.date()) + pd.Timedelta(days=1)
out = ROOT / "forecasts" / f"{F:%Y-%m-%d}.csv"
if out.exists():
    print(f"already forecast, skip: {out.name} exists (first-write-wins, never overwritten)"); sys.exit(0)
if not a.dry_run and now.hour >= 10 and F == pd.Timestamp(now.date()) + pd.Timedelta(days=1):
    sys.exit(f"refusing: {now:%H:%M} UTC is not before 10:00 UTC; forecast for {F.date()} would not be provably pre-auction")
days, R, Pi = load_prices(ROOT / "data" / "gme_nord.csv")
if days[-1] != F - pd.Timedelta(days=1):
    sys.exit(f"data ends {days[-1].date()}, need {(F - pd.Timedelta(days=1)).date()} for delivery day {F.date()}")
days = days.append(pd.DatetimeIndex([F]))
R = np.vstack([R, np.full((1, 24), np.nan)]); Pi = np.vstack([Pi, np.full((1, 24), np.nan)])
p = forecast_day(days, R, Pi, F)
df = pd.DataFrame(dict(delivery_date=F.date(), hour=range(1, 25), lear=p.round(4), generated_utc=now.strftime("%Y-%m-%dT%H:%M:%SZ")))
if a.dry_run:
    print(df.to_string(index=False)); sys.exit()
df.to_csv(out, index=False); print("wrote", out)
meta = dict(delivery_date=str(F.date()), generated_at_utc=now.strftime("%Y-%m-%dT%H:%M:%SZ"), run_id=os.environ.get("GITHUB_RUN_ID", "local"))
out.with_suffix(".meta.json").write_text(json.dumps(meta, indent=2) + "\n"); print("wrote", out.with_suffix(".meta.json"))
