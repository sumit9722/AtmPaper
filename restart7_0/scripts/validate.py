"""Independent replay and targeted source checks for the Restart 7 delta."""
import collections
import itertools
import json
import math
import random
import numpy as np
from pyproj import Geod
from common import *


def same(a, b):
    if a == "" or b == "":
        assert a == b, (a, b)
    else:
        assert math.isclose(float(a), float(b), rel_tol=1e-12, abs_tol=1e-10), (a, b)


def main():
    checks = {}
    assert_inputs_unchanged()
    freeze()
    checks["base_consumed_artifacts_unchanged"] = "PASS"
    panels = read(DATA / "atm_panel_full_year_2024_2025.csv") + read(DATA / "atm_panel_partial_2023.csv")
    pby = {p["row_id"]: p for p in panels}
    base_panels = read(BASE / "data/processed/atm_panel_full_year_2024_2025.csv") + read(BASE / "data/processed/atm_panel_partial_2023.csv")
    assert len(panels) == len(pby) == 4018
    assert set(pby) == {p["row_id"] for p in base_panels}
    for old in base_panels:
        current = pby[old["row_id"]]
        for field in ("site_id", "city", "longitude", "latitude", "outcome_year", "osm_id", "supported_days",
                      "supported_start", "supported_end_exclusive", "osm_geometry_is_centroid", "max_coordinate_drift_m"):
            assert old[field] == current[field], (old["row_id"], field)
    checks["unchanged_membership_geometry_and_exposure"] = "PASS"
    # Deliberately spell out the decisions independently of the builder's predicate.
    base_events = {r["event_id"]: r for r in records(BASE / "data/processed/crime_primary_2022_2025.csv")}
    remove = {eid for eid, e in base_events.items() if
              (e["city"] == "New York City" and e["native_code"] in {"231", "233", "234"}) or
              (e["city"] == "Chicago" and e["native_code"].lstrip("0") == "760")}
    retained_ids = set()
    for event in records(DATA / "crime_retained_2022_2025.csv.gz"):
        eid = event["event_id"]
        assert eid not in retained_ids and event == base_events[eid]
        retained_ids.add(eid)
    assert retained_ids == set(base_events) - remove
    assert {r["event_id"] for r in read(QA / "excluded_vehicle_burglary.csv")} == remove
    for row in read(QA / "crime_conservation.csv"):
        assert int(row["base_cases"]) == int(row["retained_cases"]) + int(row["excluded_vehicle_cases"])
    conflicts = {r["event_id"] for r in read(QA / "source_description_review.csv")}
    checks["native_offense_filter_and_case_conservation"] = "PASS"
    quality = {r["row_id"]: r for r in read(BASE / "results/phase3/data/site_lookup_and_quality.csv")}
    pairs = set()
    for pair in records(BASE / "data/processed/qa/facility_review.csv"):
        for site in (pair["site_a"], pair["site_b"]):
            pairs.add((pair["cohort"], pair["outcome_year"], site))
    expected_core = set()
    for p in panels:
        neighbors = quality[p["row_id"]]["atm_colocated_other_objects_10m"]
        if (p["outcome_year"] in ("2024", "2025") and p["osm_geometry_is_centroid"] == "False"
                and float(p["max_coordinate_drift_m"]) <= 10 and p["boundary_buffer_clear_500m"] == "True"
                and neighbors != "" and int(neighbors) == 0
                and (p["cohort"], p["outcome_year"], p["site_id"]) not in pairs):
            expected_core.add(p["row_id"])
    core_panels = read(DATA / "atm_panel_core_2024_2025.csv")
    assert {p["row_id"] for p in core_panels} == expected_core
    assert {r["row_id"] for r in read(QA / "cohort_eligibility.csv") if r["core_eligible"] == "True"} == expected_core
    checks["independent_core_membership_rules"] = "PASS"
    # Every retained inherited link must appear exactly once, with original geometry.
    expected_links = (r for r in records(BASE / "data/processed/event_atm_links.csv")
                      if r["row_id"] in pby and r["event_id"] not in remove)
    link_count = 0
    all_counts = collections.defaultdict(collections.Counter)
    months = collections.defaultdict(collections.Counter)
    link_ids = collections.defaultdict(set)
    for old, link in itertools.zip_longest(expected_links, records(DATA / "event_atm_links.csv.gz")):
        assert old is not None and link is not None
        for field in old:
            assert old[field] == link[field], (field, old[field], link[field])
        p, event = pby[link["row_id"]], base_events[link["event_id"]]
        assert p["city"] == event["city"] == link["city"]
        distance = float(link["distance_m"])
        known = event["report_date_usable"] == "True" and event["report_date"] < (
            str(int(p["outcome_year"]) + (link["role"] == "outcome")) + "-01-01")
        assert (link["report_available_by_cutoff"] == "True") == known
        c = all_counts[link["row_id"]]
        link_ids[(link["row_id"], link["role"])].add(link["event_id"])
        if link["role"] == "outcome":
            assert p["supported_start"] <= event["event_date"] < p["supported_end_exclusive"]
            assert distance <= 100
            for radius in RADII:
                if distance <= radius:
                    for tally in (c, months[(link["row_id"], event["event_date"][:7])]):
                        tally[f"primary_count_{radius}m"] += 1
                        tally[f"{event['category']}_count_{radius}m"] += 1
                        tally[f"primary_reported_count_{radius}m"] += int(known)
                        tally[f"primary_nearest_count_{radius}m"] += link["nearest_eligible_site"] == "True"
                        tally[f"core_nearest_count_{radius}m"] += link["nearest_core_site"] == "True"
                        tally[f"description_conflict_count_{radius}m"] += link["event_id"] in conflicts
        else:
            assert int(event["event_year"]) == int(p["outcome_year"]) - 1 and 200 < distance <= 500
            c["background_unfiltered_200_500m"] += 1
            c["background_primary_200_500m"] += int(known)
            c["background_missing_invalid_report"] += event["report_date_usable"] != "True"
            c["background_late_report"] += event["report_date_usable"] == "True" and not known
        link_count += 1
    for p in panels:
        c = all_counts[p["row_id"]]
        for radius in RADII:
            for prefix in ("primary", "robbery", "burglary", "primary_reported", "primary_nearest", "core_nearest", "description_conflict"):
                name = f"{prefix}_count_{radius}m"
                same(p[name], "" if prefix == "primary_reported" and p["city"] == "Chicago" else c[name])
            assert int(p[f"primary_any_{radius}m"]) == int(c[f"primary_count_{radius}m"] > 0)
            assert int(p[f"no_description_conflict_count_{radius}m"]) == c[f"primary_count_{radius}m"] - c[f"description_conflict_count_{radius}m"]
        for field in ("background_unfiltered_200_500m", "background_primary_200_500m", "background_missing_invalid_report", "background_late_report"):
            same(p[field], "" if field == "background_primary_200_500m" and p["city"] == "Chicago" else c[field])
    checks["complete_cached_link_reuse_and_annual_count_replay"] = "PASS"
    # Nearest-site sensitivities use each subset's eligible locations.
    subsets = {"core": expected_core,
               "point_only": {p["row_id"] for p in read(DATA / "atm_panel_point_only_2024_2025.csv")},
               "explicit_atm_core": {p["row_id"] for p in read(DATA / "atm_panel_explicit_atm_core_2024_2025.csv")}}
    nearest_counts = collections.defaultdict(collections.Counter)
    grouping = lambda r: (r["cohort"], r["city"], r["outcome_year"], r["role"], r["event_id"])
    for _, group in itertools.groupby(records(DATA / "event_atm_links.csv.gz"), grouping):
        links = list(group)
        for name, ids in subsets.items():
            selected = [r for r in links if r["row_id"] in ids]
            nearest = min(selected, key=lambda r: (float(r["distance_m"]), r["site_id"]))["row_id"] if selected else None
            for link in links:
                assert (link[f"nearest_{name}_site"] == "True") == (link["row_id"] == nearest)
                if link["role"] == "outcome":
                    for radius in RADII:
                        if float(link["distance_m"]) <= radius:
                            nearest_counts[(name, link["row_id"])][radius] += link["row_id"] == nearest
            if links[0]["role"] == "outcome":
                for link in links:
                    for radius in RADII:
                        assert int(link[f"core_matches_{radius}m"]) == sum(r["row_id"] in expected_core and float(r["distance_m"]) <= radius for r in links)
    for name in subsets:
        for p in read(DATA / f"atm_panel_{name}_2024_2025.csv"):
            assert p["nearest_assignment_population"] == name
            for radius in RADII:
                assert int(p[f"primary_nearest_count_{radius}m"]) == nearest_counts[(name, p["row_id"])][radius]
    checks["nearest_assignment_recomputed_for_every_subset"] = "PASS"
    annual_months = collections.defaultdict(collections.Counter)
    month_keys = set()
    for month in records(DATA / "atm_site_month_panel.csv.gz"):
        rowid = month["annual_row_id"]
        key = (rowid, month["month"])
        assert key not in month_keys
        month_keys.add(key)
        annual_months[rowid]["supported_days"] += int(month["supported_days_in_month"])
        for radius in RADII:
            for prefix in ("primary", "robbery", "burglary", "primary_reported", "primary_nearest", "core_nearest", "description_conflict"):
                field = f"{prefix}_count_{radius}m"
                same(month[field], "" if prefix == "primary_reported" and month["city"] == "Chicago" else months[key][field])
                if month[field] != "":
                    annual_months[rowid][field] += int(month[field])
    base_month_keys = {(r["annual_row_id"], r["month"]) for r in records(BASE / "data/processed/atm_site_month_panel.csv") if r["annual_row_id"] in pby}
    assert month_keys == base_month_keys
    for p in panels:
        for field, value in annual_months[p["row_id"]].items():
            same(p[field], value)
    checks["monthly_counts_exposure_and_annual_reconciliation"] = "PASS"
    prior = collections.defaultdict(collections.Counter)
    prior_ids = collections.defaultdict(set)
    before_prior = (r for r in records(BASE / "results/phase3/data/prior_event_links.csv.gz") if r["event_id"] not in remove)
    for old, link in itertools.zip_longest(before_prior, records(DATA / "prior_event_links.csv.gz")):
        assert old == link and old is not None
        p, e = pby[link["row_id"]], base_events[link["event_id"]]
        assert e["city"] == p["city"] and int(e["event_year"]) == int(p["outcome_year"]) - 1
        d = float(link["distance_m"])
        assert d <= 100
        known = e["report_date_usable"] == "True" and e["report_date"] < p["outcome_year"] + "-01-01"
        prior_ids[p["row_id"]].add(e["event_id"])
        selections = {"prior_crime_25m": d <= 25, "prior_crime_50m": d <= 50, "prior_crime_100m": True,
                      "prior_robbery_50m": d <= 50 and e["category"] == "robbery",
                      "prior_burglary_50m": d <= 50 and e["category"] == "burglary",
                      "prior_recent_crime_50m": d <= 50 and int(e["event_date"][5:7]) >= 7}
        for field, add in selections.items():
            prior[p["row_id"]][field + "_unfiltered"] += int(add)
            prior[p["row_id"]][field] += int(add and known)
    context = {r["row_id"]: r for r in read(FEATURES / "data/site_context_raw.csv")}
    for rowid, p in pby.items():
        for field in LAGS:
            same(context[rowid][field + "_unfiltered"], prior[rowid][field + "_unfiltered"])
            same(context[rowid][field], "" if p["city"] == "Chicago" else prior[rowid][field])
    checks["corrected_prior_counts_cutoffs_and_chicago_missingness"] = "PASS"
    conflict_local = collections.Counter()
    conflict_annulus = collections.Counter()
    conflict_outcome = collections.defaultdict(collections.Counter)
    for link in records(DATA / "prior_event_links.csv.gz"):
        if link["event_id"] in conflicts and float(link["distance_m"]) <= 50:
            conflict_local[link["row_id"]] += 1
    for link in records(DATA / "event_atm_links.csv.gz"):
        if link["event_id"] not in conflicts:
            continue
        if link["role"] == "background":
            conflict_annulus[link["row_id"]] += 1
        else:
            for radius in RADII:
                if float(link["distance_m"]) <= radius:
                    conflict_outcome[link["row_id"]][radius] += 1
    for suffix in ("full_year_2024_2025", "partial_2023"):
        for row in records(FEATURES / f"data/features_no_source_conflicts_{suffix}.csv"):
            rowid = row["row_id"]
            same(row["log1p_prior_local_50m_retrospective"], math.log1p(prior[rowid]["prior_crime_50m_unfiltered"] - conflict_local[rowid]))
            same(row["log1p_prior_annulus_200_500m_retrospective"], math.log1p(all_counts[rowid]["background_unfiltered_200_500m"] - conflict_annulus[rowid]))
    checks["source_description_conflict_sensitivity_baselines"] = "PASS"
    # Direct geodesic omission check: two deterministic sites in each city/year.
    geod = Geod(ellps="WGS84")
    event_groups = collections.defaultdict(list)
    for eid in sorted(retained_ids):
        e = base_events[eid]
        event_groups[(e["city"], e["event_year"])].append(e)
    sampled = []
    for city in CITIES:
        for year in ("2023", "2024", "2025"):
            group = sorted((p for p in panels if p["city"] == city and p["outcome_year"] == year), key=lambda p: p["row_id"])
            sampled += random.Random(701).sample(group, min(2, len(group)))
    for p in sampled:
        for year in (p["outcome_year"], str(int(p["outcome_year"]) - 1)):
            es = event_groups[(p["city"], year)]
            distances = geod.inv(np.full(len(es), float(p["longitude"])), np.full(len(es), float(p["latitude"])),
                                 np.array([float(e["longitude"]) for e in es]), np.array([float(e["latitude"]) for e in es]))[2]
            if year == p["outcome_year"]:
                expected = {e["event_id"] for e, d in zip(es, distances) if d <= 100 and p["supported_start"] <= e["event_date"] < p["supported_end_exclusive"]}
                assert expected == link_ids[(p["row_id"], "outcome")]
            else:
                expected = {e["event_id"] for e, d in zip(es, distances) if 200 < d <= 500}
                assert expected == link_ids[(p["row_id"], "background")]
                expected_prior = {e["event_id"] for e, d in zip(es, distances) if d <= 100}
                assert expected_prior == prior_ids[p["row_id"]]
    write(QA / "independent_distance_sample.csv", ({k: p[k] for k in ("row_id", "city", "outcome_year", "longitude", "latitude")} for p in sampled))
    checks["independent_geodesic_omission_check_18_sites"] = "PASS"
    schema = json.loads((FEATURES / "data/feature_schema.json").read_text())
    old_primary = {}
    raw_environment = {}
    for suffix in ("full_year_2024_2025", "partial_2023"):
        old_primary.update({r["row_id"]: r for r in read(BASE / f"results/phase3/data/features_primary_{suffix}.csv")})
        raw_environment.update({r["row_id"]: r for r in read(BASE / f"results/phase3_environment_expanded/environment_{suffix}.csv")})
        for row in records(FEATURES / f"data/features_primary_{suffix}.csv"):
            rowid = row["row_id"]
            assert list(row) == ["row_id"] + schema["primary_predictors"]
            same(row[schema["baseline_predictors"][0]], math.log1p(prior[rowid]["prior_crime_50m_unfiltered"]))
            same(row[schema["baseline_predictors"][1]], math.log1p(all_counts[rowid]["background_unfiltered_200_500m"]))
            for col in schema["environment_predictors"]:
                assert row[col] == old_primary[rowid][col]
        for row in records(FEATURES / f"data/features_report_filtered_{suffix}.csv"):
            rowid = row["row_id"]
            assert pby[rowid]["city"] != "Chicago"
            same(row["log1p_prior_local_50m_report_filtered"], math.log1p(prior[rowid]["prior_crime_50m"]))
            same(row["log1p_prior_annulus_200_500m_report_filtered"], math.log1p(all_counts[rowid]["background_primary_200_500m"]))
        expanded = read(FEATURES / f"data/features_expanded_environment_{suffix}.csv")
        for row in expanded:
            assert list(row) == ["row_id"] + schema["expanded_environment_predictors"]
            for col in schema["expanded_environment_predictors"]:
                assert row[col] == raw_environment[row["row_id"]][col]
    assert not set(spec()["exclude_expanded_city_proxies"]) & set(schema["expanded_environment_predictors"])
    assert not set(spec()["redundant_expanded_aliases"]) & set(schema["expanded_environment_predictors"])
    for alias, representative in spec()["redundant_expanded_aliases"].items():
        assert all(r[alias] == r[representative] for r in raw_environment.values())
    for path in (FEATURES / "data").glob("features_*.csv"):
        rows = read(path)
        ids = [r["row_id"] for r in rows]
        assert len(ids) == len(set(ids))
        if "_core_" in path.name:
            assert set(ids) <= expected_core
        forbidden = {"city", "site_id", "longitude", "latitude", "core_eligible", "outcome_year", "supported_days", "sld_D1_FLAG"}
        assert rows and not forbidden & set(rows[0])
        suffix = next(s for s in ("explicit_atm_core_2024_2025", "point_only_2024_2025", "core_2024_2025",
            "full_year_2024_2025", "partial_2023", "core_2024", "core_2025", "full_year_2024", "full_year_2025") if path.stem.endswith("_" + s))
        expected = {p["row_id"] for p in panels if
                    (p["outcome_year"] == "2023" if suffix == "partial_2023" else p["outcome_year"] in ("2024", "2025"))}
        if suffix.startswith("explicit_atm_core"):
            expected &= subsets["explicit_atm_core"]
        elif suffix.startswith("point_only"):
            expected &= subsets["point_only"]
        elif suffix.startswith("core"):
            expected &= expected_core
        if suffix in ("core_2024", "core_2025", "full_year_2024", "full_year_2025"):
            expected = {key for key in expected if pby[key]["outcome_year"] == suffix[-4:]}
        if path.stem.startswith("features_report_filtered_"):
            expected = {key for key in expected if pby[key]["city"] != "Chicago"}
        assert set(ids) == expected, path.name
        family = path.stem[:-len(suffix)]
        master_suffix = "partial_2023" if suffix == "partial_2023" else "full_year_2024_2025"
        master_rows = {r["row_id"]: r for r in read(FEATURES / "data" / (family + master_suffix + ".csv"))}
        assert all(row == master_rows[row["row_id"]] for row in rows), path.name
    labels = read(FEATURES / "data/outcomes.csv")
    assert {r["row_id"] for r in labels} == set(pby)
    for label in labels:
        p = pby[label["row_id"]]
        for radius in RADII:
            assert label[f"recorded_any_{radius}m"] == p[f"primary_any_{radius}m"]
            assert label[f"recorded_count_{radius}m"] == p[f"primary_count_{radius}m"]
            reported = p[f"primary_reported_count_{radius}m"]
            assert label[f"reported_before_next_year_count_{radius}m"] == reported
            assert label[f"reported_before_next_year_any_{radius}m"] == ("" if reported == "" else str(int(int(reported) > 0)))
            assert int(label[f"no_source_conflicts_any_{radius}m"]) == int(int(p[f"primary_count_{radius}m"]) - conflict_outcome[p["row_id"]][radius] > 0)
    checks["fixed_baseline_environment_inheritance_allowlists_and_label_alignment"] = "PASS"
    for filename in ("facility_review.csv", "manual_linkage_audit.csv"):
        original = read(BASE / "data/processed/qa" / filename)
        revised = read(QA / filename)
        assert len(original) == len(revised)
        assert all(a["reviewer_decision"] == b["reviewer_decision"] for a, b in zip(original, revised))
    assert schema["models_fitted"] is False and schema["confirmatory_modeling_ready"] is False
    checks["human_review_status_and_claim_limits_preserved"] = "PASS"
    assert_inputs_unchanged()
    save(QA / "validation.json", {"status": "PASS", "checks": checks, "master_full_year_rows": 2731,
        "core_rows": len(expected_core), "partial_2023_rows": 1287, "retained_cases": len(retained_ids),
        "excluded_vehicle_cases": len(remove), "retained_event_links": link_count, "monthly_rows": len(month_keys),
        "independent_distance_sites": len(sampled), "scientific_review": "PENDING", "models_fitted": False,
        "confirmatory_eligible": False})
    print(f"Validation PASS: {len(checks)} groups; {len(sampled)} independent distance audits", flush=True)


if __name__ == "__main__":
    main()
