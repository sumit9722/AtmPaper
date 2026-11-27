# Ranked 2025 predictions (frozen Restart 9 run)

Outcome: any robbery or burglary within 50 m of the ATM in 2025. Main score = past-crime logistic model (best on the test). Chicago and LA scores come from a model trained only on NYC 2024. NYC scores come from the pooled design, with nearby training sites removed. Scores rank ATMs; NYC-trained probabilities run high for other cities (NYC base rate 63%), so read them as ranks.

| city | ATMs | actual rate | top-10% hit rate (past crime) | top-10% hit rate (LightGBM + attributes) | bottom-50% hit rate (past crime) |
|---|---|---|---|---|---|
| Chicago | 212 | 41% | 100% (21 ATMs) | 86% | 21% |
| Los Angeles | 112 | 33% | 100% (11 ATMs) | 91% | 11% |
| New York City | 611 | 56% | 97% (61 ATMs) | 89% | 37% |
