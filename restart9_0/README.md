# Restart 9 — situational attributes, NYC → Chicago transfer, LightGBM

**Result: the primary test FAILED.** The new attributes (lighting, bars, liquor stores,
night-time activity, police stations, highways, branch hours, ATM and branch age) do not
predict crime near ATMs beyond prior crime when a model trained in New York City is
applied to Chicago. Both logistic regression and LightGBM did *worse* than the
crime-history baseline. The rules were committed to GitHub before any result was seen
([protocol](protocol.md), commit `10648207`); the run was done once.

## What was tested

* **Cohort:** Restart 7 conservative core, 1,790 ATM site-years in NYC, Chicago and LA.
* **Outcomes:** O1 (primary) = any robbery or burglary within 50 m in the year. O2 = any
  incident police coded at an ATM premise within 100 m (Restart 8; NYC and Chicago only).
* **Baseline (M0):** prior-year crime within 50 m and at 200–500 m.
* **M9** = M0 + 15 new attributes, all measured before the outcome year:

| Asked for | Measured as | Source |
|---|---|---|
| Lighting | 311 street-light failure requests within 100 m, previous year | NYC / Chicago / LA 311 |
| Bars, liquor stores | count within 250 m and nearest distance | OpenStreetMap (Dec snapshot) |
| Night-time foot traffic | late-night places and 24/7 places within 250 m; distance to rail/subway | OpenStreetMap |
| Police station | distance to nearest | OpenStreetMap |
| Highway | distance to nearest motorway/trunk | OpenStreetMap |
| Bank-branch hours | hours listed, open weekends, open late | OSM tags of the ATM/bank |
| ATM age | years since the ATM was first mapped; age of co-located FDIC branch | OSM history API; FDIC |
| Cash-load schedule | **not available** (not public) | — |

* **M9F** = M9 + Restart 8 branch deposits and branch presence.
* **Designs:** D1 (primary) train NYC 2024 → test Chicago 2025 (LA 2025 secondary);
  D2 train NYC + Chicago 2024 → test Chicago 2025 (spatially purged folds);
  D3 Restart 7 pooled three-city 2024 → 2025 design.
* **Learners:** L2 logistic regression and LightGBM, both tuned by inner spatial CV.
* **Success rule:** AP gain ≥ 0.01 over logistic M0, Bonferroni lower bound > 0, Brier not worse.

## Primary result — NYC → Chicago 2025, robbery/burglary ≤50 m (212 sites, 87 positives)

| model | average precision | gain vs baseline [Bonferroni 97.5% CI] | passes |
|---|---|---|---|
| Logistic M0 (baseline) | **0.764** | — | — |
| Logistic M9 | 0.712 | −0.052 [−0.115, +0.065] | no |
| LightGBM M9 | 0.731 | −0.033 [−0.084, +0.026] | no |
| LightGBM M0 | 0.742 | −0.022 | — |
| Logistic M9F (+ deposits) | 0.700 | −0.064 | no |

NYC → Los Angeles is worse still: logistic M9 0.680 vs baseline 0.781
(−0.101, 95% CI [−0.200, −0.030]). Adding Chicago 2024 training data (D2) does not help:
logistic M9 0.751 vs 0.768.

## Secondary results (no multiplicity correction across ~45 contrasts)

* **Pooled within-city (D3), robbery/burglary:** no gain. Logistic M9 0.805 vs M0 0.804.
  The new attributes help slightly in NYC (0.820 → 0.831) and hurt in Chicago
  (0.765 → 0.738) and LA (0.785 → 0.713). LightGBM M9 beats *LightGBM* M0
  (+0.016) only because LightGBM's own baseline is weaker than logistic M0.
* **Pooled within-city (D3), ATM-premise crime:** the one positive signal. Logistic M9
  0.248 vs M0 0.188 (+0.060, 95% CI [+0.010, +0.100]). With deposits (M9F) the result is
  0.275–0.281. The gain is mostly NYC (0.212 → 0.277); Chicago moves 0.096 → 0.107 (23 positives).
  It does **not** carry over from NYC to Chicago (D1 O2: logistic M9 −0.016).
  Treat it as a hypothesis for a future frozen test, not a finding.

## Which features mattered (descriptive; LightGBM, NYC → Chicago)

Prior local crime dominates (mean |SHAP| 0.46; permutation AP drop 0.24). Next come
distance to rail, night-time places, distance to liquor stores and ATM mapped age
(SHAP 0.12–0.20), but permuting them barely changes Chicago AP (≤0.02) or makes it
better. The 311 lighting failures, bar counts and branch hours contribute almost nothing.
See [importance.csv](results/importance.csv).

## Why this probably failed

* Prior crime already captures most of what these place attributes measure.
* The cities differ (NYC baseline prevalence 63% in 2024, Chicago 41% in 2025). What
  NYC learns about bars or transit does not transfer to Chicago's layout.
* Small samples: 212 Chicago and 112 LA test sites, so intervals are wide.
* Several measures are proxies. OSM undercounts liquor stores outside NYC.
  311 calls reflect reporting habits as well as darkness. Branch hours are tagged for
  50–56% of NYC sites but only 7–22% in Chicago.

## Ranked 2025 predictions

[results/ranked_2025/](results/ranked_2025/summary.md) lists every test ATM per city with its risk rank, bank name, coordinates, both models' scores and what actually happened in 2025. Produced by `scripts/rank_predictions.py` from the saved predictions (no refitting). Among the 10% of ATMs the past-crime model ranked riskiest, all 21 in Chicago, all 11 in LA and 59 of 61 in NYC had a robbery or burglary within 50 m in 2025 (city rates 41%, 33%, 56%).

## Amendments (made before any outcome linkage)

[amendments.md](amendments.md): A1 switched to ohsome v2 / the OSM history API after v1 returned
HTTP 403. A2 withdrew the licence-based variant because NY State Liquor Authority dates cannot
reconstruct 2023/2024 licence status.

## Files

* [protocol.md](protocol.md), [amendments.md](amendments.md)
* `results/`: [contrasts.csv](results/contrasts.csv) (every comparison),
  [metrics.csv](results/metrics.csv), [metrics_by_city.csv](results/metrics_by_city.csv),
  [predictions.csv](results/predictions.csv), [importance.csv](results/importance.csv),
  [tuning.csv](results/tuning.csv), [status.json](results/status.json),
  [features_r9.csv](results/features_r9.csv), [feature_coverage.csv](results/feature_coverage.csv)
* `data/raw/` with [manifest.csv](data/raw/manifest.csv) (SHA-256 of every raw file)

## Reproduce

```bash
python -m venv .venv9 && .venv9/bin/pip install -r restart9_0/requirements.txt
.venv9/bin/python -m unittest discover -s restart9_0/tests -v
.venv9/bin/python -I restart9_0/scripts/acquire.py        # skips cached files; OSM needs restart6_0/apikey.txt
.venv9/bin/python -I restart9_0/scripts/build_features.py
.venv9/bin/python -I restart9_0/scripts/evaluate.py
```

OSM © OpenStreetMap contributors, ODbL. 311 and licence data from the NYC, Chicago, LA and
New York State open-data portals.
