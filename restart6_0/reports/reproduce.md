# Reproduce Restart 6

From the repository root, use the existing virtual environment or install `restart6_0/requirements.txt` into a new one.

```bash
.venv/bin/python restart6_0/scripts/run_all.py
```

This verifies frozen raw inputs, reconstructs exposure and crimes, rebuilds annual/monthly panels, validates them, renders the report/map and splits large CSVs into checksum-verified parts. The complete offline rebuild needs no API key. The downloaded raw sources and inherited filtered NYC inputs are self-contained.

For a first acquisition, the original Restart 5 inputs must be present. Use the hidden prompt (the key is never echoed or saved):

```bash
.venv/bin/python restart6_0/scripts/run_all.py --acquire --key-stdin
```

Alternatively set `OHSOME_API_KEY` in the invoking process environment and omit `--key-stdin`. Only historical OSM downloads require it. Successful requests are cached and verified. Stop on quota errors; preserve the cache. Frozen inputs cannot be silently refreshed; changed raw files require a separately reviewed release.

To restore large CSVs without rebuilding:

```bash
.venv/bin/python restart6_0/scripts/large_artifacts.py restore
```

Old NYC raw source references in the harmonized crime table are relative to the repository root and remain traceable in Restart 5. The cached filtered NYC input suffices for this release's offline rebuild. NYC source vintage is inherited; Chicago and LA were newly extracted. Do not call the three extracts a synchronized historical snapshot.
