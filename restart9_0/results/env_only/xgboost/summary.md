# XGBoost, environment only (no past crime) — exploratory, amendment A5

Same features, designs and Chicago draws as A4. Chance: AUC 0.50; AP 0.410 (Chicago), 0.330 (LA).

| training | test city | model | AUC [95% CI] | AP [95% CI] | top-10% hit rate |
|---|---|---|---|---|---|
| 1 NYC only | Chicago | LightGBM | 0.565 [0.483, 0.658] | 0.505 [0.414, 0.648] | 57% |
| 1 NYC only | Chicago | Logistic | 0.638 [0.551, 0.736] | 0.550 [0.485, 0.717] | 62% |
| 1 NYC only | Chicago | XGBoost | 0.583 [0.509, 0.668] | 0.509 [0.426, 0.641] | 62% |
| 1 NYC only | Los Angeles | LightGBM | 0.528 [0.377, 0.642] | 0.351 [0.213, 0.486] | 18% |
| 1 NYC only | Los Angeles | Logistic | 0.594 [0.476, 0.687] | 0.409 [0.262, 0.566] | 64% |
| 1 NYC only | Los Angeles | XGBoost | 0.581 [0.410, 0.702] | 0.388 [0.233, 0.540] | 27% |
| 2 NYC + 10% Chicago 2024 (draw-averaged) | Chicago | LightGBM | 0.582 [0.499, 0.674] | 0.522 [0.425, 0.659] | 62% |
| 2 NYC + 10% Chicago 2024 (draw-averaged) | Chicago | Logistic | 0.636 [0.549, 0.733] | 0.558 [0.487, 0.718] | 67% |
| 2 NYC + 10% Chicago 2024 (draw-averaged) | Chicago | XGBoost | 0.588 [0.510, 0.679] | 0.524 [0.436, 0.666] | 62% |

XGBoost per-draw spread (20 draws): AUC 0.586 (range 0.553–0.618), AP 0.522 (range 0.501–0.541).

## XGBoost weightage (% of total gain)

| attribute | Step 1 NYC only | Step 2 NYC + 10% Chicago | direction (Step 1) |
|---|---|---|---|
| Distance to rail/subway station | 16.1% | 17.5% | higher value -> less risk |
| ATM age (years mapped) | 12.1% | 12.2% | higher value -> more risk |
| Late-night places within 250 m | 11.2% | 12.8% | higher value -> more risk |
| 24/7 places within 250 m | 11.1% | 12.1% | higher value -> more risk |
| Distance to police station | 10.3% | 9.7% | higher value -> less risk |
| Distance to nearest bar | 9.3% | 8.5% | higher value -> more risk |
| Distance to highway | 8.6% | 7.4% | higher value -> less risk |
| Distance to nearest liquor store | 8.2% | 8.6% | higher value -> less risk |
| Bank-branch age | 6.2% | 4.7% | mixed / none |
| Streetlight outages within 100 m (311) | 3.4% | 3.6% | higher value -> more risk |
| Bars within 250 m | 1.4% | 1.1% | higher value -> less risk |
| Liquor stores within 250 m | 1.2% | 1.1% | higher value -> more risk |
| Open at weekends | 0.3% | 0.3% | higher value -> more risk |
| Branch hours listed | 0.3% | 0.3% | higher value -> more risk |
| Open late | 0.2% | 0.1% | higher value -> more risk |
