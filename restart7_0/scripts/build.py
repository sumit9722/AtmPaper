"""Apply a targeted revision to frozen Restart 6 outputs; no downloads or fits."""
import collections
import csv
import itertools
import json
import math
from common import *


def classify_events():
    events = {}
    excluded_rows = []
    conflicts = []
    rules = spec()["exclude_native_codes"]
    totals = collections.Counter()
    for event in records(BASE / "data/processed/crime_primary_2022_2025.csv"):
        eid = event["event_id"]
        assert eid not in events
        events[eid] = event
        remove = excluded(event, rules)
        totals[(event["city"], event["event_year"], "excluded" if remove else "retained")] += 1
        if remove:
            excluded_rows.append(event | {"revision_reason": "vehicle_burglary_outside_common_structural_burglary_endpoint"})
        description = event["native_description"].upper()
        if event["city"] == "Los Angeles" and event["category"] == "burglary" and not any(
                term in description for term in ("BURGL", "459", "LOOT")):
            conflicts.append(event | {"review_reason": "burglary_source_code_with_inconsistent_description",
                                      "reviewer_decision": "PENDING", "treatment": "retained_source_code; exclude_in_sensitivity"})
    removed = {r["event_id"] for r in excluded_rows}
    for row in records(BASE / "data/processed/qa/crime_duplicates.csv"):
        if row["event_id"] in removed and not excluded(row, rules):
            raise RuntimeError("Excluded winning case hides eligible duplicate; targeted re-resolution required")
    fields = list(next(iter(events.values())))
    write(DATA / "crime_retained_2022_2025.csv.gz", (r for eid, r in events.items() if eid not in removed), fields)
    write(QA / "excluded_vehicle_burglary.csv", excluded_rows, fields + ["revision_reason"])
    write(QA / "source_description_review.csv", conflicts, fields + ["review_reason", "reviewer_decision", "treatment"])
    codebook = []
    counts = collections.Counter((e["city"], e["source_system"], e["native_code"], e["native_description"]) for e in events.values())
    conflict_keys = {(e["city"], e["source_system"], e["native_code"], e["native_description"]) for e in conflicts}
    for row in records(BASE / "data/processed/crime_codebook.csv"):
        key = tuple(row[k] for k in ("city", "source_system", "native_code", "native_description"))
        codebook.append(row | {"revision_decision": "EXCLUDE_vehicle_burglary" if excluded(row, rules) else "RETAIN_native_category",
                               "retained_input_incidents": counts[key], "source_description_conflict": key in conflict_keys,
                               "independent_review": "PENDING"})
    write(DATA / "crime_codebook.csv", codebook)
    write(QA / "crime_conservation.csv", [
        {"city": city, "year": year, "base_cases": totals[(city, year, "retained")] + totals[(city, year, "excluded")],
         "retained_cases": totals[(city, year, "retained")], "excluded_vehicle_cases": totals[(city, year, "excluded")]}
        for city in CITIES for year in ("2022", "2023", "2024", "2025")])
    monthly = collections.Counter()
    for eid, event in events.items():
        if eid not in removed:
            monthly[(event["city"], event["event_date"][:7], event["source_system"])] += 1
    write(DATA / "crime_monthly_coverage.csv", [
        {"city": c, "month": m, "source_system": s, "retained_cases": n,
         "interpretation": "observed_extract; not_certified_complete"}
        for (c, m, s), n in sorted(monthly.items())])
    print(f"Offense correction: {len(events)} inherited cases, {len(removed)} removed", flush=True)
    return events, removed, {r["event_id"] for r in conflicts}


