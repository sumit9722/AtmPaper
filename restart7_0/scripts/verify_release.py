"""Read-only integrity check of an already generated incremental release."""
from common import *


def main():
    assert_inputs_unchanged()
    entries = read(QA / "output_manifest.csv")
    for entry in entries:
        path = ROOT / entry["file"]
        assert path.stat().st_size == int(entry["bytes"]) and sha(path) == entry["sha256"], path
    print(f"Release integrity PASS: {len(entries)} artifacts and all inherited inputs", flush=True)


if __name__ == "__main__":
    main()
