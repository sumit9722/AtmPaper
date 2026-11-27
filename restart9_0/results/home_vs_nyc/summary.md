# Chicago-trained vs NYC-trained, same Chicago 2025 test (exploratory, amendment A7)

Test: Restart 7 core Chicago 2025, 212 ATMs, 87 with robbery/burglary within 50 m (chance AP 0.410, AUC 0.500). 180 of 212 test ATMs also appear in Chicago 2024 training. XGBoost uses the teammate's draft/xgboost_model method; logistic uses the Restart 9 pipeline. CRIME = prior-year crime within 50 m and 200–500 m.

## XGBoost

| features | trained on | AUC [95% CI] | AP [95% CI] |
|---|---|---|---|
| CRIME | Chicago 2024 | 0.773 [0.693, 0.848] | 0.665 [0.540, 0.790] |
| CRIME | Chicago 2024, purged | 0.729 [0.649, 0.811] | 0.639 [0.533, 0.778] |
| CRIME | NYC 2024 | 0.781 [0.716, 0.857] | 0.745 [0.657, 0.829] |
| E19 | Chicago 2024 | 0.682 [0.590, 0.788] | 0.572 [0.487, 0.696] |
| E19 | Chicago 2024, purged | 0.547 [0.461, 0.656] | 0.480 [0.378, 0.661] |
| E19 | NYC 2024 | 0.633 [0.548, 0.730] | 0.525 [0.457, 0.689] |
| E107 | Chicago 2024 | 0.705 [0.611, 0.814] | 0.577 [0.488, 0.731] |
| E107 | Chicago 2024, purged | 0.492 [0.401, 0.608] | 0.434 [0.341, 0.595] |
| E107 | NYC 2024 | 0.585 [0.487, 0.711] | 0.485 [0.386, 0.638] |
| CRIME+E19 | Chicago 2024 | 0.792 [0.722, 0.870] | 0.663 [0.574, 0.777] |
| CRIME+E19 | Chicago 2024, purged | 0.757 [0.689, 0.834] | 0.638 [0.541, 0.785] |
| CRIME+E19 | NYC 2024 | 0.780 [0.723, 0.853] | 0.737 [0.681, 0.820] |
| CRIME+E107 | Chicago 2024 | 0.781 [0.708, 0.860] | 0.670 [0.572, 0.777] |
| CRIME+E107 | Chicago 2024, purged | 0.678 [0.604, 0.771] | 0.593 [0.495, 0.733] |
| CRIME+E107 | NYC 2024 | 0.792 [0.727, 0.868] | 0.703 [0.605, 0.824] |

## Logistic

| features | trained on | AUC [95% CI] | AP [95% CI] |
|---|---|---|---|
| CRIME | Chicago 2024 | 0.804 [0.741, 0.873] | 0.772 [0.692, 0.848] |
| CRIME | Chicago 2024, purged | 0.634 [0.543, 0.738] | 0.568 [0.452, 0.734] |
| CRIME | NYC 2024 | 0.793 [0.731, 0.865] | 0.764 [0.688, 0.840] |
| E19 | Chicago 2024 | 0.689 [0.602, 0.786] | 0.618 [0.532, 0.726] |
| E19 | Chicago 2024, purged | 0.618 [0.510, 0.737] | 0.548 [0.409, 0.709] |
| E19 | NYC 2024 | 0.667 [0.571, 0.779] | 0.552 [0.490, 0.726] |
| E107 | Chicago 2024 | 0.697 [0.608, 0.798] | 0.591 [0.507, 0.709] |
| E107 | Chicago 2024, purged | 0.563 [0.463, 0.668] | 0.439 [0.343, 0.566] |
| E107 | NYC 2024 | 0.636 [0.548, 0.747] | 0.491 [0.432, 0.674] |
| CRIME+E19 | Chicago 2024 | 0.765 [0.698, 0.853] | 0.702 [0.613, 0.796] |
| CRIME+E19 | Chicago 2024, purged | 0.756 [0.677, 0.843] | 0.616 [0.506, 0.772] |
| CRIME+E19 | NYC 2024 | 0.765 [0.692, 0.863] | 0.698 [0.632, 0.826] |
| CRIME+E107 | Chicago 2024 | 0.753 [0.678, 0.845] | 0.666 [0.588, 0.769] |
| CRIME+E107 | Chicago 2024, purged | 0.621 [0.533, 0.738] | 0.486 [0.376, 0.662] |
| CRIME+E107 | NYC 2024 | 0.746 [0.656, 0.851] | 0.599 [0.550, 0.799] |

## Home advantage: Chicago-trained minus NYC-trained (paired, 2 km block bootstrap)

| learner | Chicago training | features | AUC difference [95% CI] | AP difference [95% CI] |
|---|---|---|---|---|
| XGBoost | Chicago 2024 | CRIME | -0.007 [-0.046, +0.033] | -0.080 [-0.157, -0.005] |
| XGBoost | Chicago 2024, purged | CRIME | -0.052 [-0.121, +0.014] | -0.106 [-0.171, -0.020] |
| Logistic | Chicago 2024 | CRIME | +0.010 [-0.003, +0.024] | +0.008 [-0.005, +0.023] |
| Logistic | Chicago 2024, purged | CRIME | -0.159 [-0.256, -0.049] | -0.196 [-0.276, -0.068] |
| XGBoost | Chicago 2024 | E19 | +0.049 [-0.036, +0.145] | +0.047 [-0.057, +0.115] |
| XGBoost | Chicago 2024, purged | E19 | -0.086 [-0.186, +0.022] | -0.045 [-0.171, +0.081] |
| Logistic | Chicago 2024 | E19 | +0.022 [-0.048, +0.075] | +0.065 [-0.044, +0.109] |
| Logistic | Chicago 2024, purged | E19 | -0.049 [-0.149, +0.043] | -0.004 [-0.147, +0.093] |
| XGBoost | Chicago 2024 | E107 | +0.120 [+0.053, +0.199] | +0.091 [+0.019, +0.183] |
| XGBoost | Chicago 2024, purged | E107 | -0.093 [-0.252, +0.056] | -0.052 [-0.164, +0.064] |
| Logistic | Chicago 2024 | E107 | +0.061 [-0.004, +0.120] | +0.099 [-0.017, +0.161] |
| Logistic | Chicago 2024, purged | E107 | -0.072 [-0.190, +0.024] | -0.052 [-0.206, +0.041] |
| XGBoost | Chicago 2024 | CRIME+E19 | +0.012 [-0.039, +0.055] | -0.073 [-0.149, +0.008] |
| XGBoost | Chicago 2024, purged | CRIME+E19 | -0.023 [-0.088, +0.037] | -0.098 [-0.171, +0.005] |
| Logistic | Chicago 2024 | CRIME+E19 | -0.001 [-0.053, +0.043] | +0.004 [-0.110, +0.061] |
| Logistic | Chicago 2024, purged | CRIME+E19 | -0.009 [-0.091, +0.070] | -0.082 [-0.202, +0.040] |
| XGBoost | Chicago 2024 | CRIME+E107 | -0.011 [-0.053, +0.026] | -0.033 [-0.127, +0.037] |
| XGBoost | Chicago 2024, purged | CRIME+E107 | -0.114 [-0.192, -0.027] | -0.110 [-0.200, -0.016] |
| Logistic | Chicago 2024 | CRIME+E107 | +0.007 [-0.042, +0.056] | +0.067 [-0.072, +0.135] |
| Logistic | Chicago 2024, purged | CRIME+E107 | -0.124 [-0.241, -0.015] | -0.113 [-0.292, +0.014] |
