"""Frozen, bounded Phase 4 experiment using the existing Restart 7 matrices."""
import csv
import hashlib
import importlib.metadata
import json
import math
import platform
import sys
import warnings
from pathlib import Path

import joblib
import numpy as np
from pyproj import Geod, Transformer
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.exceptions import ConvergenceWarning
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import average_precision_score, roc_auc_score, brier_score_loss
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from threadpoolctl import threadpool_limits

ROOT = Path(__file__).resolve().parent
BASE = ROOT.parent
PROJECT = BASE.parent
OUT = ROOT / "results"
CITIES = ("New York City", "Chicago", "Los Angeles")
GEOD = Geod(ellps="WGS84")
CS = (0.01, 0.1, 1.0, 10.0)
SEED = 701
GROUP_FIELDS = ("object_group_id", "nearby_component_id", "acs_geoid_2022", "sld_geoid_2019")


def read(path):
    with Path(path).open(newline="", encoding="utf-8-sig") as stream:
        return list(csv.DictReader(stream))


def write(path, rows, fields=None):
    rows = list(rows)
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    fields = fields or list(rows[0])
    with Path(path).open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def save(path, data):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(json.dumps(data, indent=2, allow_nan=False) + "\n")


def sha(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1048576), b""):
            digest.update(chunk)
    return digest.hexdigest()


def hashfold(group, inner=False):
    prefix = "restart7_phase4_inner|" if inner else "restart7_phase4|"
    return int(hashlib.sha256((prefix + group).encode()).hexdigest()[:8], 16) % (3 if inner else 5)


def weighted_ap(y, scores, weights):
    """AP for many bootstrap multiplicity vectors, respecting tied scores."""
    y = np.asarray(y, dtype=float)
    scores = np.asarray(scores)
    weights = np.atleast_2d(weights)
    order = np.argsort(-scores, kind="stable")
    end = np.r_[np.flatnonzero(np.diff(scores[order]) != 0), len(y) - 1]
    total_positive = weights @ y
    results = np.full(len(weights), np.nan)
    for start in range(0, len(weights), 100):
        w = weights[start:start + 100, order]
        positives = np.cumsum(w * y[order], axis=1)[:, end]
        totals = np.cumsum(w, axis=1)[:, end]
        precision = np.divide(positives, totals, out=np.zeros_like(positives), where=totals > 0)
        increments = np.diff(np.c_[np.zeros(len(w)), positives], axis=1)
        denom = total_positive[start:start + len(w)]
        results[start:start + len(w)] = np.divide(np.sum(precision * increments, axis=1), denom,
                                                   out=np.full(len(w), np.nan), where=denom > 0)
    return results


def frozen_inputs():
    old_manifest = read(BASE / "qa/output_manifest.csv")
    for entry in old_manifest:
        path = BASE / entry["file"]
        if path.stat().st_size != int(entry["bytes"]) or sha(path) != entry["sha256"]:
            raise RuntimeError(f"Frozen phase 1–3 artifact changed: {path}")
    needed = [BASE / "results/phase3/data/feature_schema.json", BASE / "results/phase3/data/outcomes.csv",
              BASE / "results/phase3/data/site_lookup_and_quality.csv", BASE / "qa/output_manifest.csv",
              BASE / "qa/research_review_gates.csv", BASE / "qa/validation.json", ROOT / "protocol.md", ROOT / "run.py",
              ROOT / "requirements.txt"]
    needed += sorted((BASE / "results/phase3/data").glob("features_*full_year_2024_2025.csv"))
    needed += sorted((BASE / "results/phase3/data").glob("features_*core_2024_2025.csv"))
    needed += [ROOT / "test_phase4.py", ROOT / "report.py"]
    entries = [{"file": str(p.relative_to(PROJECT)), "bytes": p.stat().st_size, "sha256": sha(p)} for p in sorted(set(needed))]
    target = OUT / "input_manifest.csv"
    if target.exists() and read(target) != [{k: str(v) for k, v in r.items()} for r in entries]:
        raise RuntimeError("Frozen Phase 4 inputs/code changed; do not silently rerun a changed experiment")
    write(target, entries)
    save(OUT / "environment.json", {"python": platform.python_version(),
        "packages": {name: importlib.metadata.version(name) for name in ("numpy", "pyproj", "scikit-learn", "joblib", "threadpoolctl")}})


