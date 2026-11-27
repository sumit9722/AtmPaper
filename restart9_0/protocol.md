# Restart 9 — situational attributes and NYC → Chicago transfer (frozen protocol)

Recorded 2026-11-27 and committed to Git **before** any new attribute is joined to
an outcome. The commit hash and GitHub push time are the timestamp. Any later
change is a labelled amendment in `amendments.md`; results of the frozen design
are always reported.

Exploratory. The 2024 and 2025 outcomes were inspected in Restarts 6–8.

## Question

Can situational attributes of an ATM site predict crime **over and above prior
crime** (lighting, nearby bars and liquor stores, night-time activity, police
stations, highways, branch hours, ATM/branch age)? The key case is a model trained
in New York City and applied to Chicago, with Los Angeles as a second target.

## Cohort, outcomes, baseline (unchanged from Restarts 7/8)

* Cohort: Restart 7 conservative core, 1,790 site-years (2024: 855; 2025: 935).
* **O1 (primary):** `recorded_any_50m`, any robbery or structural burglary within
  50 m of the released coordinates in the outcome year.
* **O2 (secondary):** `atm_premise_any_100m` from Restart 8 (NYC and Chicago only).
* **Baseline M0:** `log1p_prior_local_50m_retrospective`,
  `log1p_prior_annulus_200_500m_retrospective`.

## New attributes (M9), all measured before the outcome year

OSM layers come from ohsome snapshots on 15 December of the preceding year.
311 requests cover the preceding calendar year. Distances are projected (UTM),
capped at 5,000 m, and then `log1p`. Counts are `log1p`.

| # | feature | source | definition |
|---|---------|--------|-----------|
| A1 | `log1p_bars_250m` | OSM | amenity ∈ {bar, pub, nightclub, biergarten} within 250 m |
| A2 | `log1p_dist_bar_m` | OSM | distance to nearest of A1 |
| A3 | `log1p_liquor_250m` | OSM | shop ∈ {alcohol, wine} within 250 m |
| A4 | `log1p_dist_liquor_m` | OSM | distance to nearest of A3 |
| A5 | `log1p_light_outage_311_100m` | city 311 | street-light failure requests within 100 m, preceding year (NYC: complaint_type "Street Light Condition", descriptors containing Out/Dim/Missing/Cycling; Chicago: "Street Light Out", "Alley Light Out", "Viaduct Light Out" complaints; LA: "Single/Multiple Streetlight Issue") |
| A6 | `log1p_night_poi_250m` | OSM | amenity ∈ {fast_food, cinema, theatre, casino, fuel} or shop=convenience within 250 m |
| A7 | `log1p_poi_24_7_250m` | OSM | any object with opening_hours="24/7" within 250 m (excluding the focal object) |
| A8 | `log1p_dist_rail_m` | OSM | nearest railway=station, or public_transport=station with train/subway/light_rail=yes |
| A9 | `log1p_dist_police_m` | OSM | nearest amenity=police |
| A10 | `log1p_dist_highway_m` | OSM | nearest highway ∈ {motorway, trunk, motorway_link, trunk_link} line |
| A11 | `hours_known` | OSM focal tags | focal object has opening_hours |
| A12 | `open_weekend` | OSM focal tags | opening_hours lists Sa or Su as open (or 24/7) |
| A13 | `open_late` | OSM focal tags | any closing time ≥ 18:00 (or 24/7) |
| A14 | `atm_mapped_age_years` | OSM full history | years from first version matching the ATM filter to the snapshot date |
| A15 | `fdic_branch_age_years` | FDIC SOD (R8) | years since the co-located branch (≤50 m) was established; missing if none |

**Unavailable, so not included:** cash-load schedules (not public); true ATM
installation dates (A14 is a mapping-age proxy); direct night-time pedestrian
counts (no comparable open source across the three cities); OSM street lamps (far
below the cities' actual streetlight stock, so a count would measure mapping effort).

**Secondary feature sets**

* **M9F** = M9 + Restart 8 `log_branch_deposits` and `fdic_branch_50m`.
* **M9L** (NYC and Chicago only) = M9 with A1–A4 replaced by official alcohol
  licences active on 15 December of the preceding year: on-premise licences within
  250 m, off-premise licences within 250 m, and the nearest distance to each.
  NY SLA active and inactive lists: on-premise = description matches
  restaurant|food & beverage|club|tavern|bar|hotel|cabaret|brew; off-premise =
  Liquor Store|Grocery Store|Drug Store. Chicago business licences: on-premise =
  Tavern, Consumption on Premises - Incidental Activity; off-premise = Package Goods.

## Designs

* **D1 (primary):** train NYC 2024 → test Chicago 2025. LA 2025 is a secondary target.
* **D2:** train NYC 2024 + Chicago 2024 → test Chicago 2025. Five 2 km hash folds
  on the Chicago test. Chicago training rows are purged within 1,500 m and by shared
  geography groups (Restart 7 rule).
* **D3:** Restart 7 pooled three-city 2024 → 2025 spatial-fold design, unchanged.

## Learners

* **LR:** Restart 7 pipeline (median imputation, scaling, L2 logistic),
  C ∈ {0.01, 0.1, 1, 10} chosen by inner purged spatial CV on AP.
* **LGBM:** LightGBM, learning_rate 0.03, subsample 0.8 (bagging_freq 1),
  colsample 0.8, reg_lambda 1, seed 9.
  Grid: num_leaves {4, 8, 16} × min_child_samples {20, 40} × n_estimators {100, 300},
  chosen by the same inner CV on AP. Missing values are left to LightGBM. Single-threaded and deterministic.

## Primary test and success rule

Two primary contrasts on D1/O1, Chicago 2025:
(a) LR-M9 vs LR-M0, (b) LGBM-M9 vs LR-M0 (the strongest baseline).
Paired AP difference with 2,000 bootstrap resamples of 2 km test blocks.
**Success:** AP gain ≥ 0.01, Bonferroni-adjusted (2 contrasts) interval lower bound
(1.25th percentile) > 0, and Brier score no worse than LR-M0. Every other contrast
is reported with 95% intervals as secondary/descriptive. LightGBM SHAP values and
test-set permutation importance are descriptive only.

## Rules

No candidate, radius, cohort, outcome or hyperparameter is added or changed after
results are seen without a labelled amendment. Failed and unfavourable results are
reported in full.
