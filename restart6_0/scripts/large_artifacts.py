"""Store oversized generated CSVs as byte-exact, checksum-verified parts.

Usage from the repository root:
  python restart6_0/scripts/large_artifacts.py split
  python restart6_0/scripts/large_artifacts.py verify
  python restart6_0/scripts/large_artifacts.py restore [repository-relative CSV path ...]
"""

import argparse
import hashlib
import json
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "large_artifacts.json"
PART_BYTES = 64_000_000
FILES = (
    "data/processed/crime_primary_2022_2025.csv",
    "data/processed/event_atm_links.csv",
)


def digest(path):
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def entries():
    data = json.loads(MANIFEST.read_text())
    assert data["format"] == "byte_concat_v1"
    assert set(data["files"]) == set(FILES)
    return data["files"]


def verify_parts(entry):
    total = 0
    for part in entry["parts"]:
        path = ROOT / part["file"]
        assert path.is_file(), path
        assert path.stat().st_size == part["bytes"], path
        assert digest(path) == part["sha256"], path
        total += part["bytes"]
    assert total == entry["bytes"], entry


def restore(names=None):
    catalog = entries()
    for name in names or FILES:
        if name not in catalog:
            raise ValueError(f"Unmanaged large artifact: {name}")
        entry = catalog[name]
        target = ROOT / name
        if target.is_file():
            assert target.stat().st_size == entry["bytes"] and digest(target) == entry["sha256"], target
            continue
        verify_parts(entry)
        temporary = target.with_name(target.name + ".restoring")
        try:
            with temporary.open("wb") as output:
                for part in entry["parts"]:
                    with (ROOT / part["file"]).open("rb") as source:
                        for block in iter(lambda: source.read(1024 * 1024), b""):
                            output.write(block)
            assert temporary.stat().st_size == entry["bytes"] and digest(temporary) == entry["sha256"], target
            os.replace(temporary, target)
        finally:
            temporary.unlink(missing_ok=True)


def split():
    catalog = {}
    for name in FILES:
        source = ROOT / name
        if not source.is_file():
            raise FileNotFoundError(source)
        parts = []
        with source.open("rb") as stream:
            for number, block in enumerate(iter(lambda: stream.read(PART_BYTES), b""), 1):
                part = source.with_name(f"{source.name}.part{number:03d}")
                part.write_bytes(block)
                parts.append({"file": str(part.relative_to(ROOT)), "bytes": len(block), "sha256": digest(part)})
        assert parts and sum(p["bytes"] for p in parts) == source.stat().st_size
        catalog[name] = {"bytes": source.stat().st_size, "sha256": digest(source), "parts": parts}
    MANIFEST.write_text(json.dumps({"format": "byte_concat_v1", "part_bytes": PART_BYTES, "files": catalog}, indent=2) + "\n")
    for entry in entries().values():
        verify_parts(entry)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["split", "verify", "restore"])
    parser.add_argument("files", nargs="*")
    args = parser.parse_args()
    if args.action == "split":
        if args.files:
            parser.error("split manages the complete fixed file list")
        split()
    elif args.action == "verify":
        if args.files:
            parser.error("verify manages the complete fixed file list")
        for entry in entries().values():
            verify_parts(entry)
    else:
        restore(args.files)
    print(f"Large artifact {args.action}: PASS")


if __name__ == "__main__":
    main()
