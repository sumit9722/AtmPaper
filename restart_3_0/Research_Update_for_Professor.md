# Research progress report: three-city ATM-site crime study, Phases 1–5

- **Prepared:** 19 October 2026.
- **Study period:** 1 January 2024–31 December 2025; New York City, Buffalo and Rochester.
- **Overall status:** Computational work through Phase 5 is complete, and saved automated validations pass. The analysis remains exploratory. Independent scientific review has not been completed, and 2025 outcomes had been inspected in earlier project work.
- **Main finding:** The prespecified test did not show reliable improvement from the new housing-context variables. Cross-city transfer produced mixed gains and losses, with no general benefit across cities and models.

## Work completed

- **Phase 1 — Study definition**
  - Fixed the study population, 50 m primary nearby-crime endpoint, 25 m and 100 m sensitivities, earlier-year crime background, and annual address-continuity rule before the new model fits.
  - Recorded the offense codebook, source register, analysis specifications and review gates. This is retrospective working documentation, not external preregistration.
- **Phase 2 — Annual ATM and crime panel**
  - Rebuilt the two annual cohorts from preserved ATM inventories and police archives: **1,201 site-years in 2024** and **1,241 in 2025**. A site-year is not necessarily a distinct physical machine.
  - Linked police-recorded robbery and burglary to eligible ATM coordinates. At the primary 50 m radius, **674 of 1,241 2025 sites (54.3%)** had at least one nearby recorded event.
  - Passed source-hash, cohort, distance, linkage and count-reconciliation checks. The saved panel contains **2,442 site-year rows**.
- **Phase 3 — Housing context**
  - Imported eight official [ACS 2018–2022 detailed housing tables](https://www.census.gov/programs-surveys/acs/data/summary-file.2022.html) from the public [Census table-based files](https://www2.census.gov/programs-surveys/acs/summary_file/2022/table-based-SF/data/5YRData/), covering **8,217 block groups in seven counties**. No API credential was used.
  - Added vacancy, renter occupancy, multifamily housing, household crowding, no-vehicle households, median gross rent, housing age and recent moves. Prior-year crime is the ninth, baseline predictor.
  - Matched all **2,442** site-years uniquely to 2022 block-group polygons. Source estimates, margins of error and numeric missing-value codes were retained; 268 rows (11.0%) lack a usable median-rent value. Missing predictors were imputed only within model-training folds.
  - Passed independent reconciliation of every selected source component against the bulk files and validation of every derived feature formula. The bulk format does not supply other API-only annotation qualifiers.
- **Phase 4 — Forward prediction test**
  - Trained on 2024 outcomes reported before 2025 and tested on archived 2025 outcomes. Spatial evaluation purged earlier-year training sites within **1,500 m** of each held-out 2025 site. A separate city-held-out analysis and five predefined sensitivities were also completed.
  - Compared **M0:** logistic regression with prior-year crime; **M1:** logistic regression with crime plus eight housing variables; and **M2:** boosted trees with the same nine predictors.
  - In the primary pooled spatial evaluation, average precision was **0.7195 (M0), 0.7071 (M1), and 0.7001 (M2)**. Paired differences relative to M0 were **−0.0124** for M1 (95% block-bootstrap interval **−0.0492 to +0.0180**) and **−0.0193** for M2 (**−0.0723 to +0.0256**).
  - Neither housing model passed the predefined exploratory improvement criterion of at least +0.01 average precision with a positive lower interval bound. The intervals condition on saved predictions and do not include model-refitting uncertainty. All **141** outer model artifacts and **44,376** saved prediction rows passed validation.
- **Phase 5 — Cross-city transfer**
  - Evaluated local-only training, each other city, pooled source cities, and source data plus matched **10% or 25%** earlier target-city labels. Used **20 fixed sampling seeds** and compared each augmented model with a target-only model trained on exactly the same local sample.
  - Completed **7,380 evaluations**, **7,155 unique saved fits** and **610,572 held-out prediction rows**; all passed the saved validation checks. There were **267** flagged single-class fits, reflecting small training samples in some conditions.
  - Across the **18 source/fraction/model combinations per target city**, mean matched transfer benefit was positive in **11** for New York City, **5** for Buffalo and **14** for Rochester; it was negative in the remaining conditions. These are descriptive comparisons, not independent significance tests. The 20-seed ranges describe sampling variation and are not confidence intervals.

## Interpretation and decisions

- The measured outcome is police-recorded robbery or burglary **near** an ATM site; the records do not establish that the ATM or its customer was targeted.
- The 2025 test year is a forward-time split within this restart, but its outcomes had been examined in earlier analyses. These results therefore cannot serve as an independent confirmation.
- Monthly ATM listings support the annual cohort rule but do not verify continuous operation or machine identity. Coordinate drift, Buffalo location precision, municipal boundary clipping, event-code review and reporting-vintage differences remain material review items.
- ACS housing variables describe neighborhoods rather than ATM security. Their survey uncertainty was retained in source files but was not propagated through model intervals. No causal, deployment or site-placement recommendation follows from these results.
- The appropriate current conclusion is **computational completion with no demonstrated primary housing-feature improvement and no universal transfer benefit**. Confirmatory or operational claims remain on hold.

## Required next steps

- Independently review offense mappings, ambiguous event links, ATM facility/address continuity, Buffalo coordinate precision and boundary effects.
- Obtain substantive approval of the eight housing definitions and assess whether survey uncertainty or missing rent changes interpretation.
- Test the frozen approach on a later, genuinely uninspected outcome period if a confirmatory claim is desired.

## Supporting artifacts

- [Annual panel and Phase 1–2 validation](data/processed/atm_panel_2024_2025_full_year.csv), [Phase 1–2 validation record](reports/validation.json), and [source reconciliation](reports/environment_bulk_validation.json).
- [Phase 3 feature report](results/phase3/docs/execution.md) and [Phase 3 validation](results/phase3/qa/validation.json).
- [Phase 4 methods and results](results/phase4/docs/03_results.md), [Phase 4 validation](results/phase4/qa/validation.json), and [paired AP comparisons](results/phase4/data/paired_ap_comparisons.csv).
- [Phase 5 methods and results](results/phase5/docs/03_results.md), [Phase 5 validation](results/phase5/qa/validation.json), and [all matched-benefit summaries](results/phase5/data/benefit_summary.csv).
