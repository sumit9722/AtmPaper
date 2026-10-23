# Restart 6 recovery checkpoint

This records the initial recovery checkpoint. For the latest build result,
see `phase_status.json`, `execution.json` and `phase_1_2_report.md`.

Scope remains the frozen Restart 6 phases 1–2 specification: New York City,
Chicago and Los Angeles city; an exploratory historical OSM ATM cohort;
separate inherited NYC DFS reference data; no models.

Recovery on 2026-10-23 found 83 of 108 required historical OSM snapshots.
NYC and LA each have all 36. Chicago has February–December 2023; the remaining
25 dates run from January 2024 through January 2026. The cache hashes,
feature validity intervals and ATM tag population pass checks recorded in
`resume_cache_audit.json`. All inherited filtered input hashes pass.

All 12 Chicago/LA crime source-year partitions reconcile to their saved
before/after counts and unique row IDs. The crime builder was rerun and
produced 278,394 retained incidents, 1,101 excluded rows and 145 duplicate
rows. The existing synthetic regression passes.

The initial resumed session had no `OHSOME_API_KEY`. The user subsequently
provided a local `apikey.txt`; acquisition resumed using standard input
without printing or copying the credential. The filename is ignored by Git
at every directory depth and excluded from the artifact manifest, as are
local `.env` files. Authentication is required only for uncached snapshots.

From the repository root, download the missing snapshots with a hidden key
prompt (the key is not saved or echoed):

```bash
.venv/bin/python restart6_0/scripts/acquire.py --stage osm --key-stdin
```

Then run the complete offline build:

```bash
.venv/bin/python restart6_0/scripts/run_all.py
```

The download verifies and reuses cached files, paces requests according to
the saved service amendment, and stops on a quota response. Network access
may require the execution environment's approval.

The resumed code adds independent validation of partial-2023 membership,
exact-coordinate exposure days, nearest-site assignments and match
multiplicity. `run_all.py` now also runs and records the synthetic regression
before building the research panels. These strengthened real-data checks
are recorded in the final validation report when the complete pipeline runs.

Final release checks cover generated counts, reports, map, manifests and
split artifacts. Scientific review remains pending and
`confirmatory_eligible=false` regardless of computational success. Earlier
restarts remain preserved.
