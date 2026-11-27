# Environment-only prediction (no past-crime inputs) — exploratory, amendment A4

Features: the 15 Restart 9 situational attributes only. Outcome: any robbery/burglary within 50 m in 2025. Reference is chance: AUC 0.50 and AP equal to the share of test ATMs with crime.

| training | test city | model | AP [95% CI] | chance AP | ROC-AUC [95% CI] | top-10% hit rate |
|---|---|---|---|---|---|---|
| 1 NYC only | Chicago | LightGBM | 0.505 [0.414, 0.648] | 0.410 | 0.565 [0.483, 0.658] | 57% |
| 1 NYC only | Los Angeles | LightGBM | 0.351 [0.213, 0.486] | 0.330 | 0.528 [0.377, 0.643] | 18% |
| 1 NYC only | Chicago | Logistic | 0.550 [0.486, 0.717] | 0.410 | 0.638 [0.551, 0.736] | 62% |
| 1 NYC only | Los Angeles | Logistic | 0.409 [0.262, 0.566] | 0.330 | 0.594 [0.476, 0.687] | 64% |
| 2 NYC + 10% Chicago 2024 (draw-averaged) | Chicago | LightGBM | 0.522 [0.425, 0.659] | 0.410 | 0.582 [0.499, 0.674] | 62% |
| 2 NYC + 10% Chicago 2024 (draw-averaged) | Chicago | Logistic | 0.558 [0.487, 0.718] | 0.410 | 0.636 [0.549, 0.733] | 67% |

Step 2 per-draw spread (20 draws of 19 Chicago 2024 site-years):

* LightGBM: AP 0.520 (range 0.494–0.541), AUC 0.580 (range 0.552–0.598)
* Logistic: AP 0.555 (range 0.543–0.569), AUC 0.634 (range 0.622–0.652)

## LightGBM weightage (% of total gain)

| attribute | Step 1 NYC only | Step 2 NYC + 10% Chicago | direction (Step 1) |
|---|---|---|---|
| Distance to rail/subway station | 16.8% | 18.9% | higher value -> less risk |
| Late-night places within 250 m | 13.9% | 14.4% | higher value -> more risk |
| ATM age (years mapped) | 13.5% | 12.1% | higher value -> more risk |
| Distance to police station | 11.8% | 9.1% | higher value -> less risk |
| Distance to nearest bar | 9.8% | 8.8% | higher value -> more risk |
| 24/7 places within 250 m | 9.6% | 13.3% | higher value -> more risk |
| Distance to nearest liquor store | 8.4% | 9.2% | higher value -> less risk |
| Distance to highway | 7.9% | 6.5% | higher value -> less risk |
| Bank-branch age | 3.6% | 3.3% | mixed / none |
| Streetlight outages within 100 m (311) | 2.0% | 2.7% | higher value -> more risk |
| Bars within 250 m | 1.4% | 0.7% | higher value -> less risk |
| Liquor stores within 250 m | 0.9% | 0.5% | higher value -> less risk |
| Branch hours listed | 0.2% | 0.2% | higher value -> more risk |
| Open at weekends | 0.2% | 0.2% | higher value -> more risk |
| Open late | 0.1% | 0.0% | higher value -> more risk |
