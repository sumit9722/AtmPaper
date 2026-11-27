# Environment only + population density, housing density, public transport — exploratory, amendment A6

E15 = the 15 Restart 9 attributes (A4/A5). E19 = E15 + population density, housing density, transit service frequency, distance to transit stop. E4 = those 4 only. No past-crime inputs. Chance: AUC 0.50; AP 0.410 (Chicago), 0.330 (LA).

## 1 NYC only → Chicago 2025

| model | E15 AUC | E19 AUC [95% CI] | E4 AUC [95% CI] | E19 AP | E4 AP | E19 top-10% |
|---|---|---|---|---|---|---|
| Logistic | 0.638 | 0.667 [0.571, 0.779] | 0.631 [0.532, 0.750] | 0.552 | 0.500 | 67% |
| LightGBM | 0.565 | 0.625 [0.539, 0.729] | 0.624 [0.526, 0.737] | 0.523 | 0.485 | 57% |
| XGBoost | 0.583 | 0.638 [0.551, 0.742] | 0.645 [0.546, 0.754] | 0.521 | 0.514 | 52% |

## 2 NYC + 10% Chicago 2024 (draw-averaged) → Chicago 2025

| model | E15 AUC | E19 AUC [95% CI] | E4 AUC [95% CI] | E19 AP | E4 AP | E19 top-10% |
|---|---|---|---|---|---|---|
| Logistic | 0.636 | 0.667 [0.572, 0.778] | 0.636 [0.535, 0.756] | 0.556 | 0.503 | 67% |
| LightGBM | 0.582 | 0.657 [0.570, 0.766] | 0.635 [0.536, 0.746] | 0.545 | 0.499 | 57% |
| XGBoost | 0.588 | 0.646 [0.557, 0.755] | 0.655 [0.557, 0.760] | 0.527 | 0.534 | 57% |

## 1 NYC only → Los Angeles 2025

| model | E15 AUC | E19 AUC [95% CI] | E4 AUC [95% CI] | E19 AP | E4 AP | E19 top-10% |
|---|---|---|---|---|---|---|
| Logistic | 0.594 | 0.662 [0.542, 0.758] | 0.639 [0.511, 0.748] | 0.450 | 0.399 | 55% |
| LightGBM | 0.528 | 0.544 [0.408, 0.642] | 0.527 [0.394, 0.635] | 0.348 | 0.344 | 18% |
| XGBoost | 0.581 | 0.568 [0.427, 0.670] | 0.564 [0.441, 0.665] | 0.353 | 0.354 | 18% |

## Weightage with E19 (% of total gain, NYC only)

| attribute | LightGBM | XGBoost | direction (LightGBM) |
|---|---|---|---|
| Distance to rail/subway station | 17.7% | 16.5% | higher value -> less risk |
| 24/7 places within 250 m | 12.4% | 9.8% | higher value -> more risk |
| Late-night places within 250 m | 12.2% | 15.0% | higher value -> more risk |
| Population density | 11.7% | 10.6% | higher value -> more risk |
| ATM age (years mapped) | 9.1% | 8.8% | higher value -> more risk |
| Distance to transit stop | 8.6% | 9.6% | mixed / none |
| Transit service frequency | 7.7% | 11.9% | higher value -> more risk |
| Distance to police station | 5.9% | 4.1% | higher value -> less risk |
| Distance to nearest bar | 4.3% | 3.8% | higher value -> more risk |
| Distance to nearest liquor store | 3.8% | 4.6% | higher value -> less risk |
| Housing density | 2.5% | 1.0% | higher value -> less risk |
| Bank-branch age | 1.9% | 0.3% | mixed / none |
| Distance to highway | 1.6% | 2.9% | higher value -> less risk |
| Bars within 250 m | 0.3% | 0.2% | higher value -> less risk |
| Streetlight outages within 100 m (311) | 0.2% | 0.6% | higher value -> more risk |
| Branch hours listed | 0.0% | 0.0% | mixed / none |
| Liquor stores within 250 m | 0.0% | 0.2% | mixed / none |
| Open late | 0.0% | 0.0% | mixed / none |
| Open at weekends | 0.0% | 0.0% | mixed / none |
