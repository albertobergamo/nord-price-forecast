# PREREG_FWD - Pre-registration of the live forward test (2026-11-06)

Committed before the first scheduled run. Never edited after its commit. If something here is wrong, it is reported in RESULTS_FWD.md, not fixed here.

## Hypothesis
A frozen LEAR model (Lago et al., 2021, no exogenous variables) forecasts GME NORD hourly day-ahead prices for delivery day D more accurately than the best naive benchmark, on data that did not exist when the model was frozen.

## Frozen specification (self-contained)
- One `sklearn.linear_model.LassoLarsIC(criterion="bic", fit_intercept=True, max_iter=2500)` per published hour h in 1..24. Target: price at hour h of delivery day D.
- Inputs: all 24 hourly prices of each of D-1, D-2, D-3, D-7 (96 columns) plus 7 day-of-week dummies for D. No exogenous variables, no holiday dummies.
- Scaling: median and unscaled MAD (`median(|x - median|)`) of all hourly prices (hours 1..24, missing excluded) in the 728-day calibration window D-728..D-1; inputs and targets transformed with `asinh((x - median)/MAD)`; forecasts inverted with `sinh(.)*MAD + median`. Dummies untouched.
- Recalibrated every day on the previous 728 days (training rows are days t in D-728..D-1 with features from t-1, t-2, t-3, t-7).
- DST: 24 models; hour 25 never forecast or scored; a missing hour on a 23-hour day is interpolated within the day in inputs only; metrics use rows where actual, LEAR, naive-1 and naive-7 are all defined.
- Implementation: `src/lear.py`, tagged `fwd-spec`. It was verified to reproduce the earlier research code's forecasts (power-it H2, commit 2ffe00f) to 0.0 absolute difference on 4 sampled historical days spanning 2019-2022, in the same live mode used here (data truncated at D-1). Changes to `src/lear.py` or to the model inputs after the tag invalidate the test. Infrastructure fixes (download, workflow) are allowed and logged in the README changelog.

## Information timing
- The scheduled job runs at 08:00 UTC on calendar day X and forecasts delivery day D = X+1. It uses only GME NORD prices published up to day X (the results for X were published on X-1, after the day-ahead auction of X-1). Nothing about D is used.
- The day-ahead gate for D closes at 12:00 CET on X, i.e. 10:00 or 11:00 UTC. `src/forecast.py` refuses to write a scheduled forecast after 10:00 UTC.
- Proof of timing: the first commit adding `forecasts/D.csv`, authored by `github-actions[bot]`, together with the public Actions run metadata (run id in the commit message). Git committer dates can be forged by a repository owner, so the Actions run record is the reference; the owner is not claimed to be unable to alter history, only that the public record is checkable.

## Test window
- 60 consecutive delivery days: **2026-11-08 .. 2027-01-06** inclusive. (First scheduled run: 2026-11-07 08:00 UTC, delivery day 2026-11-08.) The window is fixed in advance; missing days stay in the 60 and are not replaced.

## Missing days and validity
- A delivery day is **missing** if there is no `forecasts/D.csv` whose first commit is before 10:00 UTC on D-1, or if the published prices for D are not available when the evaluation is run.
- If **more than 6** of the 60 days are missing, the test is **INVALID** (not PASS, not FAIL).

## Benchmarks and PASS rule (identical to H2)
- naive-1: price at the same published hour of D-1. naive-7: same hour of D-7. Best naive = the lower hourly MAE over the common sample (non-missing days; rows where all four values are defined).
- Hourly MAE pooled over those rows.
- One-sided Diebold-Mariano on daily mean absolute loss, d = L(best naive) - L(LEAR), OLS on a constant with Newey-West HAC covariance, `maxlags = floor(4*(T/100)^(2/9))`, p = 1 - Phi(t).
- **PASS** iff (1) MAE_LEAR <= 0.9 x MAE_bestnaive and (2) DM one-sided p < 0.05. Otherwise FAIL (if valid).
- With T of about 60 days the test has limited power; a FAIL does not prove LEAR has no edge, and the rule is not relaxed.

## Procedure
- `src/fwd_evaluate.py` implements this rule on `scores.csv`. It is run once after 2027-01-06 results are scored; its output is committed as RESULTS_FWD.md. The Pages dashboard shows a running MAE for transparency; it has no stopping rule and nothing is changed in response to it.
- Scores (`scores.csv`) contain, per hour: actual, LEAR, naive-1, naive-7, absolute errors, forecast commit time and the on-time flag, computed by `src/score.py` from the git history.
- Manual workflow runs are dry runs by default and are not committed. Any forecast file committed by a manual run is subject to the same on-time rule.

## Data
- Prices: GME MGP hourly, zone NORD (Gestore dei Mercati Energetici S.p.A.), downloaded in the workflow, never committed. Hourly files continue to be published after the 2025-10-01 move to 15-minute clearing.
