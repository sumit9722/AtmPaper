## Research update: Predicting crime near ATMs and learning across cities

**Progress as of 19 October 2026**

### Research questions and main findings

We have completed an extended analysis of ATM locations in New York City, Buffalo and Rochester using 2024 and 2025 records. We asked whether housing, environmental characteristics or previous crime near the same location improve prediction beyond the surrounding area's crime level, and whether data from other cities help when local training data are limited.

The clearest improvement came from **previous-year robbery and burglary within 50 metres of the ATM**. Adding this information increased average precision from 0.7195 to 0.8254 in the main future-year comparison, with an uncertainty interval supporting a positive improvement. Outside-city data also helped in some settings: nine of 54 comparisons met the stated statistical support criteria. These findings remain exploratory because both outcome years had already been examined during earlier work.

### What the data measure

The outcome is whether at least one police-recorded robbery or burglary occurred within 50 metres of an ATM during the year. This measures **crime near ATM sites**, not confirmed attacks on the machines. Fraud and other financial offences are outside this outcome.

The dataset combines the New York State Department of Financial Services inventory of bank-owned/in-bank ATMs, municipal police records and Census city boundaries. Locations were assigned to cities using coordinates and boundaries; exact duplicate ATM records were removed, and each qualifying police case was counted once within a site's neighborhood. The inventory does not represent all independent nonbank ATMs. Nearby sites can share the same incident, so their outcomes are not independent.

Historical membership was reconstructed from 14 monthly snapshots bracketing each year. Because listed ATM coordinates changed, requiring identical coordinates throughout 2024 excluded every site. We instead retained addresses appearing uniquely in every snapshot, provided all listed positions remained within 50 metres of the preceding December position. The same rule was applied to both years, with that December position used for analysis. This supports inferred membership continuity, but does not establish uninterrupted operation.

| City | ATM sites, 2024 | Sites with nearby crime, 2024 | ATM sites, 2025 | Sites with nearby crime, 2025 |
|---|---:|---:|---:|---:|
| New York City | 1,129 | 662 | 1,160 | 652 |
| Buffalo | 48 | 16 | 50 | 14 |
| Rochester | 24 | 6 | 31 | 8 |
| **Total** | **1,201** | **684** | **1,241** | **674** |

The 2,442 records represent annual observations, not distinct machines: a location can appear in both years. We reused the archived source data and checked their integrity; this analysis did not involve new downloads.

### Information considered for prediction

The baseline uses previous-year robbery and burglary more than 200 metres and up to 500 metres from each ATM. It represents the surrounding neighborhood's crime level while excluding the immediate outcome area.

We considered 27 possible additions to this baseline. Eight describe housing conditions, including vacancy, renting, multifamily housing, crowding, vehicle availability, rents, housing age and recent residential moves. Thirteen describe population, income, unemployment, employment, roads, transit, accessibility and nearby ATMs. These use common definitions across cities, drawing on 2018–2022 American Community Survey estimates, the EPA Smart Location Database released in 2021, and historical ATM inventories. Neighborhood measures should not be interpreted as direct observations of conditions at each machine.

The six remaining predictors describe previous-year crime close to the ATM: combined robbery/burglary counts within 25, 50 and 100 metres; robbery and burglary separately within 50 metres; and July–December incidents within 50 metres. Counts were transformed to reduce the influence of unusually large values. Only incidents occurring in the preceding year and reported before the prediction year were eligible. The counts were reconstructed independently using direct geographic distances for every annual site record.

Missing environmental information was retained and replaced using values estimated from the relevant training sample. Neither missing-value replacement nor variable selection used the later-year test outcomes.

### How the comparison was conducted

We trained on 2024 outcomes and evaluated predictions against 2025 outcomes. Training outcomes included only crimes reported before January 2025. Test locations were divided into five geographic groups, and training sites within 1,500 metres of the group being evaluated were excluded. This reduces the risk of reporting optimistic performance because neighboring training and test sites share local information.

We compared background-only logistic regression with a logistic model allowed to add one predictor, and a shallow boosted-tree model using the same selected inputs. Logistic regression estimates an outcome probability; boosted trees combine small decision trees to allow more flexible relationships. The expanded logistic model also limits extreme fitted coefficients to stabilize estimates.

For each training sample, the additional predictor was selected through separate geographic comparisons within 2024, again applying the 1,500-metre separation. Background alone remained an option. Selection was repeated whenever the available training records changed, including when only a small local sample was supplied. Thus, the added predictor was not chosen by comparing performance on 2025 outcomes.

Our main measure, **average precision**, summarizes how well sites with observed crime are ranked across prediction thresholds. It is not classification accuracy: 0.8254 does not mean 82.54% of sites were classified correctly. We also assessed ROC-AUC, another ranking measure, and the Brier score, which measures probability error and is better when lower. The proportion of test sites with recorded crime was 54.3%, providing a reference for interpreting average precision.

### Main prediction results

Previous-year crime within 50 metres was selected in all five geographic training comparisons, ahead of the housing and environmental alternatives. The combined 2025 results were:

| Model | Average precision ↑ | ROC-AUC ↑ | Brier score ↓ |
|---|---:|---:|---:|
| Surrounding crime only, logistic regression | 0.7195 | 0.7242 | 0.2112 |
| Surrounding crime + prior-year crime within 50 metres, logistic regression | **0.8254** | **0.7919** | **0.1868** |
| Same two crime measures, boosted trees | 0.8124 | 0.7748 | 0.1917 |

