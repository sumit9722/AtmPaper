"""Describe the completed revision, its reuse, and unresolved scientific gates."""
import json
from common import *


def markdown_table(rows, columns):
    return "\n".join(["| " + " | ".join(columns) + " |", "| " + " | ".join("---" for _ in columns) + " |"] +
                     ["| " + " | ".join(str(r[c]) for c in columns) + " |" for r in rows])


def main():
    validation = json.loads((QA / "validation.json").read_text())
    assert validation["status"] == "PASS"
    schema = json.loads((FEATURES / "data/feature_schema.json").read_text())
    sample = read(QA / "sample_summary.csv")
    core = [r for r in sample if r["subset"] == "core_2024_2025"]
    repeated = [r for r in read(QA / "repeated_units.csv") if r["subset"] == "core_2024_2025"]
    unique_objects = sum(int(r["unique_osm_objects"]) for r in repeated)
    block_groups = sum(int(r["unique_epa_block_groups"]) for r in repeated)
    table = markdown_table(core, ["city", "year", "site_years", "positive_50m", "unique_epa_block_groups"])
    revisions = [
        {"review_item": "Environmental gain versus weak baseline", "action": "Fixed prior-local-50m + prior-annulus baseline; 19 environment extension; direct-lag benchmark committed",
         "status": "IMPLEMENTED_PHASE1_3; predictive_test_not_run", "evidence": "results/phase3/data/feature_schema.json"},
        {"review_item": "Spatial precision and bank centroids", "action": "Core excludes nonpoints, >10m drift, close objects and truncated annuli; physical-distance claim removed",
         "status": "MITIGATED_NOT_VALIDATED; precise_incident_and_ATM_positions_unavailable", "evidence": "qa/cohort_eligibility.csv"},
        {"review_item": "Missing Chicago original report dates", "action": "Common retrospective occurrence-year regime in every city; separate NYC/LA report-filtered matrix",
         "status": "RETROSPECTIVE_DESIGN_IMPLEMENTED; historical_availability_not_reconstructed", "evidence": "results/phase3/data/features_baseline_core_2024_2025.csv"},
        {"review_item": "Vehicle burglary mismatch", "action": "Excluded NYC 231/233/234 and Chicago 0760 from outcomes and all lags; preserved excluded cases",
         "status": "IMPLEMENTED; remaining_codebook_review_pending", "evidence": "qa/crime_conservation.csv"},
        {"review_item": "Transfer selector fallback", "action": "Freeze identical two-feature baseline in all future local/source models; no selection removes local crime",
         "status": "FUTURE_MODEL_PROTOCOL_FIXED; no_transfer_models_fitted", "evidence": "protocol/study_spec.md"},
        {"review_item": "Feature redundancy and city proxies", "action": "Removed 6 verified aliases and 3 metropolitan totals from expanded predictors; mapped competition moved to sensitivity",
         "status": "IMPLEMENTED; other_correlations_require_training_only_handling", "evidence": "qa/environment_column_decisions.csv"},
        {"review_item": "Repeated units and unresolved identity", "action": "Publish stable object/component/geography groups, paired-year counts and pending review queues",
         "status": "GROUPING_IMPLEMENTED; physical_identity_review_pending", "evidence": "qa/repeated_units.csv"},
        {"review_item": "Previously inspected years and different older studies", "action": "Declare retrospective exploratory status; no older model performance carried forward",
         "status": "DISCLOSED; untouched_holdout_unavailable", "evidence": "protocol/study_spec.md"},
    ]
    write(QA / "review_resolution.csv", revisions)
    gates = [
        {"gate": "Crime position accuracy", "status": "PENDING_EXTERNAL_EVIDENCE", "reason": "Block geocodes cannot establish physical 25/50/100m distances; core restrictions do not repair them."},
        {"gate": "ATM identity and operation", "status": "PENDING_INDEPENDENT_REVIEW", "reason": "Bank points and ATM nodes are mapped objects; no verified machine position or operating history."},
        {"gate": "OSM representativeness and survivor selection", "status": "OPEN_LIMITATION", "reason": "Incomplete map inventory and future continuity requirements remain; report cohort attrition."},
        {"gate": "Crime source ascertainment and harmonization", "status": "PENDING_INDEPENDENT_REVIEW", "reason": "Vehicle categories corrected; native source-code/description conflicts and other codebook decisions need review."},
        {"gate": "LA reporting transition and cross-system case identity", "status": "PENDING_SOURCE_REVIEW", "reason": "No authoritative ID crosswalk or complete temporal comparability was added."},
        {"gate": "Chicago historical report availability", "status": "UNAVAILABLE_WITH_CURRENT_SOURCE", "reason": "Common study is retrospective; Chicago report-filtered data remain missing."},
        {"gate": "Human facility and linkage review", "status": "PENDING", "reason": "Original reviewer decisions are preserved; automated checks do not constitute adjudication."},
        {"gate": "Prospective or confirmatory evaluation", "status": "NOT_AVAILABLE", "reason": "Both full outcome years previously inspected; phases4/5 not executed."},
    ]
    write(QA / "research_review_gates.csv", gates)
    reuse = [
        {"component": "OSM histories and exposure", "source": "restart6_0/data/processed/atm_panel_*", "action": "Reuse rows, identity, coordinates, intervals and exposure; create eligibility views"},
        {"component": "Crime records", "source": "restart6_0/data/processed/crime_primary_2022_2025.csv", "action": "Filter specified vehicle codes; preserve every remaining source value"},
        {"component": "Event distances", "source": "restart6_0/data/processed/event_atm_links.csv", "action": "Reuse distances; remove excluded offenses; aggregate counts and subset-specific nearest assignments"},
        {"component": "Prior-crime distances", "source": "restart6_0/results/phase3/data/prior_event_links.csv.gz", "action": "Reuse distances; reaggregate corrected prior counts"},
        {"component": "Monthly exposure", "source": "restart6_0/data/processed/atm_site_month_panel.csv", "action": "Preserve supported months/days for revised cohorts; update counts"},
        {"component": "ACS/SLD spatial joins and values", "source": "restart6_0/results/phase3/data", "action": "Reuse exact values and transforms; no new joins or acquisition"},
        {"component": "Expanded environment", "source": "restart6_0/results/phase3_environment_expanded", "action": "Reuse values; exclude predetermined duplicate aliases and regional totals"},
        {"component": "Validation", "source": "restart7_0/scripts/validate.py", "action": "Replay corrected artifacts and direct-geodesic audit of 18 sampled sites"},
    ]
    write(QA / "reuse_register.csv", reuse)
    changes = read(QA / "panel_changes.csv")
    flipped = [r for r in changes if r["field"] == "primary_any_50m" and r["year"] != "2023"]
    summary_rows = []
    for city in CITIES:
        for year in ("2024", "2025"):
            summary_rows.append({"city": city, "year": year,
                                 "positive_to_negative_50m": sum(r["city"] == city and r["year"] == year and r["before"] == "1" and r["after"] == "0" for r in flipped)})
    write(QA / "label_changes_summary.csv", summary_rows)
    reports = ROOT / "reports"
    reports.mkdir(exist_ok=True)
    (ROOT / "README.md").write_text(f"""# Restart 7 — review fixes through phases 1–3

Computationally complete and validated. Built incrementally from verified
Restart 6 artifacts; **no source downloads, global spatial rematching or model
fitting**. Scientific review remains pending.

- Corrected master: **2,731 full-year site-years**, 2024–2025.
- Conservative core: **{schema['core_rows']:,} site-years**, {unique_objects:,} distinct OSM objects.
- Separate partial-2023 supplement: **1,287 rows**.
- **{validation['excluded_vehicle_cases']:,} vehicle-burglary cases** excluded consistently from outcomes and prior crime.
- Primary matrix: **2 fixed crime predictors + 19 environmental predictors**.
- Expanded exploratory supplement: **107 environmental predictors**, after removing six redundant aliases and three city proxies.

{table}

The core excludes centroids, unresolved close objects, coordinate drift >10 m
and boundary-truncated background buffers. Point bank objects tagged with ATMs
remain mapped locations, not verified machine positions. All three cities use
the same explicitly retrospective crime baseline. Report-filtered NYC/LA
matrices are separate sensitivities; Chicago's report dates are not invented.

The 50 m endpoint describes proximity to **released coordinates**. Physical
distance accuracy, ATM operation and ATM targeting are unverified. No radius
has been certified. The surviving cohort and old environmental vintages remain
retrospective limitations; this release establishes no predictive improvement.

[Execution report](reports/phase_1_2_3_report.md) ·
[Methods](reports/methods.md) · [Reproduce](reports/reproduce.md) ·
[Review resolution](qa/review_resolution.csv) · [Validation](qa/validation.json) ·
[Remaining scientific gates](qa/research_review_gates.csv)

[Core panel](data/processed/atm_panel_core_2024_2025.csv) ·
[Corrected full panel](data/processed/atm_panel_full_year_2024_2025.csv) ·
[Core feature matrix](results/phase3/data/features_primary_core_2024_2025.csv) ·
[Feature schema](results/phase3/data/feature_schema.json) ·
[Outcomes](results/phase3/data/outcomes.csv) ·
[Lookup and grouping keys](results/phase3/data/site_lookup_and_quality.csv)

```bash
.venv/bin/python restart7_0/scripts/run_all.py
```

This is a dependent incremental release: keep the referenced Restart 6 files.
Original cached source paths are interpreted relative to Restart 6 when their
`source_path_base` is `release_root`, and relative to the repository when it is
`project_root`. Input/output manifests and a reuse register document the chain.

OSM © OpenStreetMap contributors, [ODbL](https://www.openstreetmap.org/copyright),
via HeiGIT ohsome. See [source decisions](protocol/source_decisions.md).
""")
    (reports / "phase_1_2_3_report.md").write_text(f"""# Restart 7 execution report

## Phase 1 — revised design

[Study specification](../protocol/study_spec.md) freezes the retrospective
three-city coordinate-proximity question, offense correction, conservative
cohort rules, common information regime and stronger future baseline. This
revision follows the repository review; it is not a preregistration. No earlier
model result is attributed to this revised cohort.

## Phase 2 — corrected panels

Reused 4,018 main/partial rows without changing their exposure, coordinates or
historical identity. Removed {validation['excluded_vehicle_cases']:,} vehicle-burglary cases from
278,394 inherited cases, leaving {validation['retained_cases']:,}. This includes Chicago
IUCR 0760 as well as NYC truck-burglary codes. The changes apply to outcomes,
annular background, prior local crime and monthly counts.

{markdown_table(read(QA / 'crime_conservation.csv'), ['city', 'year', 'base_cases', 'excluded_vehicle_cases', 'retained_cases'])}

At 50 m, {len(flipped)} full-year master labels change from positive to negative:

{markdown_table(summary_rows, ['city', 'year', 'positive_to_negative_50m'])}

These are offense-only changes on the same inherited sites; they do not combine
the effect of cohort exclusions with the offense change.

The core contains {schema['core_rows']:,} site-years across {unique_objects:,} distinct mapped
OSM objects and {block_groups:,} EPA block groups. These are repeated observational
units, not independent samples. Point-only and explicit-ATM-tag views are also
available; alternative views must not be stacked. Nearest assignments use the
eligible sites within each view.

{table}

The full master remains available for sensitivity. The source review identified
five LA burglary-code records with inconsistent descriptions; their native
classification is retained and a separate exclusion sensitivity is supplied.
This is flagged evidence, not an invented replacement offense. All original
632 facility-pair review records and 1,205 sampled linkage-review records retain
their human-review status. Core exclusions mitigate selected issues without
claiming that a human has adjudicated them.

## Phase 3 — usable feature specifications

The common baseline is fixed prior local crime within 50 m plus prior annular
crime at >200–500 m, both log1p transformed and both occurrence-year counts from
the latest cached extract in all three cities. The primary extension adds the
same 19 inherited ACS/SLD environmental predictors. The original mapped-ATM
competition measures are sensitivity variables, not facility-verified density.

Separate NYC/LA report-filtered matrices retain historical-report-date rules.
They are not combined with Chicago unfiltered predictors. Exported training-label
sensitivities identify reports before the following January 1. Neither filtering
nor these matrices establish an archived historical database.

The expanded exploratory export contains 107 predictors, dropping six exact
aliases and the three metropolitan totals. All retained environmental values and
the primary transforms are inherited unchanged. No imputation, scaling,
selection against outcomes, or modeling occurred. Partial 2023 retains missing
ACS and ATM-competition values.

## Validation and remaining limits

{len(validation['checks'])} automated validation groups passed: input integrity,
unchanged exposure, offense conservation, independent cohort membership,
complete link/count replay, all subset nearest assignments, monthly reconciliation,
prior-cutoff rules, an independent geodesic omission check of 18 sites,
feature/label alignment, and preservation of human-review status.

Block-geocode accuracy, actual ATM identity/operation, mapping coverage, survivor
selection, LA source comparability and independent codebook review remain open.
The untouched later test period is absent. Phases 4–5 were not run. The result is
a corrected, reproducible exploratory data release, not certified ATM risk data.

See [review-by-review decisions](../qa/review_resolution.csv),
[sample/attrition tables](../qa/cohort_attrition.csv),
[changed cells](../qa/panel_changes.csv), and
[validation](../qa/validation.json).
""")
    (reports / "methods.md").write_text("""# Methods and interpretation

The [frozen specification](../protocol/study_spec.md) defines the revision.
Raw observations, historical membership and geodesic distances are inherited
from Restart 6. The input manifest verifies the exact consumed artifacts against
the base release's recorded hashes. The revision performs no global spatial
search. A small direct-geodesic sample checks omissions independently.

Excluded NYC truck-burglary and Chicago motor-vehicle-burglary cases are removed
from both outcome and prior-year links. Counts are replayed from retained links.
The duplicated-case audit confirms that no excluded winning case hides an eligible
discarded alternative. LA source-code/description contradictions are flagged;
the supplementary no-source-conflicts matrix and labels omit those same cases
from both baseline and outcome. Structural offense comparability still needs
independent review.

The conservative subset consists of full-year point objects with <=10 m inherited
drift, a clear inherited 500 m municipal buffer and no other object within 10 m
in either the annual facility audit or prior-December inventory. The historical
inventory includes objects that do not survive the outcome year. These safeguards
reduce centroid, co-location and boundary concerns, but do not validate physical
ATM locations. `amenity=bank, atm=yes` point objects remain in the core; the
explicit-ATM-tag sensitivity excludes them.

Counts at each site retain all qualifying nearby cases. Nearest-site assignment
is a separate sensitivity recomputed within the master, point-only, conservative
core and explicit-ATM core populations using cached distances. A single crime
may still label several sites in the main endpoint. Stable OSM IDs, nearby-object
components, 2 km projected blocks and source block-group IDs are metadata for
future grouped evaluation; components do not certify physical identity. No folds
or models have been fitted.

Primary crime predictors are uniformly retrospective occurrence-year quantities.
The NYC/LA report-filtered sensitivity uses usable report dates strictly before
January 1; report-filtered training-label alternatives use the next January 1.
Chicago values are never filled with zero. The common baseline's complete values
do not imply that they were available in real time. Full-year inclusion still
uses future OSM mapping presence and therefore selects a survivor population.

Main environmental matrices retain the inherited 19 deterministic transforms;
expanded matrices retain raw units. The expanded field decisions were specified
before this build and verified against all 4,018 inherited rows without using
outcome values. Their removal does not guarantee independence of the remaining
fields. Any later scaling, missing-value handling or feature search must happen
inside training folds. Partial 2023 remains distinct and lacks 11 ACS and two
ATM-competition quantities at its cutoff.

EPA/ACS are neighborhood context from fixed older vintages. They do not measure
ATM visibility, lighting, security, foot traffic or use. Outcome labels measure
released-coordinate proximity; they do not establish ATM targeting or the effect
of an ATM's presence. No non-ATM controls or causal identification were added.

Original source record paths refer to Restart 6 for `release_root`, or the
repository for `project_root`. OSM attribution and all source decisions are in
[the source notes](../protocol/source_decisions.md).
""")
    (reports / "reproduce.md").write_text("""# Reproduce the incremental release

From the repository root:

```bash
.venv/bin/python restart7_0/scripts/run_all.py
```

Install `restart7_0/requirements.txt` in a Python environment if necessary.
The runner executes rule regression tests, verifies the frozen base inputs,
rebuilds only the revision, independently validates it and regenerates reports
and output checksums. It has no network/acquisition option and fits no models.

Keep the consumed Restart 6 outputs listed in `qa/input_manifest.csv`, the base
artifact manifests, and `PAPER_REVIEW.md`. If a checkout lacks the two original
large CSVs, restore them using Restart 6's checksum-verified parts first:

```bash
.venv/bin/python restart6_0/scripts/large_artifacts.py restore
```

The new large tables use deterministic gzip compression and need no splitting.
All retained environmental values, exposure fields and distance links come from
the base release. Incremental reproduction does not require reimporting ACS,
downloading OSM or rerunning Restart 6. To audit the entire upstream source
construction, follow Restart 6's separate reproduction instructions.

Validate an existing build without rebuilding:

```bash
.venv/bin/python restart7_0/scripts/validate.py
.venv/bin/python restart7_0/scripts/verify_release.py
```

For modeling, use explicit predictor lists from the feature schema. The primary
core matrix has two fixed crime features and 19 environmental features; labels
join through `row_id` to `outcomes.csv`. The metadata lookup contains city, year,
OSM/component/geographic grouping keys and quality flags. Never select all numeric
columns from a panel as predictors. Report-filtered matrices contain NYC/LA only.
Use report-filtered training labels in that sensitivity. 2023 is partial and
must not be pooled with annual binary outcomes.

Changes to frozen protocol/input files fail instead of silently refreshing a
release. The manifest is a reproducibility record, not independent scientific
approval. Rerunning does not adjudicate human review queues or create a new
uninspected holdout.
""")
    (FEATURES / "README.md").write_text("""# Restart 7 Phase 3

Use [the schema](data/feature_schema.json) and
[primary core matrix](data/features_primary_core_2024_2025.csv).
The baseline contains two fixed crime-history predictors; the extension adds
19 inherited ACS/SLD predictors. [Core baseline](data/features_baseline_core_2024_2025.csv)
and separate 2024/2025 files are available.

[Outcomes](data/outcomes.csv) and [metadata](data/site_lookup_and_quality.csv)
join by `row_id`. The primary endpoint is `recorded_any_50m`, defined using
released coordinates. It is not verified ATM-targeted crime or exact physical
proximity. Repeated-site and spatial grouping keys belong to evaluation metadata.

[Report-filtered sensitivity](data/features_report_filtered_core_2024_2025.csv)
uses only NYC/LA; Chicago's original report dates remain unavailable.
[Source-conflict sensitivity](data/features_no_source_conflicts_core_2024_2025.csv)
must be paired with `no_source_conflicts_any_50m` in the outcomes table.
[Other sensitivity predictors](data/features_sensitivity_core_2024_2025.csv)
include alternative crime radii, mapped-object competition and transit measures.

[Expanded environment](data/features_expanded_environment_core_2024_2025.csv)
contains 107 untransformed exploratory fields. It does not include crime
predictors; join explicitly to the baseline if later authorized. Do not mix raw
and transformed versions of the same variable without an explicit specification.
Full-cohort and partial-2023 versions are separate exports.

[Missingness](../../qa/feature_missingness.csv),
[column decisions](../../qa/environment_column_decisions.csv),
[sample replication](../../qa/repeated_units.csv),
[methods](../../reports/methods.md), and [reproduction](../../reports/reproduce.md).
No imputation, scaling or models were fitted. Scientific review remains pending.
""")
    save(QA / "status.json", {"status": "COMPUTATIONALLY_COMPLETE", "phase1": "SPECIFIED_EXPLORATORY",
        "phase2": "CORRECTED_AND_VALIDATED", "phase3": "CORRECTED_AND_VALIDATED",
        "core_rows": schema["core_rows"], "main_rows": 2731, "partial_rows": 1287,
        "validation_groups": len(validation["checks"]), "scientific_review": "PENDING",
        "confirmatory_eligible": False, "models_fitted": False, "base_release": "restart6_0"})
    assert_inputs_unchanged()
    paths = sorted(p for p in ROOT.rglob("*") if p.is_file() and "__pycache__" not in p.parts
                   and p != QA / "output_manifest.csv")
    write(QA / "output_manifest.csv", [{"file": str(p.relative_to(ROOT)), "bytes": p.stat().st_size, "sha256": sha(p)} for p in paths])
    print(f"Reports and manifest completed: {len(paths)} files", flush=True)


if __name__ == "__main__":
    main()