def cohort_rules(panels, quality):
    pairs = read(BASE / "data/processed/qa/facility_review.csv")
    close = set()
    for pair in pairs:
        for site in (pair["site_a"], pair["site_b"]):
            close.add((pair["cohort"], pair["outcome_year"], site))
    ledger = []
    for panel in panels:
        q = quality[panel["row_id"]]
        reasons = []
        if panel["outcome_year"] == "2023":
            reasons.append("partial_2023_not_main")
        if panel["osm_geometry_is_centroid"] != "False":
            reasons.append("nonpoint_centroid")
        if float(panel["max_coordinate_drift_m"]) > 10:
            reasons.append("coordinate_drift_over_10m")
        if panel["boundary_buffer_clear_500m"] != "True":
            reasons.append("boundary_truncated_background")
        pair_close = (panel["cohort"], panel["outcome_year"], panel["site_id"]) in close
        inventory_close = q["atm_colocated_other_objects_10m"] != "" and int(q["atm_colocated_other_objects_10m"]) > 0
        if pair_close or inventory_close:
            reasons.append("unresolved_object_within_10m")
        if panel["outcome_year"] != "2023" and q["atm_colocated_other_objects_10m"] == "":
            reasons.append("baseline_neighbor_inventory_unavailable")
        ledger.append({"row_id": panel["row_id"], "city": panel["city"], "outcome_year": panel["outcome_year"],
                       "core_eligible": not reasons, "exclusion_reasons": "|".join(reasons),
                       "point_geometry": panel["osm_geometry_is_centroid"] == "False",
                       "explicit_atm_tag": panel["osm_amenity"] == "atm", "close_pair_in_annual_cohort": pair_close,
                       "close_object_in_prior_inventory": inventory_close,
                       "physical_identity_verified": False, "physical_location_precision_verified": False})
    write(QA / "cohort_eligibility.csv", ledger)
    core = {r["row_id"] for r in ledger if r["core_eligible"]}
    points = {r["row_id"] for r in ledger if r["point_geometry"] and r["outcome_year"] != "2023"}
    explicit = {r["row_id"] for r in ledger if r["core_eligible"] and r["explicit_atm_tag"]}
    # Preserve review decisions; annotate rather than impersonating a reviewer.
    annotated = []
    for pair in pairs:
        key_a = f"{pair['cohort']}:{pair['site_a']}:{pair['outcome_year']}"
        key_b = f"{pair['cohort']}:{pair['site_b']}:{pair['outcome_year']}"
        annotated.append(pair | {"site_a_in_revised_core": key_a in core, "site_b_in_revised_core": key_b in core,
                                 "automated_action": "exclude_both_from_core; identity_review_still_pending"})
    write(QA / "facility_review.csv", annotated)
    stages = ("partial_2023_not_main", "nonpoint_centroid", "coordinate_drift_over_10m",
              "boundary_truncated_background", "unresolved_object_within_10m", "baseline_neighbor_inventory_unavailable")
    attrition = []
    for city in CITIES:
        for year in ("2024", "2025"):
            group = [r for r in ledger if r["city"] == city and r["outcome_year"] == year]
            attrition.append({"city": city, "year": year, "stage": "inherited_master", "remaining": len(group), "removed_this_stage": 0})
            for stage in stages[1:]:
                retained = [r for r in group if stage not in r["exclusion_reasons"].split("|")]
                attrition.append({"city": city, "year": year, "stage": stage, "remaining": len(retained),
                                  "removed_this_stage": len(group) - len(retained)})
                group = retained
    write(QA / "cohort_attrition.csv", attrition)
    return core, points, explicit, {r["row_id"]: r for r in ledger}


