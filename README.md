# nord-price-forecast

Live forward test of a frozen LEAR model (Lago et al., 2021) forecasting hourly day-ahead prices of the Italian NORD zone (GME MGP).

- `forecasts/D.csv`: forecast for delivery day D, committed by a GitHub Actions bot at 08:00 UTC on D-1, before the day-ahead auction closes.
- `scores.csv`: actuals plus naive-1 / naive-7 errors, appended daily after the results are published.
- Dashboard: GitHub Pages (latest forecast vs actual, running MAE vs naive-1 and naive-7).
- Pre-registration: [PREREG_FWD.md](PREREG_FWD.md) (60 delivery days from 2026-11-08; PASS rule fixed in advance).

## Data and terms
Price data: Gestore dei Mercati Energetici S.p.A. (GME), day-ahead market (MGP) results. GME data is for personal, non-commercial use and must be cited; the raw files are downloaded inside the workflow and are **not** stored in this repository. `scores.csv` republishes only the NORD hourly actuals needed to score the forecasts. Remove it if GME objects.

Not investment advice. Research project.

## Layout
- `src/lear.py` frozen model; `src/fetch_gme.py` download/parse; `src/forecast.py` forecast; `src/score.py` scoring; `src/fwd_evaluate.py` pre-registered evaluation.
- `tests/test_equivalence.py` checks the model against the original research forecasts.

## Changelog (infrastructure only)
- 2026-11-06: initial version.
