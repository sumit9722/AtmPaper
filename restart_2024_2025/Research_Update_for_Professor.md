# Research update: ATM-site crime prediction and transfer between cities

**Progress as of 18 October 2026**

Since the initial paper, we have built and tested a study covering New York City, Buffalo and Rochester over 2024 and 2025. We focused on two questions: whether environmental information improves prediction beyond the surrounding area's previous crime level, and whether information learned in one city helps prediction in another. We completed the data construction, model comparisons and transfer experiments. The results show a small but uncertain improvement from environmental features, and transfer benefits that depend on the source city, model and amount of local data.

We first clarified what the available records can measure. The primary outcome is whether at least one police-recorded robbery or burglary occurred within 50 metres of an ATM location during a year. We retained both incident counts and a yes/no indicator, and also tested distances of 25 and 100 metres. These records describe **crime near ATM sites**, not necessarily crimes committed against the ATM itself. We therefore do not interpret the predictions as confirmed ATM-attack risk. Fraud and other financial offences were not included in the primary outcome.

We then assembled a common dataset for the three cities. We used the New York State Department of Financial Services inventory of bank-owned/in-bank ATMs, police records from the three cities, and Census municipal boundaries. We assigned locations to cities using their coordinates and the city boundaries, rather than postal city names. We removed exact duplicate ATM records and counted each qualifying police case once, retaining records of exclusions and duplicate handling. The ATM inventory does not cover independent nonbank machines, so the study's population is limited to the inventory's coverage.

We checked historical ATM membership before assigning crime to past locations. We used 14 monthly snapshots bracketing each study year. A major difficulty was that ATM coordinates changed during 2024: requiring exactly the same address and coordinates throughout the year produced no fully supported 2024 records. This was an identity-matching problem, not evidence that no ATMs operated during that year. We therefore used the same alternative rule for both years: retain a city/address appearing uniquely in every monthly snapshot, provided all its listed coordinates remain within 50 metres of its position in the preceding December. We fixed the analysis location to that December position and preserved the stricter matching results for comparison. This rule supports inferred continuity of membership, but it does not verify daily operation or exact opening and closing dates.

This produced the following annual datasets:

| City | ATM sites in 2024 | Sites with nearby primary crime in 2024 | ATM sites in 2025 | Sites with nearby primary crime in 2025 |
|---|---:|---:|---:|---:|
| New York City | 1,129 | 662 | 1,160 | 652 |
| Buffalo | 48 | 16 | 50 | 14 |
| Rochester | 24 | 6 | 31 | 8 |
| **Total** | **1,201** | **684** | **1,241** | **674** |

There are **2,442 annual site records**, not 2,442 distinct machines: a location can contribute in both years. Multiple nearby ATMs can also share the same crime incident. We retained those links and later tested an alternative that assigns an incident only to its nearest eligible ATM.

We next separated local crime outcomes from surrounding crime. For each ATM, we counted the previous year's robbery and burglary incidents more than 200 metres and up to 500 metres away. Thus, 2023 crime supplies background information for predicting 2024, and 2024 crime supplies background information for predicting 2025. The main background measure includes only incidents with a report timestamp before the prediction year; an unrestricted version was retained for comparison. This gives us a baseline that asks how much can already be predicted from ordinary neighborhood crime before adding environmental information.

We then attached environmental information using common definitions across all cities. We used the same 2018–2022 American Community Survey estimates for both prediction years, together with the EPA Smart Location Database released in 2021. The variables cover population density, household income, unemployment, employment and retail intensity, employment mix, road and intersection density, transit service, job accessibility, and proximity to other ATMs. ATM competition was calculated from each year's preceding December inventory, without requiring neighboring ATMs to survive into the outcome year. The resulting primary model inputs contain **13 environmental variables plus the background-crime measure**.

The Census information matched all 2,442 annual site records. EPA information had a unique geographic match for 2,393 records; 25 records had ambiguous matches and 24 had no match. All 49 unresolved cases were in 2025. We retained these records with missing environmental values instead of assigning an arbitrary nearby neighborhood. No feature exceeded 20% missingness in any city/year group. We also checked distributions, unusual values, constant variables and highly correlated predictors. Road and transit variables are neighborhood measures, not direct measurements at each ATM. We did not include police-station distance because a comparable verified historical source was not available.