def aggregate_links(panels, core, points, explicit, removed, conflict_ids):
    byid = {r["row_id"]: r for r in panels}
    counts = {key: collections.Counter() for key in byid}
    other_subsets = {"point_only": points, "explicit_atm_core": explicit}
    months = collections.defaultdict(collections.Counter)
    linkfile = DATA / "event_atm_links.csv.gz"
    consumed = kept = 0
    with csv_stream(linkfile, "w") as stream:
        writer = None
        source = records(BASE / "data/processed/event_atm_links.csv")
        grouping = lambda r: (r["cohort"], r["city"], r["outcome_year"], r["role"], r["event_id"])
        for _, group in itertools.groupby(source, key=grouping):
            links = [r for r in group if r["row_id"] in byid]
            consumed += len(links)
            if not links or links[0]["event_id"] in removed:
                continue
            links.sort(key=lambda r: (float(r["distance_m"]), r["site_id"]))
            core_links = [r for r in links if r["row_id"] in core]
            nearest_core = core_links[0]["row_id"] if core_links else None
            subset_links = {name: [r for r in links if r["row_id"] in ids] for name, ids in other_subsets.items()}
            for index, link in enumerate(links):
                rowid = link["row_id"]
                distance = float(link["distance_m"])
                c = counts[rowid]
                known = link["report_available_by_cutoff"] == "True"
                isout = link["role"] == "outcome"
                cored = rowid in core
                revised = link | {"nearest_eligible_site": index == 0,
                                  "core_eligible": cored, "nearest_core_site": cored and rowid == nearest_core,
                                  "source_description_conflict": link["event_id"] in conflict_ids}
                for radius in RADII:
                    revised[f"matches_{radius}m"] = sum(float(r["distance_m"]) <= radius for r in links) if isout else 0
                    revised[f"core_matches_{radius}m"] = sum(float(r["distance_m"]) <= radius for r in core_links) if isout else 0
                for name, selected_links in subset_links.items():
                    revised[f"nearest_{name}_site"] = bool(selected_links and rowid == selected_links[0]["row_id"])
                if writer is None:
                    writer = csv.DictWriter(stream, fieldnames=list(revised))
                    writer.writeheader()
                writer.writerow(revised)
                kept += 1
                if isout:
                    month = months[(rowid, link["event_date"][:7])]
                    for radius in RADII:
                        if distance > radius:
                            continue
                        increments = {f"primary_count_{radius}m": 1, f"{link['category']}_count_{radius}m": 1,
                                      f"primary_reported_count_{radius}m": int(known),
                                      f"primary_nearest_count_{radius}m": int(index == 0),
                                      f"core_nearest_count_{radius}m": int(cored and rowid == nearest_core),
                                      f"multiple_match_count_{radius}m": int(revised[f"matches_{radius}m"] > 1),
                                      f"core_multiple_match_count_{radius}m": int(cored and revised[f"core_matches_{radius}m"] > 1),
                                      f"description_conflict_count_{radius}m": int(link["event_id"] in conflict_ids)}
                        c.update(increments)
                        month.update(increments)
                        for name, selected_links in subset_links.items():
                            c[f"{name}_nearest_count_{radius}m"] += int(revised[f"nearest_{name}_site"])
                            c[f"{name}_multiple_match_count_{radius}m"] += int(rowid in other_subsets[name] and
                                sum(float(r["distance_m"]) <= radius for r in selected_links) > 1)
                else:
                    usable = link["report_date_usable"] == "True"
                    c.update({"background_unfiltered_200_500m": 1, "background_primary_200_500m": int(known),
                              "background_missing_invalid_report": int(not usable), "background_late_report": int(usable and not known),
                              "background_description_conflicts": int(link["event_id"] in conflict_ids),
                              "background_reported_description_conflicts": int(known and link["event_id"] in conflict_ids)})
    revised_panels = []
    changes = []
    for old in panels:
        key = old["row_id"]
        count = counts[key]
        row = dict(old)
        for radius in RADII:
            for prefix in ("primary", "robbery", "burglary", "primary_reported", "primary_nearest", "multiple_match",
                           "core_nearest", "core_multiple_match", "description_conflict"):
                name = f"{prefix}_count_{radius}m"
                row[name] = "" if prefix == "primary_reported" and row["city"] == "Chicago" else count[name]
            for subset in other_subsets:
                for prefix in ("nearest", "multiple_match"):
                    name = f"{subset}_{prefix}_count_{radius}m"
                    row[name] = count[name]
            row[f"primary_any_{radius}m"] = int(count[f"primary_count_{radius}m"] > 0)
            row[f"no_description_conflict_count_{radius}m"] = count[f"primary_count_{radius}m"] - count[f"description_conflict_count_{radius}m"]
        for name in ("background_unfiltered_200_500m", "background_primary_200_500m", "background_missing_invalid_report",
                     "background_late_report", "background_description_conflicts", "background_reported_description_conflicts"):
            row[name] = "" if name == "background_primary_200_500m" and row["city"] == "Chicago" else count[name]
        total = count["background_unfiltered_200_500m"]
        row["background_report_date_coverage"] = 1 - count["background_missing_invalid_report"] / total if total else ""
        row["background_has_unknown_availability"] = row["city"] == "Chicago" or count["background_missing_invalid_report"] > 0
        row["background_measurement_status"] = ("unavailable_original_report_dates" if row["city"] == "Chicago" else
                                                "incomplete_report_dates" if count["background_missing_invalid_report"] else "report_filtered_latest_extract")
        row.update(core_eligible=key in core, common_baseline="occurrence_year_latest_extract_retrospective",
                   physical_location_precision_verified=False, physical_identity_verified=False, base_release="restart6_0")
        for name, value in row.items():
            if name in old and name.startswith(("primary_", "robbery_", "burglary_", "background_", "multiple_match_")) and old[name] != str(value):
                try:
                    if float(old[name]) == float(value):
                        continue
                except ValueError:
                    pass
                changes.append({"row_id": key, "city": row["city"], "year": row["outcome_year"], "field": name,
                                "before": old[name], "after": value})
        revised_panels.append(row)
    write(QA / "panel_changes.csv", changes)
    monthly = []
    for old in records(BASE / "data/processed/atm_site_month_panel.csv"):
        rowid = old["annual_row_id"]
        if rowid not in byid:
            continue
        row = dict(old)
        count = months[(rowid, row["month"])]
        for radius in RADII:
            for prefix in ("primary", "robbery", "burglary", "primary_reported", "primary_nearest", "core_nearest", "description_conflict"):
                field = f"{prefix}_count_{radius}m"
                row[field] = "" if prefix == "primary_reported" and row["city"] == "Chicago" else count[field]
            row[f"primary_any_{radius}m"] = int(count[f"primary_count_{radius}m"] > 0)
        row["core_eligible"] = rowid in core
        monthly.append(row)
    write(DATA / "atm_site_month_panel.csv.gz", monthly)
    save(QA / "link_reuse.json", {"base_links_for_revised_rows": consumed, "retained_links": kept,
                                  "removed_links": consumed - kept, "global_spatial_matches_recomputed": 0,
                                  "new_source_downloads": 0, "monthly_rows": len(monthly)})
    print(f"Reused link distances: {kept} retained; updated {len(monthly)} site-month rows", flush=True)
    return revised_panels