def prepare_scenarios():
    folder = BASE / "results/phase3/data"
    schema = json.loads((folder / "feature_schema.json").read_text())
    lookup = {r["row_id"]: r for r in read(folder / "site_lookup_and_quality.csv")}
    outcomes = {r["row_id"]: r for r in read(folder / "outcomes.csv")}
    fields = schema["primary_predictors"]
    transforms = {c: Transformer.from_crs(4326, epsg, always_xy=True) for c, epsg in zip(CITIES, (32618, 32616, 32611))}
    definitions = [("core_50m", "primary", "core_2024_2025", 50),
                   ("core_25m", "primary", "core_2024_2025", 25),
                   ("core_100m", "primary", "core_2024_2025", 100),
                   ("master_50m", "primary", "full_year_2024_2025", 50),
                   ("explicit_atm_50m", "primary", "explicit_atm_core_2024_2025", 50),
                   ("no_source_conflicts_50m", "no_source_conflicts", "core_2024_2025", 50),
                   ("report_filtered_50m", "report_filtered", "core_2024_2025", 50)]
    sensitivities = {r["row_id"]: r for r in read(folder / "features_sensitivity_core_2024_2025.csv")}
    scenarios = {}
    for name, kind, subset, radius in definitions:
        rows = read(folder / f"features_{kind}_{subset}.csv")
        rows.sort(key=lambda r: r["row_id"])
        cols = fields if kind != "report_filtered" else ["log1p_prior_local_50m_report_filtered", "log1p_prior_annulus_200_500m_report_filtered"] + schema["environment_predictors"]
        meta, x, y = [], [], []
        for row in rows:
            r = dict(lookup[row["row_id"]])
            r["outcome_year"] = int(r["outcome_year"])
            xx, yy = transforms[r["city"]].transform(float(r["longitude"]), float(r["latitude"]))
            r["spatial_block_5km"] = f"{r['city']}:{math.floor(xx / 5000)}:{math.floor(yy / 5000)}"
            values = [float(row[c]) if row[c] != "" else np.nan for c in cols]
            if radius != 50:
                values[0] = float(sensitivities[row["row_id"]][f"log1p_prior_crime_{radius}m_retrospective"])
            label = f"recorded_any_{radius}m"
            if kind == "no_source_conflicts":
                label = "no_source_conflicts_any_50m"
            if kind == "report_filtered" and r["outcome_year"] == 2024:
                label = "reported_before_next_year_any_50m"
            x.append(values)
            y.append(int(outcomes[row["row_id"]][label]))
            r["label_field"] = label
            meta.append(r)
        if radius != 50:
            cols = [f"log1p_prior_local_{radius}m_retrospective"] + cols[1:]
        scenarios[name] = {"name": name, "meta": meta, "x": np.array(x, dtype=float), "y": np.array(y), "features": cols}
    return scenarios


def distances(meta):
    n = len(meta)
    result = np.full((n, n), np.inf)
    for city in CITIES:
        indices = np.array([i for i, r in enumerate(meta) if r["city"] == city], dtype=int)
        lon = np.array([float(meta[i]["longitude"]) for i in indices])
        lat = np.array([float(meta[i]["latitude"]) for i in indices])
        for local, i in enumerate(indices):
            result[i, indices] = GEOD.inv(np.full(len(indices), lon[local]), np.full(len(indices), lat[local]), lon, lat)[2]
    return result


