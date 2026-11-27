# LightGBM weightage and NYC → Chicago 2025 prediction (exploratory, amendment A3)

Outcome: any robbery/burglary within 50 m in 2025. Chicago test: 212 ATMs, 87 with crime (41%). AP = average precision (random guessing ≈ 0.41).

## Step 1 — trained on NYC 2024 only

| model | AP | ROC-AUC | Brier |
|---|---|---|---|
| LightGBM + attributes | 0.731 | 0.773 | 0.201 |
| LightGBM past crime only | 0.742 | 0.771 | 0.220 |
| Logistic past crime only (baseline) | 0.764 | 0.793 | 0.213 |

LightGBM + attributes vs baseline: -0.033 AP (95% CI -0.079 to +0.016).

## Step 2 — trained on NYC 2024 + 10% of Chicago 2024

19 Chicago 2024 site-years per draw (10% of 190), 20 random draws, 5 spatial folds. Eligible Chicago pool per fold after the 1,500 m purge: 80–157 site-years.

| model | mean AP | AP range over 20 draws | mean ROC-AUC | mean Brier |
|---|---|---|---|---|
| LightGBM + attributes | 0.722 | 0.679–0.740 | 0.763 | 0.202 |
| LightGBM past crime only | 0.735 | 0.723–0.744 | 0.766 | 0.219 |
| Logistic past crime only (baseline) | 0.764 | 0.758–0.769 | 0.794 | 0.210 |

LightGBM + attributes vs baseline: mean -0.042 AP; better in 0 of 20 draws; 95% CI of the draw-averaged gain -0.089 to +0.013.

## Weightage (% of LightGBM total gain)

| attribute | Step 1 NYC only | Step 2 NYC + 10% Chicago | effect direction (Step 1) |
|---|---|---|---|
| Past crime within 50 m (previous year) | 27.3% | 26.8% | higher value -> more risk |
| Past crime 200-500 m (previous year) | 14.3% | 12.9% | higher value -> more risk |
| Distance to rail/subway station | 13.3% | 13.4% | higher value -> less risk |
| Late-night places within 250 m | 11.8% | 9.1% | higher value -> more risk |
| ATM age (years mapped) | 7.6% | 6.7% | higher value -> more risk |
| 24/7 places within 250 m | 6.8% | 6.5% | higher value -> more risk |
| Distance to nearest liquor store | 6.6% | 8.4% | higher value -> less risk |
| Distance to police station | 5.1% | 5.2% | mixed / none |
| Distance to nearest bar | 3.2% | 3.9% | higher value -> more risk |
| Distance to highway | 1.9% | 3.5% | higher value -> less risk |
| Bank-branch age | 1.4% | 1.8% | mixed / none |
| Liquor stores within 250 m | 0.3% | 0.6% | higher value -> more risk |
| Streetlight outages within 100 m (311) | 0.3% | 0.8% | mixed / none |
| Bars within 250 m | 0.0% | 0.3% | mixed / none |
| Branch hours listed | 0.0% | 0.0% | mixed / none |
| Open late | 0.0% | 0.0% | mixed / none |
| Open at weekends | 0.0% | 0.2% | mixed / none |
