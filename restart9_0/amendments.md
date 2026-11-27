# Restart 9 amendments

## A1 — data access (2026-11-27, before any outcome linkage)

ohsome v1 extraction endpoints (`elements/centroid`, `elements/geometry`) returned
HTTP 403 on the first download attempt; only `count` and `metadata` still respond.
Operational change, no definition changed:

* OSM layers: same ohsome data via the HeiGIT ohsome v2 single-snapshot extraction
  (the endpoint Restart 6 used). Same filters and snapshot dates. Non-point objects use
  the projected centroid of their geometry; highways keep their line geometry.
* A14 `atm_mapped_age_years`: first version matching the ATM filter, taken from the public
  OpenStreetMap API object history (`/api/0.6/{type}/{id}/history`) of each cohort
  object instead of ohsome full history.

## A2 — M9L withdrawn (2026-11-27, data audit, before any outcome linkage)

The NY State Liquor Authority lists cannot reconstruct which licences were active
on 15 December 2023/2024. In the active list, 21,816 of 24,821 NYC licences
(88%) have an "original issue date" in 2025–2026 and only 137 before 2024. This
suggests the records were re-issued under new IDs, so `originalissuedate` is not
the true first issue. As a result, the NYC off-premise count jumps from 2,332
(Dec 2023) to 4,320 (Dec 2024) for no real-world reason.
Counts at the cutoff would be strongly biased toward recent licences, so M9L is not
estimated. Chicago licence features are retained in `features_r9.csv` for reference
only. A1–A4 (OSM) remain the primary bar/liquor measures.

## A3 — exploratory follow-up requested after the frozen results (2026-11-27)

Not part of the frozen test; added at the team's request after the results were seen.
`scripts/transfer_weights.py`:
(1) LightGBM weightage (gain, split and SHAP shares) for the NYC-only D1 model, plus its
Chicago 2025 predictions, AP and ROC-AUC;
(2) NYC 2024 + a random 10% of Chicago 2024 (19 site-years) → Chicago 2025. The 10% is drawn per
spatial test fold from Chicago 2024 sites at least 1,500 m from that fold's test sites, repeated
over 20 seeds. Baselines are past-crime-only logistic and LightGBM on identical data. Results are
exploratory and do not change the frozen verdict.

## A4 — environment-only models (2026-11-27, exploratory, team request)

At the team's request, models were refitted with the 15 situational attributes only, with no
prior-crime inputs (`scripts/env_only.py`). Designs and tuning match A3 (NYC only → Chicago/LA 2025;
NYC + 10% Chicago 2024 → Chicago 2025, same 20 random draws and purge). The reference is chance
(AUC 0.5; AP = test prevalence). This asks whether environment alone ranks ATM risk. It does not
replace the frozen comparison with the crime-history baseline.

## A5 — XGBoost on the environment-only design (2026-11-27, exploratory, team request)

XGBoost added to A4 with identical features, designs, Chicago draws and inner spatial CV
(`scripts/xgb_env_only.py`). Fixed settings: learning rate 0.03, subsample 0.8, colsample 0.8,
L2 1, hist trees, seed 9. Grid: max_depth {2, 3, 4} × min_child_weight {1, 5} ×
n_estimators {100, 300}. A third learner on the same data adds another comparison, so its
result is descriptive.