def purge(train, test, distance, meta):
    if not len(test):
        return np.asarray(train, dtype=int)
    mask = (distance[np.ix_(train, test)] >= 1500).all(axis=1)
    for field in GROUP_FIELDS:
        excluded = {meta[i][field] for i in test} - {""}
        mask &= np.array([meta[i][field] not in excluded for i in train])
    return np.asarray(train, dtype=int)[mask]


def class_ok(y, minimum, per_class):
    return len(y) >= minimum and np.sum(y == 0) >= per_class and np.sum(y == 1) >= per_class


def plans_for(scenario):
    meta, y = scenario["meta"], scenario["y"]
    distance = distances(meta)
    train = np.array([i for i, r in enumerate(meta) if r["outcome_year"] == 2024])
    test = np.array([i for i, r in enumerate(meta) if r["outcome_year"] == 2025])
    definitions = [("forward_spatial", str(f), test[[hashfold(meta[i]["spatial_block_2km"]) == f for i in test]], train) for f in range(5)]
    if scenario["name"] == "core_50m":
        definitions += [("forward_city_out", city, test[[meta[i]["city"] == city for i in test]],
                         train[[meta[i]["city"] != city for i in train]]) for city in CITIES]
    plans = []
    for scheme, fold, heldout, candidates in definitions:
        fitting = purge(candidates, heldout, distance, meta)
        inner = []
        for k in range(3):
            val = fitting[[hashfold(meta[i]["spatial_block_2km"], True) == k for i in fitting]]
            pool = fitting[[hashfold(meta[i]["spatial_block_2km"], True) != k for i in fitting]]
            fit = purge(pool, val, distance, meta)
            usable = class_ok(y[fit], 30, 5) and class_ok(y[val], 10, 1)
            inner.append({"fold": k, "train": fit, "validation": val, "usable": bool(usable)})
        valid = len(heldout) > 0 and class_ok(y[fitting], 50, 10) and sum(s["usable"] for s in inner) >= 2
        plans.append({"scenario": scenario["name"], "scheme": scheme, "fold": fold, "train": fitting,
                      "test": heldout, "inner": inner, "usable": bool(valid), "distance": distance})
    return plans


def logistic(c):
    return make_pipeline(SimpleImputer(strategy="median", keep_empty_features=True), StandardScaler(),
                         LogisticRegression(C=c, solver="lbfgs", max_iter=2000, tol=1e-8))


def fit_checked(model, x, y):
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        model.fit(x, y)
    if any(issubclass(w.category, ConvergenceWarning) for w in caught):
        raise RuntimeError("Model convergence failed")
    return [str(w.message) for w in caught]


def audit_split(plan, scenario, train, test):
    assert all(scenario["meta"][i]["outcome_year"] == 2024 for i in train)
    assert set(train).isdisjoint(test)
    assert np.min(plan["distance"][np.ix_(train, test)]) >= 1500
    for field in GROUP_FIELDS:
        a = {scenario["meta"][i][field] for i in train} - {""}
        b = {scenario["meta"][i][field] for i in test} - {""}
        assert a.isdisjoint(b)


