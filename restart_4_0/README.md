# Restart 4.0 — complete through Phase 5

**Phases 1–5 are computationally complete; automated validation passed.** The primary exploratory improvement criterion passed.

[Revised research update for the professor](Research_Update_for_Professor_v2.md) frames the simple nearby-crime predictor as a benchmark for an initial geographic transferability check. The [original update](Research_Update_for_Professor.md) is retained.

The strongest recurring additional predictor is **prior-year robbery/burglary within 50 m**, transformed as `log1p(count)` and filtered to reports available before the prediction year. It was selected in all five spatial outer folds and 7 of eight Phase 4 fits overall. Selection compared 28 background/one-additional-variable choices using only 2024 training data.

| model | average_precision | roc_auc | brier_score | top_decile_precision | top_decile_recall |
| --- | --- | --- | --- | --- | --- |
| M0 | 0.7195 | 0.7242 | 0.2112 | 0.7680 | 0.1424 |
| M1 | 0.8254 | 0.7919 | 0.1868 | 0.9440 | 0.1751 |
| M2 | 0.8124 | 0.7748 | 0.1917 | 0.9520 | 0.1766 |

The primary M1−M0 AP gain is **+0.1059**, with paired spatial 95% interval **[+0.0652, +0.1336]**. The evaluation contains 1,241 2025 ATM sites and 674 positive sites; no-skill prevalence is 0.5431. M0 is background-only logistic; M1 adds a training-selected variable with regularization; M2 uses shallow trees with the same selected predictors.

Phase 5 completed **7,380 model evaluations** over 20 adaptation seeds. **9 of 54** source/fraction/model comparisons meet the fixed exploratory support rule: AP gain ≥0.01, positive spatial interval, and Holm-adjusted block-randomization p<0.05. All 54 comparisons, including negative results, are reported in [Phase 5 results](results/phase5/docs/03_results.md).

| city | source | fraction | model | ap_difference | ci_low | ci_high | holm_p |
| --- | --- | --- | --- | --- | --- | --- | --- |
| New York City | Rochester | 0.1 | M1 | 0.0318 | 0.0199 | 0.0416 | 0.0054 |
| New York City | Rochester | 0.1 | M2 | 0.0268 | 0.0178 | 0.0373 | 0.0054 |
| New York City | Rochester | 0.25 | M1 | 0.0159 | 0.0082 | 0.0227 | 0.0100 |
| New York City | Rochester | 0.25 | M2 | 0.0168 | 0.0087 | 0.0251 | 0.0329 |
| New York City | pooled | 0.1 | M2 | 0.0218 | 0.0123 | 0.0321 | 0.0329 |
| Buffalo | New York City | 0.1 | M1 | 0.3960 | 0.2562 | 0.5678 | 0.0054 |
| Buffalo | New York City | 0.25 | M1 | 0.3998 | 0.2524 | 0.5666 | 0.0147 |
| Buffalo | pooled | 0.1 | M1 | 0.3960 | 0.2562 | 0.5678 | 0.0054 |
| Buffalo | pooled | 0.25 | M1 | 0.3998 | 0.2524 | 0.5666 | 0.0147 |

The main improvement measures temporal crime persistence. It does not demonstrate a housing effect, causal ATM risk, or universally beneficial city transfer. Both outcome years were inspected in previous releases, so these are exploratory findings; independent confirmation and source/linkage review remain pending.

[Methods](reports/methods.md) · [Phase 1–3 execution](reports/phase_1_3.md) · [Phase 4 results](results/phase4/docs/03_results.md) · [Phase 5 results](results/phase5/docs/03_results.md) · [Validation status](reports/phase_status.json)

Reproduce from the project root:

```bash
.venv/bin/python restart_4_0/scripts/run_all.py
```

The offline pipeline references the preserved `restart_3_0` and `restart_2024_2025` inputs. Keep those directories. It rechecks cached source digests, reconstructs features, fits every model, recalculates uncertainty and validates before regenerating reports. No new source download is claimed.