We then tested whether these environmental variables improve future-year prediction. We trained using 2024 and evaluated using 2025. The 2024 training outcomes were restricted to crimes reported before January 2025. To reduce overly optimistic results from nearby locations sharing information, we divided the locations into spatial groups and removed training sites within 1,500 metres of the held-out test sites. We estimated missing-value replacements, scaling, model settings and optional probability calibration using training data only.

We compared three models: logistic regression using background crime alone; regularized logistic regression using background crime plus the environmental variables; and gradient-boosted trees using the same combined inputs. Our main metric was **average precision**, which measures how well a model ranks sites with observed crime ahead of other sites across prediction thresholds. It is not classification accuracy: a score of 0.74 does not mean that 74% of sites were classified correctly. We also assessed overall ranking with ROC-AUC and probability accuracy with the Brier score, where lower values are better.

The main future-year, spatially separated results were:

| Model | Average precision: higher is better | ROC-AUC: higher is better | Brier score: lower is better |
|---|---:|---:|---:|
| Background crime only | 0.7195 | 0.7242 | 0.2112 |
| Background crime + environment, logistic regression | 0.7414 | 0.7169 | 0.2128 |
| Background crime + environment, boosted trees | 0.6886 | 0.6911 | 0.2210 |

Adding environmental variables to logistic regression increased average precision by **0.0219**. However, the 95% uncertainty interval for that improvement was **−0.0176 to +0.0499**. We estimated this using 2,000 repeated samples of geographic blocks, preserving the pairing between model predictions. Our working criterion required an improvement of at least 0.01 and an interval entirely above zero. The result did not meet that criterion. The environmental logistic model also did not improve ROC-AUC or Brier score, and boosted trees performed worse than the background-only model. Therefore, we have not established reliable additional predictive value from the environmental variables in the main test. This is an inconclusive improvement result, not proof that the environment has no relationship with crime.

We then checked whether that pattern depended on the outcome definition or background measure. We repeated the full comparisons using smaller and larger crime buffers, nearest-ATM incident assignment, an unrestricted prior-year background count, and exclusion of Buffalo. The average-precision results were:

| Test | Background only | Background + environment, logistic regression | Background + environment, boosted trees |
|---|---:|---:|---:|
| Main 50-metre outcome | 0.7195 | 0.7414 | 0.6886 |
| 25-metre outcome | 0.5284 | 0.4642 | 0.4585 |
| 100-metre outcome | 0.9489 | 0.9344 | 0.9366 |
| Nearest-ATM assignment, 50 metres | 0.6456 | 0.6546 | 0.6380 |
| Background without report-date restriction | 0.7194 | 0.7476 | 0.6824 |
| Main outcome excluding Buffalo | 0.7237 | 0.7472 | 0.6871 |

These checks did not show a consistent advantage for environmental models. In particular, the background-only model performed better at both 25 and 100 metres. Scores across different radii should not be treated as directly comparable measures of model quality, because changing the radius changes the outcome and the proportion of sites with recorded crime. The high score at 100 metres therefore does not establish better prediction of actual ATM attacks.

We also inspected performance separately by city. The combined test is dominated by New York City, which contributes 1,160 of the 1,241 test sites. Buffalo has only 50 test sites with 14 positive outcomes, and Rochester has 31 with eight positive outcomes. For the environmental logistic model, average precision was 0.7517 in New York City, 0.3476 in Buffalo and 0.3367 in Rochester. Rochester's ROC-AUC was below 0.5 for all three models in this evaluation. These small-city results limit any claim that the pooled performance represents reliable prediction across all three cities.

