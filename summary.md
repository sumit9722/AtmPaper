# Progress summary through Phase 5

Checked: 11 October 2026

**Overall status:** Computational work through Phase 5 is complete, with passing saved automated validation reports. The project has not passed all scientific acceptance gates: Phase 4 did not establish reliable improvement from environmental features, and independent research review remains pending.

| Phase | Work completed | Completion status |
| --- | --- | --- |
| **1 — Study definition** | Prepared the study specification, crime codebook, source register and historical-exposure rules for New York City, Buffalo and Rochester. | Working documentation complete; researcher ratification and independent codebook review pending. No external preregistration recorded. |
| **2 — ATM and crime panel** | Combined official ATM snapshots and police records, reconstructed supported activity intervals, linked nearby robbery/burglary events at 25/50/100 metres, and calculated prior-year background crime. Produced 2,233 historical sites and 1,192 full-year 2025 sites, plus audit files, checksums and a map. | Computationally complete; saved validation passed. Exposure and linkage still require scientific review. |
| **3 — Common environmental features** | Built comparable demographic, employment, road, transit, accessibility and ATM-density features across all three cities: 14 primary predictors and three sensitivity predictors. Published feature matrices and quality checks. | Computationally complete; saved validation passed. Feature approval remains pending. Road context uses documented proxies; police-station distance was omitted. |
| **4 — Predictive comparisons** | Completed original spatial/city comparisons and a retrospective temporal supplement using 1,201 eligible 2024 training sites and 1,192 2025 test sites. Saved 15 temporal models, predictions, calibration results and spatial-block uncertainty estimates. | Computationally complete and validated, but the predefined improvement gate failed. |
| **5 — Cross-city transfer** | Compared local training, individual and pooled source cities, and source data plus 10%/25% local training samples against matched local-only controls over 20 seeds. Produced 7,380 model evaluations, 7,107 unique fits and 586,464 held-out predictions. | Computationally complete and validated; results remain descriptive rather than confirmatory. |

Phase 4's pooled average precision increased from 0.7189 for M0 to 0.7440 for M1, but the improvement's confidence interval included zero. Phase 5 showed mixed transfer benefits: some conditions improved results in Buffalo and Rochester, while others reduced performance. There is no demonstrated universal transfer benefit.

Remaining work includes independent crime/linkage and facility review, Buffalo coordinate-precision assessment, approval of feature definitions and the 2024 address-continuity amendment, and evaluation on a genuinely uninspected later period. These outcomes measure crime near ATM sites, not confirmed attacks on ATMs.

**Check performed:** Reviewed the execution blueprint, phase documentation and saved validation reports; independently counted the full-year panel and Phase 5 evaluation, fit and prediction rows. Full training and validation pipelines were not rerun for this summary.

Evidence: [Phases 1–2](reports/phase_1_2_report.md), [Phase 3](results/phase3/README.md), [current Phase 4 status](results/phase4/CURRENT_STATUS.md), [Phase 5](results/phase5/README.md), and [Phase 4–5 validation](results/phase5/qa/validation.json).