def aggregate_prior(panels, removed, conflict_ids):
    pby = {r["row_id"]: r for r in panels}
    counts = {key: collections.Counter() for key in pby}
    retained = []
    for link in records(BASE / "results/phase3/data/prior_event_links.csv.gz"):
        if link["event_id"] in removed:
            continue
        retained.append(link)
        d = float(link["distance_m"])
        increments = (d <= 25, d <= 50, True, d <= 50 and link["category"] == "robbery",
                      d <= 50 and link["category"] == "burglary", d <= 50 and link["event_date"][5:7] >= "07")
        c = counts[link["row_id"]]
        known = link["report_available_by_cutoff"] == "True"
        for name, add in zip(LAGS, increments):
            c[name + "_unfiltered"] += int(add)
            c[name] += int(add and known)
        c["nearby_missing_report_date"] += link["report_date_usable"] != "True"
        c["nearby_late_report"] += link["report_date_usable"] == "True" and not known
        c["local_description_conflicts"] += d <= 50 and link["event_id"] in conflict_ids
        c["local_reported_description_conflicts"] += d <= 50 and link["event_id"] in conflict_ids and known
    write(DATA / "prior_event_links.csv.gz", retained)
    contexts = []
    changes = []
    availability = []
    for old in records(BASE / "results/phase3/data/site_context_raw.csv"):
        row = dict(old)
        p = pby[row["row_id"]]
        count = counts[row["row_id"]]
        row["background_primary"] = p["background_primary_200_500m"]
        row["background_unfiltered"] = p["background_unfiltered_200_500m"]
        for name in LAGS:
            row[name] = "" if p["city"] == "Chicago" else count[name]
            row[name + "_unfiltered"] = count[name + "_unfiltered"]
        row["local_description_conflicts"] = count["local_description_conflicts"]
        row["local_reported_description_conflicts"] = count["local_reported_description_conflicts"]
        for name in ("background_primary", "background_unfiltered") + LAGS + tuple(n + "_unfiltered" for n in LAGS):
            if old[name] == "" and row[name] == "":
                continue
            if float(old[name]) != float(row[name]):
                changes.append({"row_id": row["row_id"], "field": name, "before": old[name], "after": row[name]})
        contexts.append(row)
        availability.append({"row_id": row["row_id"], "city": p["city"], "prior_year": int(p["outcome_year"]) - 1,
                             "report_filtered_available": p["city"] != "Chicago",
                             "nearby_missing_report_date": count["nearby_missing_report_date"],
                             "nearby_late_report": count["nearby_late_report"],
                             "retrospective_count_available": True})
    write(FEATURES / "data/site_context_raw.csv", contexts)
    write(QA / "prior_feature_changes.csv", changes)
    write(QA / "prior_crime_availability.csv", availability)
    return {r["row_id"]: r for r in contexts}


