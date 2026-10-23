# Restart 6 — NYC, Chicago and Los Angeles

Phases 1–2 are computationally complete and automatically validated. Scientific review remains pending. No models were fitted.

| City | 2024 full-year sites | 2025 full-year sites | 2023 partial sites |
| --- | --- | --- | --- |
| New York City | 702 | 750 | 680 |
| Chicago | 443 | 482 | 441 |
| Los Angeles | 174 | 180 | 166 |

Historical OSM snapshots: February 22, 2023–January 15, 2026. **2,731 full-year site-years** and **1,287 partial-2023 site-periods**. NYC's prior official DFS cohort is preserved as a separate reference; it is not pooled with OSM.

[Execution report](reports/phase_1_2_report.md) · [Offline map](reports/atm_locations_map.html) · [Full-year panel](data/processed/atm_panel_full_year_2024_2025.csv) · [Partial 2023](data/processed/atm_panel_partial_2023.csv) · [Monthly panel](data/processed/atm_site_month_panel.csv) · [Validation](reports/validation.json) · [Reproduce](reports/reproduce.md)

```bash
.venv/bin/python restart6_0/scripts/run_all.py
```

The offline rebuild needs no key. Historical OSM acquisition uses `OHSOME_API_KEY` or a hidden prompt. Large crime/link CSVs are stored as checksum-verified parts; the rebuild recreates them, or run `python restart6_0/scripts/large_artifacts.py restore`.

OSM is an incomplete mapped sample; continuity does not establish ATM operation. Chicago/LA block geocodes limit small-radius interpretation. LA's reporting transition and Chicago's missing original report dates are explicitly flagged. Nearby robbery/burglary is not verified ATM-targeted crime. `confirmatory_eligible=false`.

© OpenStreetMap contributors, [ODbL](https://www.openstreetmap.org/copyright), via HeiGIT ohsome. Source URLs, hashes, reuse provenance and review gates are included.