def fit_experiments(scenarios, plans):
    predictions, scores, memberships, inner_memberships, fit_records = [], [], [], [], []
    for index, plan in enumerate(plans):
        scenario = scenarios[plan["scenario"]]
        x, y, meta = scenario["x"], scenario["y"], scenario["meta"]
        tr, te = plan["train"], plan["test"]
        audit_split(plan, scenario, tr, te)
        base = {k: plan[k] for k in ("scenario", "scheme", "fold")}
        for role, ids in (("train", tr), ("test", te)):
            memberships += [base | {"role": role, "row_id": meta[i]["row_id"], "year": meta[i]["outcome_year"]} for i in ids]
        for inner in plan["inner"]:
            if inner["usable"]:
                audit_split(plan, scenario, inner["train"], inner["validation"])
            for role in ("train", "validation"):
                inner_memberships += [base | {"inner_fold": inner["fold"], "usable": inner["usable"], "role": role,
                                               "row_id": meta[i]["row_id"]} for i in inner[role]]
        model_ids = ["M0", "M1"] + (["B0", "B1"] if plan["scenario"] == "core_50m" else [])
        for model_id in model_ids:
            cols = np.arange(2 if model_id.endswith("0") else x.shape[1])
            selected_c = ""
            if model_id.startswith("M"):
                candidate_scores = []
                for c in CS:
                    vals = []
                    for inner in plan["inner"]:
                        if not inner["usable"]:
                            continue
                        fit, val = inner["train"], inner["validation"]
                        model = logistic(c)
                        fit_checked(model, x[np.ix_(fit, cols)], y[fit])
                        ap = average_precision_score(y[val], model.predict_proba(x[np.ix_(val, cols)])[:, 1])
                        vals.append(ap)
                        scores.append(base | {"model": model_id, "C": c, "inner_fold": inner["fold"],
                                               "fit_rows": len(fit), "validation_rows": len(val), "average_precision": ap})
                    candidate_scores.append(float(np.mean(vals)))
                selected_c = CS[int(np.argmax(candidate_scores))]
                model = logistic(selected_c)
            else:
                model = make_pipeline(SimpleImputer(strategy="median", keep_empty_features=True),
                    GradientBoostingClassifier(n_estimators=100, learning_rate=0.05, max_depth=2,
                                               min_samples_leaf=10, random_state=SEED))
            notes = fit_checked(model, x[np.ix_(tr, cols)], y[tr])
            pred = model.predict_proba(x[np.ix_(te, cols)])[:, 1]
            fit_id = f"fit_{index:03d}_{model_id}"
            model_path = OUT / "models" / f"{fit_id}.joblib"
            model_path.parent.mkdir(exist_ok=True)
            joblib.dump({"pipeline": model, "feature_names": [scenario["features"][j] for j in cols],
                         "train_row_ids": [meta[i]["row_id"] for i in tr], "test_row_ids": [meta[i]["row_id"] for i in te],
                         "plan": base, "model": model_id, "selected_C": selected_c}, model_path, compress=3)
            all_missing = [scenario["features"][j] for j in cols if np.isnan(x[tr, j]).all()]
            fit_records.append(base | {"fit_id": fit_id, "model": model_id, "selected_C": selected_c,
                "train_rows": len(tr), "train_positive": int(y[tr].sum()), "test_rows": len(te),
                "feature_count": len(cols), "all_missing_training_columns": "|".join(all_missing),
                "warnings": "|".join(notes), "model_file": str(model_path.relative_to(ROOT))})
            replay = joblib.load(model_path)["pipeline"].predict_proba(x[np.ix_(te, cols)])[:, 1]
            assert np.array_equal(pred, replay)
            for i, score in zip(te, pred):
                predictions.append(base | {"row_id": meta[i]["row_id"], "city": meta[i]["city"], "model": model_id,
                    "fit_id": fit_id, "observed": int(y[i]), "score": float(score), "is_probability": True,
                    "label_field": meta[i]["label_field"], "spatial_block_2km": meta[i]["spatial_block_2km"],
                    "spatial_block_5km": meta[i]["spatial_block_5km"]})
        for model_id in ("training_prevalence", "prior_local_rank"):
            pred = np.full(len(te), y[tr].mean()) if model_id == "training_prevalence" else x[te, 0]
            for i, score in zip(te, pred):
                predictions.append(base | {"row_id": meta[i]["row_id"], "city": meta[i]["city"], "model": model_id,
                    "fit_id": "", "observed": int(y[i]), "score": float(score), "is_probability": model_id == "training_prevalence",
                    "label_field": meta[i]["label_field"], "spatial_block_2km": meta[i]["spatial_block_2km"],
                    "spatial_block_5km": meta[i]["spatial_block_5km"]})
        print(f"Fitted {plan['scenario']} {plan['scheme']} {plan['fold']}: train {len(tr)}, test {len(te)}", flush=True)
    write(OUT / "predictions.csv", predictions)
    write(OUT / "inner_scores.csv", scores)
    write(OUT / "split_membership.csv", memberships)
    write(OUT / "inner_membership.csv", inner_memberships)
    write(OUT / "model_fits.csv", fit_records)
    return predictions, fit_records