def export_features(panels, contexts, quality, core, points, explicit, eligibility, removed):
    from pyproj import Transformer
    dictionary = read(BASE / "results/phase3/data/feature_dictionary.csv")
    env = [r for r in dictionary if r["source"] in spec()["primary_environment_sources"] and r["role"] == "primary"]
    assert len(env) == 19
    old_models = {}
    old_sensitivity = {}
    for suffix in ("full_year_2024_2025", "partial_2023"):
        old_models.update({r["row_id"]: r for r in read(BASE / f"results/phase3/data/features_primary_{suffix}.csv")})
        old_sensitivity.update({r["row_id"]: r for r in read(BASE / f"results/phase3/data/features_sensitivity_{suffix}.csv")})
    raw_environment = []
    for suffix in ("full_year_2024_2025", "partial_2023"):
        raw_environment += read(BASE / f"results/phase3_environment_expanded/environment_{suffix}.csv")
    raw_byid = {r["row_id"]: r for r in raw_environment}
    # Connected components are grouping safeguards, not adjudicated facilities.
    parent = {}
    def find(key):
        parent.setdefault(key, key)
        if parent[key] != key:
            parent[key] = find(parent[key])
        return parent[key]
    site_to_object = {p["site_id"]: p["city"] + "|" + p["osm_id"] for p in panels}
    for p in panels:
        find(site_to_object[p["site_id"]])
    for pair in records(BASE / "data/processed/qa/facility_review.csv"):
        if pair["site_a"] in site_to_object and pair["site_b"] in site_to_object:
            a, b = find(site_to_object[pair["site_a"]]), find(site_to_object[pair["site_b"]])
            parent[max(a, b)] = min(a, b)
    trans = {c: Transformer.from_crs(4326, epsg, always_xy=True) for c, epsg in zip(CITIES, (32618, 32616, 32611))}
    matrices = {"primary": [], "baseline": [], "report_filtered": [], "sensitivity": [], "no_source_conflicts": []}
    labels, lookups = [], []
    baseline = spec()["baseline_features"]
    for p in panels:
        rowid = p["row_id"]
        context = contexts[rowid]
        b = {"row_id": rowid, baseline[0]: math.log1p(float(context["prior_crime_50m_unfiltered"])),
             baseline[1]: math.log1p(float(context["background_unfiltered"]))}
        e = {f["predictor"]: old_models[rowid][f["predictor"]] for f in env}
        matrices["baseline"].append(b)
        matrices["primary"].append(b | e)
        reported = {"row_id": rowid}
        for output, source in (("log1p_prior_local_50m_report_filtered", "prior_crime_50m"),
                               ("log1p_prior_annulus_200_500m_report_filtered", "background_primary")):
            reported[output] = "" if context[source] == "" else math.log1p(float(context[source]))
        matrices["report_filtered"].append(reported | e)
        sensitive = {"row_id": rowid}
        for name in LAGS:
            sensitive["log1p_" + name + "_retrospective"] = math.log1p(float(context[name + "_unfiltered"]))
        for name in ("log1p_atm_density_500m", "log1p_nearest_other_atm"):
            sensitive[name] = old_models[rowid][name]
        for name in ("log1p_transit_centroid_distance", "log1p_transit_job_accessibility"):
            sensitive[name] = old_sensitivity[rowid][name]
        matrices["sensitivity"].append(sensitive)
        no_conflicts = {"row_id": rowid,
                       baseline[0]: math.log1p(float(context["prior_crime_50m_unfiltered"]) - context["local_description_conflicts"]),
                       baseline[1]: math.log1p(float(context["background_unfiltered"]) - p["background_description_conflicts"])}
        matrices["no_source_conflicts"].append(no_conflicts | e)
        label = {"row_id": rowid}
        for radius in RADII:
            label.update({f"recorded_count_{radius}m": p[f"primary_count_{radius}m"],
                          f"recorded_any_{radius}m": p[f"primary_any_{radius}m"],
                          f"reported_before_next_year_count_{radius}m": p[f"primary_reported_count_{radius}m"],
                          f"reported_before_next_year_any_{radius}m": "" if p[f"primary_reported_count_{radius}m"] == "" else int(p[f"primary_reported_count_{radius}m"] > 0),
                          f"no_source_conflicts_any_{radius}m": int(p[f"no_description_conflict_count_{radius}m"] > 0),
                          f"robbery_count_{radius}m": p[f"robbery_count_{radius}m"],
                          f"burglary_count_{radius}m": p[f"burglary_count_{radius}m"]})
        labels.append(label)
        x, y = trans[p["city"]].transform(float(p["longitude"]), float(p["latitude"]))
        object_id = p["city"] + "|" + p["osm_id"]
        lookups.append(quality[rowid] | {"acs_geoid_2022": context["acs_geoid_2022"], "sld_geoid_2019": context["sld_geoid_2019"],
            "core_eligible": rowid in core, "point_geometry_subset": rowid in points, "explicit_atm_core_subset": rowid in explicit,
            "exclusion_reasons": eligibility[rowid]["exclusion_reasons"], "object_group_id": object_id,
            "nearby_component_id": find(object_id), "spatial_block_2km": f"{p['city']}:{math.floor(x/2000)}:{math.floor(y/2000)}",
            "osm_geometry_is_centroid": p["osm_geometry_is_centroid"], "osm_amenity": p["osm_amenity"],
            "physical_identity_verified": False, "physical_location_precision_verified": False,
            "cohort_uses_future_mapping_presence": True, "common_crime_features_are_retrospective": True,
            "la_reporting_system_break": p["city"] == "Los Angeles", "base_release": "restart6_0"})
    main = {p["row_id"] for p in panels if p["outcome_year"] != "2023"}
    subsets = {"full_year_2024_2025": main, "core_2024_2025": core, "point_only_2024_2025": points,
               "explicit_atm_core_2024_2025": explicit, "partial_2023": {p["row_id"] for p in panels} - main}
    for year in ("2024", "2025"):
        subsets[f"core_{year}"] = {p["row_id"] for p in panels if p["row_id"] in core and p["outcome_year"] == year}
        subsets[f"full_year_{year}"] = {p["row_id"] for p in panels if p["outcome_year"] == year}
    for kind, rows in matrices.items():
        for name, ids in subsets.items():
            if kind in ("report_filtered", "sensitivity", "no_source_conflicts") and name not in ("full_year_2024_2025", "core_2024_2025", "partial_2023"):
                continue
            selected = [r for r in rows if r["row_id"] in ids]
            if kind == "report_filtered":
                selected = [r for r in selected if r["log1p_prior_local_50m_report_filtered"] != ""]
            write(FEATURES / f"data/features_{kind}_{name}.csv", selected, list(rows[0]))
    write(FEATURES / "data/outcomes.csv", labels)
    write(FEATURES / "data/site_lookup_and_quality.csv", lookups)
    for name, ids in subsets.items():
        selected = []
        for p in panels:
            if p["row_id"] not in ids:
                continue
            row = dict(p)
            # Core nearest assignments refer to the core, not the master cohort.
            subset_prefix = next((prefix for prefix in ("core", "point_only", "explicit_atm_core") if name.startswith(prefix + "_")), None)
            if subset_prefix:
                for radius in RADII:
                    row[f"primary_nearest_count_{radius}m"] = row[f"{subset_prefix}_nearest_count_{radius}m"]
                    row[f"multiple_match_count_{radius}m"] = row[f"{subset_prefix}_multiple_match_count_{radius}m"]
                row["nearest_assignment_population"] = subset_prefix
            else:
                row["nearest_assignment_population"] = "inherited_master"
            selected.append(row)
        write(DATA / f"atm_panel_{name}.csv", selected, list(panels[0]) + ["nearest_assignment_population"])
    metadata = ["row_id", "site_id", "city", "outcome_year", "longitude", "latitude", "cohort", "acs_geoid_2022", "sld_geoid_2019"]
    ed = read(BASE / "results/phase3_environment_expanded/environment_dictionary.csv")
    aliases = spec()["redundant_expanded_aliases"]
    proxies = spec()["exclude_expanded_city_proxies"]
    audit = []
    for alias, representative in aliases.items():
        assert all(r[alias] == r[representative] for r in raw_environment), (alias, representative)
    for f in ed:
        col = f["column"]
        reason = ("quality_flag_not_predictor" if f["role"] == "quality_flag" else "metropolitan_total_city_proxy" if col in proxies
                  else "redundant_alias" if col in aliases else "retained_exploratory")
        audit.append({"column": col, "decision": reason, "representative": aliases.get(col, ""),
                      "comparison_rows": len(raw_environment) if col in aliases else "", "outcomes_used": False})
    keep = [r["column"] for r in audit if r["decision"] == "retained_exploratory"]
    assert len(keep) == 107
    write(QA / "environment_column_decisions.csv", audit)
    write(FEATURES / "data/expanded_environment_dictionary.csv", [r for r in ed if r["column"] in keep])
    for name in ("full_year_2024_2025", "core_2024_2025", "partial_2023"):
        selected = [r for r in raw_environment if r["row_id"] in subsets[name]]
        write(FEATURES / f"data/environment_{name}.csv", ({k: r[k] for k in metadata + keep} for r in selected), metadata + keep)
        write(FEATURES / f"data/features_expanded_environment_{name}.csv", ({k: r[k] for k in ["row_id"] + keep} for r in selected), ["row_id"] + keep)
    feature_dict = []
    for name, formula in zip(baseline, ("log1p(retained prior calendar-year incidents <=50m)", "log1p(retained prior calendar-year incidents >200m and <=500m)")):
        feature_dict.append({"predictor": name, "role": "fixed_baseline", "formula": formula, "source": "corrected_cached_event_links",
                             "timing": "retrospective occurrence-year latest extract; original availability not asserted"})
    for f in env:
        feature_dict.append({"predictor": f["predictor"], "role": "environmental_extension", "formula": f["formula"],
                             "source": f["source"], "timing": "fixed inherited vintage; ACS unavailable in partial 2023"})
    write(FEATURES / "data/feature_dictionary.csv", feature_dict)
    save(FEATURES / "data/feature_schema.json", {"version": spec()["version"], "key": "row_id",
        "baseline_predictors": baseline, "environment_predictors": [f["predictor"] for f in env],
        "primary_predictors": baseline + [f["predictor"] for f in env], "expanded_environment_predictors": keep,
        "core_rows": len(core), "master_full_year_rows": len(main), "partial_2023_rows": len(panels) - len(main),
        "primary_endpoint": "recorded_any_50m", "endpoint_meaning": "released_coordinate_proximity; not_verified_physical_distance_or_ATM_attack",
        "report_filtered_sensitivity_cities": ["New York City", "Los Angeles"],
        "primary_information_regime": "retrospective_occurrence_year_for_all_three_cities",
        "imputation_performed": False, "scaling_performed": False, "models_fitted": False,
        "physical_location_precision_verified": False, "confirmatory_modeling_ready": False,
        "labels_file": "outcomes.csv", "lookup_file": "site_lookup_and_quality.csv",
        "expanded_environment_transform": "identity_raw_units", "primary_environment_transform": "inherited_frozen_log1p_or_identity"})
    write_summaries(panels, lookups, contexts, subsets)
    write(QA / "manual_linkage_audit.csv", (r | {"offense_retained": r["event_id"] not in removed,
            "row_in_revised_release": r["row_id"] in contexts, "row_in_core": r["row_id"] in core,
            "automated_rule_check": "excluded_vehicle_offense" if r["event_id"] in removed else "source_distance_retained",
            "physical_review_status": "PENDING"} for r in records(BASE / "data/processed/qa/manual_linkage_audit.csv")))
    print(f"Feature revision: {len(core)} core rows; 2 fixed baseline + 19 environment; 107 expanded supplement", flush=True)


