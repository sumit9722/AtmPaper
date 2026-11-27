"""Readable ranked 2025 predictions per city from the frozen Restart 9 run (no refitting).

Chicago and LA: D1 (model trained on NYC 2024). NYC: D3 (pooled, spatially purged folds).
Outcome O1: any robbery/burglary within 50 m in 2025. Main score: logistic M0 (best on test);
LightGBM M9 shown alongside. Output: results/ranked_2025/*.csv and summary.md.
"""
from pathlib import Path

import pandas as pd
import pyarrow.parquet as pq

R9 = Path(__file__).resolve().parents[1]
PROJECT = R9.parent
OUT = R9 / "results/ranked_2025"
SOURCE = {"Chicago": "D1", "Los Angeles": "D1", "New York City": "D3"}
KEY = {"New York City": "nyc", "Chicago": "chicago", "Los Angeles": "la"}


def names(city):
    f = pq.read_table(PROJECT / f"restart6_0/data/raw/osm_v2/{KEY[city]}/2024-12-15.parquet").to_pandas()
    out = {}
    for t, i, tags in zip(f.osm_type, f.osm_id, f.tags):
        tg = dict(tags)
        out[f"{t}/{i}"] = tg.get("name") or tg.get("brand") or tg.get("operator") or ""
    return out


def main():
    p = pd.read_csv(R9 / "results/predictions.csv")
    p = p[p.outcome == "O1"]
    lk = pd.read_csv(PROJECT / "restart7_0/results/phase3/data/site_lookup_and_quality.csv", dtype=str)
    oc = pd.read_csv(PROJECT / "restart7_0/results/phase3/data/outcomes.csv", usecols=["row_id", "recorded_count_50m"])
    OUT.mkdir(parents=True, exist_ok=True)
    lines = ["# Ranked 2025 predictions (frozen Restart 9 run)", "",
             "Outcome: any robbery or burglary within 50 m of the ATM in 2025. Main score = past-crime logistic model "
             "(best on the test). Chicago and LA scores come from a model trained only on NYC 2024. NYC scores come "
             "from the pooled design, with nearby training sites removed. Scores rank ATMs; NYC-trained probabilities "
             "run high for other cities (NYC base rate 63%), so read them as ranks.", "",
             "| city | ATMs | actual rate | top-10% hit rate (past crime) | top-10% hit rate (LightGBM + attributes) | bottom-50% hit rate (past crime) |",
             "|---|---|---|---|---|---|"]
    for city, design in SOURCE.items():
        g = p[(p.design == design) & (p.city == city)].merge(lk[["row_id", "osm_id", "latitude", "longitude", "osm_amenity"]], on="row_id")
        g = g.merge(oc, on="row_id")
        nm = names(city)
        g["name"] = g.osm_id.map(nm).fillna("")
        g = g.sort_values("LR-M0", ascending=False, kind="stable").reset_index(drop=True)
        g["rank_past_crime"] = range(1, len(g) + 1)
        g["rank_lgbm_attributes"] = g["LGBM-M9"].rank(ascending=False, method="first").astype(int)
        top = max(1, len(g) // 10)
        lg = g.sort_values("LGBM-M9", ascending=False).head(top)
        lines.append(f"| {city} | {len(g)} | {g.observed.mean():.0%} | {g.head(top).observed.mean():.0%} ({top} ATMs) | "
                     f"{lg.observed.mean():.0%} | {g.iloc[len(g) // 2:].observed.mean():.0%} |")
        cols = ["rank_past_crime", "name", "osm_amenity", "latitude", "longitude", "LR-M0", "rank_lgbm_attributes", "LGBM-M9",
                "observed", "recorded_count_50m", "osm_id", "row_id"]
        g[cols].rename(columns={"LR-M0": "risk_score_past_crime", "LGBM-M9": "risk_score_lgbm_attributes",
                                "observed": "actual_crime_2025", "recorded_count_50m": "actual_incidents_2025",
                                "osm_amenity": "osm_type"}).to_csv(OUT / f"{KEY[city]}_ranked_2025.csv", index=False, float_format="%.4f")
    (OUT / "summary.md").write_text("\n".join(lines) + "\n")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