We next asked whether models could predict in a city excluded from training. We trained on 2024 records from the other two cities and tested on the excluded city's 2025 records. Across the combined city-held-out predictions, average precision was 0.4077 for background-only logistic regression, 0.4929 for environmental logistic regression and 0.5095 for boosted trees. Although the environmental models improved ranking relative to that baseline, their pooled scores remained below the overall positive-outcome proportion of approximately 0.543. Probability accuracy was also poor: the corresponding Brier scores were 0.4410, 0.5074 and 0.3546. In addition, predicting New York City from the other two cities meant training on only 72 earlier-year sites. We therefore do not interpret this relative improvement as evidence of strong or well-calibrated city transfer.

We then examined whether a small amount of local data could make transfer more useful. For each target city, we compared training on all available earlier local data, training on either other city alone, training on both other cities together, and combining those outside-city records with 10% or 25% of the eligible earlier local records. Each combined model had a local-only control trained on **exactly the same selected local records**. This allowed us to distinguish a benefit from adding outside-city information from a benefit caused simply by having more local labels.

We repeated the local sampling with 20 fixed random seeds, kept the same held-out 2025 sites for every comparison, and maintained the 1,500-metre separation. Model settings were fixed in advance for these comparisons rather than tuned against the target test outcomes. The transfer experiments involved **7,380 model evaluations, 7,155 unique saved fits and 610,572 held-out prediction rows**. These are repeated evaluations of the same test sites, not additional independent observations. In 267 unique fits, the small training sample contained only one outcome class; those fits were explicitly recorded and predicted their observed training prevalence. No test labels were used to correct these samples.

The transfer results were mixed. The table below shows the mean change in average precision from adding both outside cities to the same 25% local-data sample, compared with using that local sample alone:

| Target city | Background-only logistic regression | Environmental logistic regression | Boosted trees |
|---|---:|---:|---:|
| New York City | +0.0055 | −0.0028 | +0.0082 |
| Buffalo | −0.0063 | −0.0023 | +0.0341 |
| Rochester | −0.0727 | −0.1132 | +0.0634 |

Positive values mean outside-city data helped the matched local-only model; negative values mean they harmed it. For example, pooled outside-city data improved Rochester's boosted-tree model by 0.0634 on average, but reduced its environmental logistic model by 0.1132. Source choice also mattered: using New York City data with 10% local Buffalo labels improved the boosted-tree model by 0.1006 on average and improved it in all 20 sampled comparisons, whereas adding Rochester data to that Buffalo model gave a mean change of −0.0008. These are descriptive findings from repeated local-label samples. The reported seed percentiles are not confidence intervals, and the repeated comparisons do not provide independent new test sets.

Finally, we checked the computational results against the saved data and models. The future-year and city-held-out comparisons produced 141 saved outer model fits and 44,376 predictions across the main analysis and alternative definitions. We verified split membership, year separation, geographic separation, training-only preprocessing and reproduction of their saved probabilities. For the transfer experiments, we checked every saved unique model, every matched local sample, all prediction vectors and the calculations of transfer gains and losses. The automated checks passed. We preserved the source records, data definitions, exclusions, model settings, fitted models, prediction files and instructions needed to reproduce the analysis.

Several issues still require research review. Monthly ATM membership does not prove uninterrupted operation, and allowing up to 50 metres of coordinate movement is substantial relative to the main crime buffer. Buffalo's rounded/block-level crime coordinates may be too coarse for precise 50-metre attribution. City boundaries can truncate the surrounding-crime counts, and the police extracts are later-retrieved revisions rather than databases frozen at the historical prediction dates. Both outcome years were examined earlier in the project, so this is retrospective evaluation, not an untouched confirmatory test. Independent review of the crime definitions, geographic matches, ATM continuity and environmental variables is still pending. We have also not established stable effects for individual environmental factors or completed any ATM-placement recommendation.

The evidence so far supports a narrower claim than general improvement or reliable transfer. **Surrounding crime provides a useful baseline in the pooled, spatially separated future-year test; adding environmental information gives uncertain additional value; and outside-city training data can help or harm depending on the city, model and available local labels.** The next priorities are to resolve the location and historical-membership concerns, strengthen the evidence from the smaller cities, and evaluate the approach on a genuinely uninspected later period before making stronger predictive or practical claims.
