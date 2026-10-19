# Reproduction and checks

## 1. Verify the input release

Start with completed phases 1–3 in this folder. Phase 3 validation must be PASS and its output hashes must match. Preserve `protocol/phase4_analysis_spec.md` and the phase 3 allowlist. No external downloads, API credentials or parent-project data are required.

## 2. Prepare the environment

The existing repository `.venv` contains the required packages. For a standalone copy, create an environment and install `requirements-phase4.txt`. Package versions and Python version from the actual run are recorded in `qa/run_environment.json`. Do not use Python `-O`, which disables validation assertions.

## 3. Freeze splits before fitting

From the repository root:

```bash
.venv/bin/python restart_3_0/scripts/run_phase4.py --prepare-only
```

This verifies phase 3, freezes the protocol, generates both annual block assignments, outer/inner membership, separation diagnostics and experiment registry. It does not fit models. The frozen split hashes must match on subsequent runs. It deliberately invalidates previous phase 4 validation; finish the remaining steps before treating the release as complete.

## 4. Run all registered experiments

```bash
.venv/bin/python restart_3_0/scripts/run_phase4.py
```

This also verifies/prepares the same frozen splits, then executes all 47 outer evaluations, nested tuning, 141 final fold fits, calibration, metric aggregation and paired block bootstrap. It uses one thread per model and prints progress for every completed outer evaluation. An interrupted run is incomplete; rerun the command to recompute the full registered set. It is not a model-cache resume command. A changed specification or split fails the freeze check and requires a documented version amendment; do not silently delete freezes to change the analysis.

## 5. Validate independently

```bash
.venv/bin/python restart_3_0/scripts/validate_phase4.py
```

The validator recomputes distances and checks all outer/inner memberships, temporal and city isolation, fitted preprocessing, all 141 model artifacts and predictions, selection/calibration records, metrics and bootstrap intervals. It does not rerun every inner model fit. Review `qa/validation.json` and `qa/fit_warnings.csv`.

## 6. Generate the report and figures

```bash
.venv/bin/python restart_3_0/scripts/report_phase4.py
```

Reporting requires validation PASS, creates the Markdown documents and PNG/PDF figures, updates restart phase status, and hashes the final outputs and implementation files. For a standalone folder use `python scripts/...` instead of the repository-prefixed commands. The plotting cache is placed in `/tmp`.

## 7. Review the scientific gate

Read the primary native-probability comparisons first, then city-specific and sensitivity results and calibration. The working improvement rule is AP gain >=0.01 with lower paired 95% bound >0. Independent research approval remains pending even if this flag passes. No phase 5 transfer/adaptation or deployment is authorized by running this workflow.

Input hashes are relative to the restart root. Output hashes are relative to `results/phase4`. Recompute SHA-256 and compare the manifest columns to detect changes. Only load the trusted joblib artifacts created by this workflow.