def write_summaries(panels, lookups, contexts, subsets):
    lookup = {r["row_id"]: r for r in lookups}
    sample = []
    for name in ("full_year_2024_2025", "core_2024_2025", "point_only_2024_2025", "explicit_atm_core_2024_2025", "partial_2023"):
        for city in CITIES:
            for year in ("2023", "2024", "2025"):
                selected = [p for p in panels if p["row_id"] in subsets[name] and p["city"] == city and p["outcome_year"] == year]
                if not selected:
                    continue
                sample.append({"subset": name, "city": city, "year": year, "site_years": len(selected),
                    "unique_osm_objects": len({p["osm_id"] for p in selected}),
                    "unique_epa_block_groups": len({contexts[p["row_id"]]["sld_geoid_2019"] for p in selected} - {""}),
                    "spatial_blocks_2km": len({lookup[p["row_id"]]["spatial_block_2km"] for p in selected}),
                    "centroid_rows": sum(p["osm_geometry_is_centroid"] == "True" for p in selected),
                    **{f"positive_{r}m": sum(p[f"primary_any_{r}m"] for p in selected) for r in RADII},
                    "prevalence_50m": sum(p["primary_any_50m"] for p in selected) / len(selected)})
    write(QA / "sample_summary.csv", sample)
    repeated = []
    for name in ("full_year_2024_2025", "core_2024_2025"):
        for city in CITIES:
            selected = [p for p in panels if p["row_id"] in subsets[name] and p["city"] == city]
            byyear = {year: {p["osm_id"] for p in selected if p["outcome_year"] == year} for year in ("2024", "2025")}
            repeated.append({"subset": name, "city": city, "site_years": len(selected),
                "unique_osm_objects": len(byyear["2024"] | byyear["2025"]), "objects_in_both_years": len(byyear["2024"] & byyear["2025"]),
                "unique_epa_block_groups": len({contexts[p["row_id"]]["sld_geoid_2019"] for p in selected} - {""}),
                "independent_sample_size": "not_established; site_years_and_geographies_are_repeated"})
    write(QA / "repeated_units.csv", repeated)
    missing = []
    for name in ("full_year_2024_2025", "core_2024_2025", "partial_2023"):
        matrix = read(FEATURES / f"data/features_primary_{name}.csv")
        for city in CITIES:
            for year in ("2023", "2024", "2025"):
                rows = [r for r in matrix if lookup[r["row_id"]]["city"] == city and str(lookup[r["row_id"]]["outcome_year"]) == year]
                if rows:
                    for col in matrix[0]:
                        if col != "row_id":
                            missing.append({"subset": name, "city": city, "year": year, "predictor": col,
                                            "rows": len(rows), "missing": sum(r[col] == "" for r in rows)})
    write(QA / "feature_missingness.csv", missing)


def main():
    freeze()
    verify_inputs()
    save(QA / "status.json", {"status": "BUILDING", "models_fitted": False, "scientific_review": "PENDING"})
    panels = read(BASE / "data/processed/atm_panel_full_year_2024_2025.csv") + read(BASE / "data/processed/atm_panel_partial_2023.csv")
    quality = {r["row_id"]: r for r in read(BASE / "results/phase3/data/site_lookup_and_quality.csv")}
    _, removed, conflicts = classify_events()
    core, points, explicit, eligibility = cohort_rules(panels, quality)
    panels = aggregate_links(panels, core, points, explicit, removed, conflicts)
    contexts = aggregate_prior(panels, removed, conflicts)
    export_features(panels, contexts, quality, core, points, explicit, eligibility, removed)
    assert_inputs_unchanged()
    save(QA / "status.json", {"status": "BUILT_AWAITING_VALIDATION", "models_fitted": False,
                             "scientific_review": "PENDING", "confirmatory_eligible": False})


if __name__ == "__main__":
    main()
