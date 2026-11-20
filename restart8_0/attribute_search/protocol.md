# Restart 8 — ATM-specific attribute search (declared before outcome linkage)

Recorded 2026-11-20, before any candidate below was joined to an outcome.
Exploratory. Both 2024 and 2025 outcomes were inspected in earlier restarts.

## Question

Is there a *site-level ATM attribute* (a property of the machine/facility itself,
not neighbourhood census context) that adds predictive information beyond the
Restart 7 common baseline M0 = log1p(prior-year crime within 50 m) +
log1p(prior-year crime at >200–500 m)?

## Frozen candidate list (theory → expected sign)

All measured from data available before the outcome year (OSM December snapshot
preceding the outcome year; FDIC Summary of Deposits of June of the preceding year).

| id | attribute | source | theory |
|----|-----------|--------|--------|
| C1 | `standalone_atm` — OSM amenity=atm (off-premise), not a bank branch | OSM | off-premise ATMs lack branch guardianship (+) |
| C2 | `drive_through` — OSM drive_through=yes vs no/unknown | OSM | car-oriented access, fewer pedestrians (−) |
| C3 | `open_24_7` — opening_hours or opening_hours:atm = 24/7 | OSM | night-time exposure (+) |
| C4 | `log_branch_deposits` — log1p deposits ($k) of FDIC branch within 50 m (0 if none) | FDIC SOD | customer/cash flow = target supply (+) |
| C5 | `fdic_branch_50m` — any FDIC branch within 50 m | FDIC SOD | staffed branch = guardianship (−) |
| C6 | `megabank` — brand in {Chase, Bank of America, Citibank, Wells Fargo} | OSM | high-traffic siting (+) |
| C7 | `log_atm_density_500m` — mapped ATM/bank objects within 500 m (existing R7 sensitivity field) | OSM | ATM agglomeration = cash-access hub (+) |
| C8 | `branch_age_years` — years since FDIC branch established (NA if none; median-imputed in training) | FDIC SOD | established high-street location (+) |

No other candidates are added after seeing results. Any later idea is labelled
post hoc.

## Outcomes

* **Primary (R7 endpoint):** `recorded_any_50m` on the R7 core cohort
  (1,790 site-years; 2024 train, 2025 test).
* **Secondary (ATM-specific):** any police incident whose *premise is coded ATM*
  (NYC `ATM`, Chicago `ATM (AUTOMATIC TELLER MACHINE)`, LA `AUTOMATED TELLER
  MACHINE (ATM)` / `ATM Separate from Bank`), any offence, released coordinate
  within 100 m of the site, in the outcome year. Restart 8 raw pull.

## Test

Reuse the R7 Phase 4 design exactly: 2024→2025, five 2 km hash spatial folds,
1,500 m + geography-group purge, nested C ∈ {0.01,0.1,1,10}, training-only
imputation/scaling. For each candidate k: M0+k vs M0, pooled AP difference with
2,000 within-city 2 km block bootstrap resamples. Also a 2024-only likelihood
ratio test (logistic, city fixed effects, cluster-robust by 2 km block).

**Acceptance (per candidate):** AP gain > 0 with 95% block-bootstrap lower bound
> 0, Brier not worse, Holm-adjusted (8 candidates) LR p < 0.05 in training year,
and the same sign in ≥2 of 3 cities. Report every candidate either way.