def metric_rows(predictions):
    metrics, calibration = [], []
    groups = sorted({(r["scenario"], r["scheme"], r["model"]) for r in predictions})
    for scenario, scheme, model in groups:
        selected = [r for r in predictions if (r["scenario"], r["scheme"], r["model"]) == (scenario, scheme, model)]
        for city in ["ALL"] + [c for c in CITIES if any(r["city"] == c for r in selected)]:
            rows = sorted((r for r in selected if city == "ALL" or r["city"] == city), key=lambda r: r["row_id"])
            assert len(rows) == len({r["row_id"] for r in rows})
            y = np.array([r["observed"] for r in rows])
            p = np.array([r["score"] for r in rows])
            top = np.argsort(-p, kind="stable")[:math.ceil(len(rows) * .1)]
            is_probability = rows[0]["is_probability"]
            prefix = {"scenario": scenario, "scheme": scheme, "city": city, "model": model}
            ap = float(average_precision_score(y, p)) if y.sum() else ""
            metrics.append(prefix | {"n": len(rows), "positive": int(y.sum()), "prevalence": float(y.mean()),
                "average_precision": ap, "roc_auc": float(roc_auc_score(y, p)) if len(set(y)) == 2 else "",
                "brier_score": float(brier_score_loss(y, p)) if is_probability else "",
                "top_decile_precision": float(y[top].mean()), "top_decile_recall": float(y[top].sum() / y.sum()) if y.sum() else "",
                "mean_prediction": float(p.mean()) if is_probability else ""})
            if ap != "":
                assert math.isclose(weighted_ap(y, p, np.ones(len(y)))[0], ap, abs_tol=1e-12)
            if is_probability:
                bins = np.minimum((p * 10).astype(int), 9)
                for k in range(10):
                    chosen = bins == k
                    calibration.append(prefix | {"bin": k, "lower": k / 10, "upper": (k + 1) / 10,
                        "n": int(chosen.sum()), "mean_prediction": float(p[chosen].mean()) if chosen.any() else "",
                        "observed_fraction": float(y[chosen].mean()) if chosen.any() else ""})
    write(OUT / "metrics.csv", metrics)
    write(OUT / "calibration_bins.csv", calibration)
    macro = []
    for scenario, scheme, model in groups:
        group = [r for r in metrics if r["scenario"] == scenario and r["scheme"] == scheme and r["model"] == model and r["city"] != "ALL"]
        macro.append({"scenario": scenario, "scheme": scheme, "model": model, "cities": len(group),
                      "equal_city_mean_ap": float(np.mean([r["average_precision"] for r in group]))})
    write(OUT / "macro_metrics.csv", macro)
    return metrics


def bootstrap_weights(rows, block_field):
    rng = np.random.default_rng(SEED)
    weights = np.zeros((2000, len(rows)), dtype=np.int16)
    for city in CITIES:
        indices = [i for i, r in enumerate(rows) if r["city"] == city]
        if not indices:
            continue
        blocks = sorted({rows[i][block_field] for i in indices})
        counts = rng.multinomial(len(blocks), np.full(len(blocks), 1 / len(blocks)), size=2000)
        mapping = {block: j for j, block in enumerate(blocks)}
        weights[:, indices] = counts[:, [mapping[rows[i][block_field]] for i in indices]]
    return weights


