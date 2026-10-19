## Research update: An initial test of geographic transferability using a simple crime predictor

**Progress as of 19 October 2026**

We have completed an initial geographic transferability analysis using ATM locations in New York City, Buffalo and Rochester. For this stage, we used a substantively trivial predictor—previous-year robbery and burglary within 50 metres of an ATM—as a simple starting point for checking whether a predictive relationship learned in one city can be useful in another. It is unsurprising that places with previous crime tend to experience crime again. The research interest at this stage is whether models using that information remain useful across cities, particularly when little local training data are available.

This distinction changes how we interpret the results. Better prediction after adding nearby crime establishes a useful benchmark. Evidence of geographic transferability comes from the separate experiments that train on other cities and test whether adding those records improves prediction over a model given the same limited local data.

### What we predicted

The outcome was whether at least one police-recorded robbery or burglary occurred within 50 metres of an ATM during the prediction year. It measures crime near an ATM location; the records do not establish that the ATM itself was targeted.

We trained models on 2024 outcomes and evaluated them on 2025 outcomes. The analysis included 1,201 ATM sites in 2024 and 1,241 in 2025. The 2025 test set contained 1,160 sites in New York City, 50 in Buffalo and 31 in Rochester, of which 652, 14 and eight respectively had recorded nearby crime. These are annual site observations, so a location can appear in both years.

The inventory covers bank-owned/in-bank ATMs. Historical membership was inferred from monthly records using stable addresses and a maximum permitted coordinate movement of 50 metres. This does not establish uninterrupted operation or cover all independent nonbank ATMs.

### Why use such a simple variable?

Previous-year crime within the same small area provides an intuitive benchmark for a first transferability check. Before asking whether less obvious housing or environmental variables transfer, we can ask whether even this basic crime-persistence signal supports useful prediction across different cities. Its simplicity makes the interpretation straightforward: any improvement from adding outside-city training records concerns the usefulness of those records for prediction, rather than the novelty of the variable itself.

The predictor uses **crime from the preceding year**, with reports required to be available before the prediction year. It therefore does not reuse the prediction year's outcome as an input. The baseline already includes previous-year crime in the surrounding 200–500-metre ring; the added variable describes crime in the immediate 50-metre area.

The actual analysis compared 27 possible additions, including housing, environmental and nearby-crime variables. Previous-year robbery/burglary within 50 metres was selected in all five main geographic training comparisons. Selection used only the earlier-year training data and was repeated for each distinct training sample. We therefore interpret the selected variable as a simple benchmark for this initial transferability study; it was not the only variable specified and tested from the outset. Individual transfer fits could select a different variable or retain the background-only model.

### Establishing the benchmark

In the main future-year evaluation, test sites were divided into five geographic groups. Training sites within 1,500 metres of the group being evaluated were excluded to reduce overlap between neighboring training and test locations.

| Model | Average precision ↑ | ROC-AUC ↑ | Brier score ↓ |
|---|---:|---:|---:|
| Surrounding crime only, logistic regression | 0.7195 | 0.7242 | 0.2112 |
| Surrounding crime + prior-year crime within 50 metres, logistic regression | 0.8254 | 0.7919 | 0.1868 |
| Same two crime measures, boosted trees | 0.8124 | 0.7748 | 0.1917 |

Average precision measures how well sites with recorded crime are ranked; it is not classification accuracy. The logistic model's improvement was **+0.1059**, with a paired spatial 95% uncertainty interval of **+0.0652 to +0.1336**. This is consistent with the expected persistence of nearby crime. On its own, this comparison does not demonstrate transfer to an unseen city, because the training data include records from all three cities.

### Does the model transfer between cities?

We tested two situations. First, we trained on the other two cities and predicted the excluded city's 2025 outcomes without using its local training outcomes. Combined average precision rose from 0.4077 for the background-only model to 0.6314 for the selected logistic model. However, ROC-AUC was only 0.5124 and the Brier score was 0.3398. These mixed results do not establish reliable prediction in a new city without local training data.

Second, we tested whether outside-city records help when a small local training sample is available. Models received outside-city records plus either 10% or 25% of the eligible local records. Each was compared with a local-only model receiving **exactly the same local records**. We repeated local sampling 20 times and retained the later-year test sites and geographic separation. This comparison directly asks whether adding information from another city helps under limited local data.

Of 54 source-city, local-sample and model comparisons, **nine met the exploratory support rule**: an average-precision gain of at least 0.01, a spatial 95% interval entirely above zero, and a Holm-adjusted block-randomization p-value below 0.05. Examples for the selected logistic model are:

| City being predicted | Outside-city data | Local records used | Mean average-precision gain | 95% interval |
|---|---|---:|---:|---:|
| New York City | Rochester | 10% | +0.0318 | +0.0199 to +0.0416 |
| New York City | Rochester | 25% | +0.0159 | +0.0082 to +0.0227 |
| Buffalo | New York City | 10% | +0.3960 | +0.2562 to +0.5678 |
| Buffalo | New York City | 25% | +0.3998 | +0.2524 to +0.5666 |

Combining both outside cities also produced supported logistic-model gains for Buffalo at both sampling levels. The remaining three supported comparisons used boosted trees to predict New York City. No comparison predicting Rochester met the full support rule, and adding outside-city data reduced performance in some settings. Buffalo's large gains are relative to models trained on very small local samples; they are not gains over a model trained on all available local records.

### Interpretation and next steps

The contribution of this stage is an initial, limited test of geographic transferability using a simple and expected predictive signal. The results suggest that outside-city data can help in particular source–target combinations when local data are scarce. They do not establish a general transfer benefit, a new explanation of ATM-related crime, or an independent housing or environmental effect.

The findings remain exploratory because both outcome years had been inspected in earlier work. New York City dominates the combined results, and Buffalo and Rochester have small test samples. Rounded crime coordinates, uncertain ATM continuity, shared incidents between nearby sites and retrospective police-record revisions also limit interpretation. The uncertainty calculations condition on the fitted predictions and do not capture all uncertainty from model development or earlier research choices. Automated validation passed; independent source and geographic-linkage review remains pending.

The next step is to evaluate transfer on an untouched later period and obtain stronger evidence from the smaller cities. A further analysis can then test whether housing and environmental variables add useful, transferable information beyond the simple nearby-crime benchmark. This would separate the initial question—whether an obvious predictive signal can be used across cities—from the harder question of whether less trivial variables provide additional value.

<!-- Supporting details: [methods](reports/methods.md), [main prediction results](results/phase4/docs/03_results.md), and [all transfer comparisons](results/phase5/docs/03_results.md). -->
