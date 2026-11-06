"""Append actuals and naive-1/naive-7 errors to scores.csv for every forecast file not yet scored."""
import subprocess
from pathlib import Path
import numpy as np, pandas as pd

ROOT = Path(__file__).resolve().parent.parent
px = pd.read_csv(ROOT / "data" / "gme_nord.csv", parse_dates=["date"]).set_index(["date", "hour"])["nord"]
sc_path = ROOT / "scores.csv"
done = set(pd.read_csv(sc_path)["delivery_date"]) if sc_path.exists() else set()
new = []
for f in sorted((ROOT / "forecasts").glob("????-??-??.csv")):
    F = pd.Timestamp(f.stem)
    if f.stem in done:
        continue
    fc = pd.read_csv(f)
    act = [px.get((F, h), np.nan) for h in fc["hour"]]
    if np.isnan(act).all():
        print("no published prices yet for", f.stem); continue
    commit = subprocess.run(["git", "log", "--diff-filter=A", "--format=%cI", "--", f"forecasts/{f.name}"],
                            capture_output=True, text=True, cwd=ROOT).stdout.split()
    commit_utc = pd.Timestamp(commit[-1]).tz_convert("UTC") if commit else pd.NaT
    deadline = pd.Timestamp(F - pd.Timedelta(days=1)).tz_localize("UTC") + pd.Timedelta(hours=10)
    on_time = bool(pd.notna(commit_utc) and commit_utc < deadline)
    d = pd.DataFrame(dict(delivery_date=f.stem, hour=fc["hour"], actual=act, lear=fc["lear"],
                          naive1=[px.get((F - pd.Timedelta(days=1), h), np.nan) for h in fc["hour"]],
                          naive7=[px.get((F - pd.Timedelta(days=7), h), np.nan) for h in fc["hour"]]))
    for c in ["lear", "naive1", "naive7"]:
        d[f"ae_{c}"] = (d[c] - d["actual"]).abs()
    d["forecast_commit_utc"] = commit_utc.strftime("%Y-%m-%dT%H:%M:%SZ") if pd.notna(commit_utc) else ""
    d["on_time"] = on_time
    new.append(d)
if new:
    out = pd.concat(([pd.read_csv(sc_path)] if sc_path.exists() else []) + new)
    out.to_csv(sc_path, index=False); print("scored", [d.delivery_date.iloc[0] for d in new])
else:
    print("nothing new to score")