def uncertainty(predictions):
    results = []
    groups = sorted({(r["scenario"], r["scheme"]) for r in predictions})
    for scenario, scheme in groups:
        chosen = [r for r in predictions if r["scenario"] == scenario and r["scheme"] == scheme]
        pairs = [("M1", "M0")] + ([("B1", "B0")] if scenario == "core_50m" else [])
        for high, low in pairs:
            for city in ["ALL"] + [c for c in CITIES if any(r["city"] == c for r in chosen)]:
                a = sorted((r for r in chosen if r["model"] == high and (city == "ALL" or r["city"] == city)), key=lambda r: r["row_id"])
                b = sorted((r for r in chosen if r["model"] == low and (city == "ALL" or r["city"] == city)), key=lambda r: r["row_id"])
                assert [r["row_id"] for r in a] == [r["row_id"] for r in b]
                yy = np.array([r["observed"] for r in a])
                ps = [np.array([r["score"] for r in rows]) for rows in (a, b)]
                ap_diff = float(average_precision_score(yy, ps[0]) - average_precision_score(yy, ps[1]))
                scales = [2, 5] if scenario == "core_50m" and scheme == "forward_spatial" and city == "ALL" and high == "M1" else [2]
                for scale in scales:
                    field = f"spatial_block_{scale}km"
                    weights = bootstrap_weights(a, field)
                    valid = (weights @ yy > 0) & (weights @ (1 - yy) > 0)
                    deltas = weighted_ap(yy, ps[0], weights[valid]) - weighted_ap(yy, ps[1], weights[valid])
                    lo, hi = np.quantile(deltas, [.025, .975])
                    results.append({"scenario": scenario, "scheme": scheme, "city": city, "comparison": high + "-" + low,
                        "block_km": scale, "test_blocks": len({r[field] for r in a}), "ap_difference": ap_diff,
                        "ci_low": float(lo), "ci_high": float(hi), "resamples": 2000, "valid_resamples": int(valid.sum()),
                        "inference": "exploratory_conditional_on_fitted_predictions; secondary_unadjusted"})
        print(f"Uncertainty complete: {scenario} {scheme}", flush=True)
    write(OUT / "paired_differences.csv", results)
    return results


def validate_saved(scenarios, plans, predictions, fits):
    replayed = 0
    for fit in fits:
        artifact = joblib.load(ROOT / fit["model_file"])
        s = scenarios[fit["scenario"]]
        index = {r["row_id"]: i for i, r in enumerate(s["meta"])}
        ids = [index[r] for r in artifact["test_row_ids"]]
        tr = [index[r] for r in artifact["train_row_ids"]]
        cols = [s["features"].index(c) for c in artifact["feature_names"]]
        xx = s["x"][np.ix_(tr, cols)]
        expected = []
        for col in xx.T:
            expected.append(float(np.median(col[~np.isnan(col)])) if np.any(~np.isnan(col)) else 0.0)
        imputer = artifact["pipeline"].steps[0][1]
        assert np.allclose(imputer.statistics_, expected, rtol=1e-12, atol=1e-12)
        if fit["model"].startswith("M"):
            scaler = artifact["pipeline"].steps[1][1]
            filled = np.where(np.isnan(xx), np.array(expected)[None, :], xx)
            assert np.allclose(scaler.mean_, filled.mean(axis=0))
        observed = artifact["pipeline"].predict_proba(s["x"][np.ix_(ids, cols)])[:, 1]
        saved = [r for r in predictions if r["fit_id"] == fit["fit_id"]]
        assert [r["row_id"] for r in saved] == artifact["test_row_ids"]
        assert np.array_equal(observed, [r["score"] for r in saved])
        assert np.array_equal([r["observed"] for r in saved], s["y"][ids])
        replayed += 1
    for scenario, scheme in {(p["scenario"], p["scheme"]) for p in plans}:
        expected = {r["row_id"] for r in scenarios[scenario]["meta"] if r["outcome_year"] == 2025}
        for model in {r["model"] for r in predictions if r["scenario"] == scenario and r["scheme"] == scheme}:
            rows = [r for r in predictions if r["scenario"] == scenario and r["scheme"] == scheme and r["model"] == model]
            assert len(rows) == len(expected) and {r["row_id"] for r in rows} == expected
    for entry in read(OUT / "input_manifest.csv"):
        path = PROJECT / entry["file"]
        assert path.stat().st_size == int(entry["bytes"]) and sha(path) == entry["sha256"]
    save(OUT / "validation.json", {"status": "PASS", "checks": {
        "phase1_3_and_phase4_inputs_unchanged": "PASS", "outer_and_inner_spatial_identity_geography_separation": "PASS",
        "training_only_imputation_and_scaling": "PASS", "all_saved_models_replay_exactly": "PASS",
        "prediction_labels_and_unique_complete_test_coverage": "PASS", "weighted_bootstrap_AP_matches_sklearn": "PASS"},
        "models_replayed": replayed, "predictions": len(predictions), "scientific_review": "PENDING"})


