"""Small local utilities; Restart 6 is always read-only input."""
import contextlib
import csv
import gzip
import hashlib
import io
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PROJECT = ROOT.parent
BASE = PROJECT / "restart6_0"
DATA = ROOT / "data/processed"
QA = ROOT / "qa"
FEATURES = ROOT / "results/phase3"
CITIES = ("New York City", "Chicago", "Los Angeles")
RADII = (25, 50, 100)
LAGS = ("prior_crime_25m", "prior_crime_50m", "prior_crime_100m",
        "prior_robbery_50m", "prior_burglary_50m", "prior_recent_crime_50m")


def sha(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


@contextlib.contextmanager
def csv_stream(path, mode="r"):
    path = Path(path)
    if mode == "w":
        path.parent.mkdir(parents=True, exist_ok=True)
    if path.suffix == ".gz" and mode == "w":
        with path.open("wb") as raw:
            with gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0) as zipped:
                with io.TextIOWrapper(zipped, encoding="utf-8", newline="") as text:
                    yield text
    elif path.suffix == ".gz":
        with gzip.open(path, "rt", encoding="utf-8-sig", newline="") as stream:
            yield stream
    else:
        with path.open(mode, encoding="utf-8-sig" if mode == "r" else "utf-8", newline="") as stream:
            yield stream


def records(path):
    with csv_stream(path) as stream:
        yield from csv.DictReader(stream)


def read(path):
    return list(records(path))


def write(path, rows, fields=None):
    rows = iter(rows)
    first = next(rows, None)
    if fields is None:
        if first is None:
            raise ValueError(f"Empty output requires fields: {path}")
        fields = list(first)
    with csv_stream(path, "w") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        if first is not None:
            writer.writerow(first)
        writer.writerows(rows)


def save(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, allow_nan=False) + "\n")


def spec():
    return json.loads((ROOT / "protocol/revision.json").read_text())


def excluded(event, rules=None):
    rules = rules or spec()["exclude_native_codes"]
    code = event["native_code"]
    if event["city"] == "Chicago":
        code = code.zfill(4)
    return code in rules.get(event["city"], [])


def freeze():
    paths = sorted((ROOT / "protocol").glob("*"))
    hashes = {str(p.relative_to(ROOT)): sha(p) for p in paths if p.is_file()}
    target = QA / "protocol_freeze.json"
    if target.exists():
        if json.loads(target.read_text())["files"] != hashes:
            raise RuntimeError("Frozen protocol changed; record a new revision before rebuilding")
    else:
        save(target, {"version": spec()["version"], "files": hashes,
                      "status": "retrospective_working_specification", "scientific_approval": "PENDING"})


INPUTS = [
    "data/processed/atm_panel_full_year_2024_2025.csv",
    "data/processed/atm_panel_partial_2023.csv",
    "data/processed/atm_site_month_panel.csv",
    "data/processed/event_atm_links.csv",
    "data/processed/crime_primary_2022_2025.csv",
    "data/processed/crime_codebook.csv",
    "data/processed/qa/crime_duplicates.csv",
    "data/processed/qa/facility_review.csv",
    "data/processed/qa/manual_linkage_audit.csv",
    "data/processed/qa/research_review_gates.csv",
    "results/phase3/data/site_context_raw.csv",
    "results/phase3/data/site_lookup_and_quality.csv",
    "results/phase3/data/feature_dictionary.csv",
    "results/phase3/data/prior_event_links.csv.gz",
    "results/phase3/data/features_primary_full_year_2024_2025.csv",
    "results/phase3/data/features_primary_partial_2023.csv",
    "results/phase3/data/features_sensitivity_full_year_2024_2025.csv",
    "results/phase3/data/features_sensitivity_partial_2023.csv",
    "results/phase3/data/atm_neighbor_links.csv",
    "results/phase3/qa/prior_crime_availability.csv",
    "results/phase3/qa/spatial_join_audit.csv",
    "results/phase3_environment_expanded/environment_full_year_2024_2025.csv",
    "results/phase3_environment_expanded/environment_partial_2023.csv",
    "results/phase3_environment_expanded/environment_dictionary.csv",
]


def verify_inputs():
    """Verify only consumed artifacts, using existing release hashes as anchors."""
    expected = {}
    manifest_paths = [(BASE / "reports/artifact_manifest.csv", BASE),
                      (BASE / "results/phase3/qa/output_manifest.csv", PROJECT),
                      (BASE / "results/phase3_environment_expanded/output_manifest.csv", PROJECT)]
    for manifest, base in manifest_paths:
        for row in records(manifest):
            expected[(base / row["file"]).resolve()] = row
    large = json.loads((BASE / "large_artifacts.json").read_text())["files"]
    for name, entry in large.items():
        expected[(BASE / name).resolve()] = entry
    rows = []
    for name in INPUTS:
        path = BASE / name
        if not path.exists():
            raise FileNotFoundError(f"Missing base artifact {path}; restore Restart 6 large artifacts if needed")
        reference = expected[path.resolve()]
        digest = sha(path)
        if digest != reference["sha256"] or path.stat().st_size != int(reference["bytes"]):
            raise RuntimeError(f"Restart 6 artifact changed: {path}")
        rows.append({"file": str(path.relative_to(PROJECT)), "bytes": path.stat().st_size,
                     "sha256": digest, "action": "reuse_verified_artifact"})
    for path, _ in manifest_paths:
        rows.append({"file": str(path.relative_to(PROJECT)), "bytes": path.stat().st_size,
                     "sha256": sha(path), "action": "provenance_manifest"})
    for path in [BASE / "large_artifacts.json", PROJECT / "PAPER_REVIEW.md"]:
        rows.append({"file": str(path.relative_to(PROJECT)), "bytes": path.stat().st_size,
                     "sha256": sha(path), "action": "revision_or_provenance_input"})
    target = QA / "input_manifest.csv"
    if target.exists() and read(target) != [{k: str(v) for k, v in r.items()} for r in rows]:
        raise RuntimeError("Frozen revision inputs changed")
    write(target, rows)
    return rows


def assert_inputs_unchanged():
    for row in records(QA / "input_manifest.csv"):
        path = PROJECT / row["file"]
        if path.stat().st_size != int(row["bytes"]) or sha(path) != row["sha256"]:
            raise RuntimeError(f"Input modified during revision: {path}")
