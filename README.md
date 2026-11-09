# nord-price-forecast

Live forward test of a frozen LEAR model (Lago et al., 2021) forecasting hourly day-ahead prices of the Italian NORD zone (GME MGP).

- `forecasts/D.csv`: forecast for delivery day D, committed by a GitHub Actions bot at 08:00 UTC on D-1, before the day-ahead auction closes.
- `scores.csv`: one row per delivery day: on-time flag and daily mean absolute error of LEAR, naive-1 and naive-7 (no prices), appended daily after the results are published.
- Dashboard: GitHub Pages (latest published forecast curve; running daily-MAE chart of LEAR vs naive-1 and naive-7).
- Pre-registration: [PREREG_FWD.md](PREREG_FWD.md) (60 delivery days from 2026-11-08; PASS rule fixed in advance).

## Data and terms
Market data: Gestore dei Mercati Energetici S.p.A. (GME), day-ahead market (MGP) results. GME data is for personal, non-commercial use and must be cited. This repository contains no GME prices: the forecast job downloads them to its temporary runner disk only, and the scoring job holds them in memory only. What is published is the forecast itself and daily mean absolute errors.

Not investment advice. Research project.

## Layout
- `src/lear.py` frozen model; `src/fetch_gme.py` download/parse; `src/forecast.py` forecast; `src/score.py` scoring (daily rows only); `src/fwd_evaluate.py` pre-registered evaluation.
- `tests/test_equivalence.py` checks the model against the original research forecasts.

## Verifica
For each `forecasts/D.meta.json` (D = delivery day), check that the forecast was produced by a GitHub run that started before 10:00 UTC on D-1:

```bash
D=2026-11-12                                   # delivery day to check
RUN=$(jq -r .run_id forecasts/$D.meta.json)
gh run view $RUN --json createdAt,headSha,conclusion,event
git log --diff-filter=A --format='%H %an %cI %s' -- forecasts/$D.csv   # commit that added the CSV
```

The forecast is verified if all of these hold:
1. `createdAt` of the run is before `(D-1)T10:00:00Z`, and `conclusion` is `success`.
2. `generated_at_utc` in the sidecar is also before `(D-1)T10:00:00Z`.
3. The commit that added `forecasts/D.csv` is authored by `github-actions[bot]` and its subject ends with `(run <run_id>)`.
4. That commit also contains `forecasts/D.meta.json`, and `headSha` of the run is its ancestor: `git merge-base --is-ancestor <headSha> <commit>`.

5. OpenTimestamps: `ots verify forecasts/$D.csv.ots` reports a Bitcoin attestation (block time) and it is compared with the publication of the MGP results for D. GME publishes the general provisional MGP results "not earlier than 12:55 of day D-1" (final results not earlier than 13:05), Italian local time, i.e. 11:55 UTC in winter (CET) and 10:55 UTC in summer (CEST); the MGP sitting closes at 12:00 of D-1 (Technical Rule no. 03 rev. 14 MPE, art. 2 "Timing of activities for the MGP session": https://gme.mercatoelettrico.org/Portals/0/Documents/en-US/20260113DTF03rev14MPE_en.pdf; same closing time in the GME Vademecum, updated 31 Jan 2026: https://www.mercatoelettrico.org/Portals/0/Documents/en-us/20260131VademecumBorsaElettrica_En.pdf). Note that 12:55 is a lower bound, not a fixed publication time: results cannot appear earlier, they may appear later.
   - Attestation before 12:55 local time of D-1: no look-ahead is possible.
   - Attestation after: weak evidence only; checks 1-4 remain decisive.
   Proofs are created pending by CI and completed in place by the single `ots upgrade` pass in `scripts/archive_runs.sh`; commit the upgraded `.ots` files. `ots verify` needs a local Bitcoin Core node (or use the web verifier at opentimestamps.org with the CSV and the `.ots`). The block time lags the run by hours (calendar aggregation). A missing `.ots` (the stamp step is best effort) does not invalidate a forecast. If the 02:17 stamp fails, the 04:17/06:17 backup run stamps the already-committed CSV (the step runs whenever the newest CSV has no `.ots`), so that `.ots` is later than the forecast run.

Note: `headSha` is the commit the run checked out when it started, so it does not contain `forecasts/D.csv`; the CSV is created by the run and committed at its end (check 3-4).

GitHub deletes run logs after 90 days by default. Run `scripts/archive_runs.sh` (writes `audit/runs.json`) at the end of the test and in any case by 2027-02-01, then commit the file.

## Changelog (infrastructure only)
- 2026-11-06: initial version.
- 2026-11-06: score workflow no longer fails when scores.csv does not exist yet (no change to model or forecasts).
- 2026-11-06 (before the first scheduled run): licensing fix, storage-only change. `scores.csv` now holds daily rows only (delivery_date, on_time, n_hours, mae_lear, mae_naive1, mae_naive7); the scoring job fetches actuals in memory and writes no prices; `src/fwd_evaluate.py` computes the same pre-registered rule from the daily rows (pooled hourly MAE = n_hours-weighted mean of daily MAEs; DM on the same daily differentials) and asserts the window has no DST day; Pages shows only the published forecast and the running daily-MAE chart. The PASS rule, the model and the forecasts are unchanged. Note: PREREG_FWD.md (not edited) describes `scores.csv` as per-hour; that description is superseded by this storage change, the evaluation rule is mathematically identical.
- 2026-11-09: scheduled runs of 2026-11-07 and 2026-11-08 started at ~14:40 UTC (cron 08:00 UTC delayed by GitHub) and were refused by the 10:00 UTC pre-auction guard in `src/forecast.py`; the download step was fine. Fix: cron moved to 02:17 UTC (workflow only; model, `src/forecast.py` and PREREG_FWD.md untouched). Delivery days 2026-11-08 and 2026-11-09 are logged as MISSING and are not backfilled (they stay in the 60-day window, per PREREG_FWD.md). Delivery day 2026-11-10 is also missing: the 2026-11-09 run could not start before 10:00 UTC.
- 2026-11-09 (deviation log): 3 delivery days missing (2026-11-08, 2026-11-09, 2026-11-10) because GitHub delayed the scheduled cron past the 10:00 UTC guard. Infrastructural cause, independent of prices. Mitigation: backup crons 04:17 and 06:17 UTC; `src/forecast.py` skips with exit 0 if the day's forecast already exists (first-write-wins, never overwrites). The 10:00 UTC guard, the model, PREREG_FWD.md and the actuals are unchanged.
- 2026-11-09: audit metadata added. Each new forecast now also writes `forecasts/D.meta.json` (delivery_date, generated_at_utc, run_id = GITHUB_RUN_ID or "local"), committed with the CSV; the CSV is unchanged. The already-forecast skip now runs before the 10:00 UTC guard (the guard itself is unchanged). No impact on the model or PREREG_FWD.md.
- 2026-11-09: README "Verifica" section and `scripts/archive_runs.sh` added (documentation and audit tooling only; not run yet). No impact on the model or PREREG_FWD.md.
- 2026-11-09: best-effort OpenTimestamps step in `forecast.yml` (`ots stamp forecasts/D.csv`, `continue-on-error`, warning on failure, never blocks the commit); `ots upgrade` pass added to `scripts/archive_runs.sh`; README "Verifica" extended. No impact on the model, the CSV or PREREG_FWD.md.\n
- 2026-11-09: README "Verifica" check 5 now references the publication of the MGP results (not earlier than 12:55 local time of D-1, per GME Technical Rule 03 rev. 14 MPE) instead of 10:00 UTC; documentation only, no impact on the model, the CSV or PREREG_FWD.md.