def summarize(metrics, differences, fit_count, skipped):
    from report import generate
    primary = next(r for r in differences if r["scenario"] == "core_50m" and r["scheme"] == "forward_spatial"
                   and r["city"] == "ALL" and r["comparison"] == "M1-M0" and r["block_km"] == 2)
    m = {r["model"]: r for r in metrics if r["scenario"] == "core_50m" and r["scheme"] == "forward_spatial" and r["city"] == "ALL"}
    gate = primary["ap_difference"] >= .01 and primary["ci_low"] > 0 and m["M1"]["brier_score"] <= m["M0"]["brier_score"]
    status = {"status": "COMPUTATIONALLY_COMPLETE", "scope": "exploratory_retrospective_coordinate_benchmark",
        "numerical_continuation_gate": bool(gate), "primary_ap_gain": primary["ap_difference"],
        "primary_ap_gain_ci": [primary["ci_low"], primary["ci_high"]], "models_fitted": fit_count,
        "skipped_scenarios": skipped, "scientific_review": "PENDING", "confirmatory_eligible": False,
        "phase5_started": False, "next_action": "review_robustness_and_measurement_before_further_work" if gate else "stop_environmental_model_expansion; report_negative_or_inconclusive_result"}
    save(OUT / "status.json", status)
    generate(status, metrics, differences)
    files = sorted(p for p in ROOT.rglob("*") if p.is_file() and "__pycache__" not in p.parts and p != OUT / "output_manifest.csv")
    write(OUT / "output_manifest.csv", [{"file": str(p.relative_to(ROOT)), "bytes": p.stat().st_size, "sha256": sha(p)} for p in files])


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    frozen_inputs()
    save(OUT / "status.json", {"status": "ASSESSING_FEASIBILITY", "models_fitted": 0})
    scenarios = prepare_scenarios()
    plans = []
    feasibility, skipped = [], []
    for name, scenario in scenarios.items():
        these = plans_for(scenario)
        for p in these:
            feasibility.append({"scenario": name, "scheme": p["scheme"], "fold": p["fold"], "train_rows": len(p["train"]),
                "train_positive": int(scenario["y"][p["train"]].sum()), "test_rows": len(p["test"]),
                "test_positive": int(scenario["y"][p["test"]].sum()), "usable_inner_folds": sum(r["usable"] for r in p["inner"]), "usable": p["usable"]})
        if not all(p["usable"] for p in these):
            skipped.append(name)
        else:
            plans += these
    write(OUT / "feasibility.csv", feasibility)
    if "core_50m" in skipped:
        save(OUT / "status.json", {"status": "STOPPED_FEASIBILITY_FAILURE", "models_fitted": 0, "reason": "primary_spatial_or_inner_split_not_usable"})
        raise RuntimeError("Primary feasibility failed; no models fitted. See feasibility.csv")
    print(f"Feasibility passed: {len(plans)} outer splits; skipped {skipped}", flush=True)
    with threadpool_limits(limits=1):
        predictions, fits = fit_experiments(scenarios, plans)
        metrics = metric_rows(predictions)
        differences = uncertainty(predictions)
        validate_saved(scenarios, plans, predictions, fits)
    summarize(metrics, differences, len(fits), skipped)


if __name__ == "__main__":
    main()