The main logistic model improved average precision by **0.1059**, with a paired 95% uncertainty interval of **+0.0652 to +0.1336**. This exceeded the stated requirement of at least 0.01 improvement with an interval entirely above zero. The interval used 2,000 repeated samples of geographic blocks, comparing both models on the same sampled locations. Ranking and probability error also improved. Among the highest-ranked 10% of sites, 94.4% had recorded nearby crime, compared with 76.8% under the baseline; this does not mean that the model captured 94.4% of all affected sites.

These results support the predictive value of repeated nearby crime. They do not establish a housing effect or show that environmental factors are irrelevant. The analysis tested one additional variable at a time, rather than every possible combination. Earlier checks using different crime radii and incident assignments were not repeated for this expanded model, so the present conclusion concerns the fixed 50-metre outcome.

### Differences between cities

| City | Background-only average precision | Selected logistic model | Test sites |
|---|---:|---:|---:|
| New York City | 0.7264 | 0.8328 | 1,160 |
| Buffalo | 0.2996 | 0.6967 | 50 |
| Rochester | 0.2221 | 0.4309 | 31 |

The selected logistic model improved ranking in all three cities, but the combined result is dominated by New York City. Buffalo had only 14 affected test sites and Rochester eight. Their estimates are therefore less stable, and these city-specific comparisons should be treated as supporting description rather than separate confirmatory findings.

We also trained using only the other two cities and predicted the excluded city's later-year outcomes. Combined average precision increased from 0.4077 for background-only logistic regression to 0.6314 for the selected logistic model. However, its ROC-AUC was only 0.5124 and its Brier score was 0.3398. Predicting New York City from Buffalo and Rochester also meant starting with only 72 earlier-year sites. Improved average precision alone therefore does not establish dependable prediction in a new city.

### Can outside-city data help when local data are scarce?

For each city, we compared models trained on all eligible earlier local records, either other city, both other cities, and outside-city records combined with 10% or 25% of eligible local records. Every combined model was compared against a local-only model receiving **exactly the same local records**. The 10% sample was contained within the corresponding 25% sample. We repeated sampling 20 times while retaining the same later-year test sites and geographic separation.

The experiment produced 7,380 model evaluations and 610,572 predictions, representing repeated evaluation of the same 1,241 test sites. We summarized the mean change in average precision across the 20 local samples. Uncertainty calculations resampled geographic blocks jointly across those comparisons; the 20 samples were not treated as independent test populations.

Statistical support required an average improvement of at least 0.01, a 95% interval entirely above zero, and an adjusted p-value below 0.05. We used 9,999 random exchanges of paired predictions by geographic block, then applied Holm's correction across all 54 comparisons to account for testing multiple conditions. **Nine comparisons met all three requirements.** Selected logistic-model examples are:

| City being predicted | Additional data from | Local records used | Mean average-precision gain | 95% interval |
|---|---|---:|---:|---:|
| New York City | Rochester | 10% | +0.0318 | +0.0199 to +0.0416 |
| New York City | Rochester | 25% | +0.0159 | +0.0082 to +0.0227 |
| Buffalo | New York City | 10% | +0.3960 | +0.2562 to +0.5678 |
| Buffalo | New York City | 25% | +0.3998 | +0.2524 to +0.5666 |

Combining both outside cities gave almost identical supported logistic-model gains for Buffalo at both sampling levels. The other three supported comparisons involved boosted trees predicting New York City: Rochester data at both sampling levels, and combined outside-city data with 10% local records.

None of the comparisons predicting Rochester met the complete support rule. Several had positive average gains or intervals, but did not remain supported after the adjusted randomization test. Outside-city data also reduced performance in some settings, particularly for background-only models. Buffalo's large gains are relative to models trained on very small local samples; they should not be interpreted as improvements of the same size over a model using all available local data.

### Verification, limitations and next steps

Automated checks passed for the source-file integrity, training and test membership, year and geographic separation, variable selection, matched local samples and reported statistics. All 7,155 unique saved transfer models reproduced their stored predictions exactly. Small training samples containing only one outcome class occurred in 267 fits; these were explicitly recorded and assigned that sample's observed outcome rate. Source records, fitted models, predictions and reproduction instructions have been retained.

Important limitations remain. Monthly inventory continuity does not prove uninterrupted ATM operation, and the permitted coordinate movement is substantial relative to the 50-metre outcome radius. Buffalo's rounded crime coordinates may be too coarse for precise attribution. Nearby ATMs can share incidents, city boundaries can truncate surrounding-crime counts, and archived police extracts may include later revisions. Independent review of crime definitions, locations, historical membership and geographic matching is still pending.

The statistical intervals and tests describe uncertainty in the saved predictions; they do not include uncertainty from repeating the entire model-building process or earlier research choices. The randomization test also assumes that paired predictions can be exchanged within geographic blocks under the hypothesis of no transfer benefit. Because both outcome years were previously inspected, the findings are exploratory despite the positive statistical results.

The current evidence supports previous-year crime near an ATM as a useful addition to broader neighborhood crime information. It also identifies specific settings where outside-city data may help, without establishing a general transfer benefit. The next priorities are independent data review, stronger evidence from the smaller cities, and evaluation on an untouched later period before making practical ATM-location or security recommendations.
