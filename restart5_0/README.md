# Restart 5.0 — phases 1 and 2 complete

Computational work and independent automated validation are complete for the user's revised scope: the longest recovered continuous ATM snapshot period. Scientific approval remains pending.

- **Monthly snapshots:** 22 February 2023–15 January 2026 (36 snapshots).
- **Complete outcome years:** 2024–2025, **2,442 site-years**.
- **Partial 2023:** 22 February–31 December (313 days), **1,271 site-periods**.
- **Crime inputs analyzed:** 2022–2025, including NYC late reports from the current-year feed; 2022 is background-only.
- **No models fitted.** Nearby robbery/burglary is not verified ATM-targeted crime.

The ten-year plan was superseded at the user's request. Its raw downloads and protocol remain preserved. The first incomplete year is explicitly partial; contemporary ATMs are never backcast into unsupported years.

[Full execution report](reports/phase_1_2_report.md) · [Methods](reports/methods.md) · [Quality and sensitivities](reports/quality_and_sensitivity.md) · [Lessons applied](reports/lessons_from_previous_attempts.md) · [Offline map](reports/atm_locations_map.html) · [Reproduce](reports/reproduce.md)

[Full-year panel](data/processed/atm_panel_full_year_2024_2025.csv) · [Partial 2023 panel](data/processed/atm_panel_partial_2023.csv) · [Combined continuity panel](data/processed/atm_panel_continuity_2023_2025.csv) · [Exact-identity sensitivity](data/processed/atm_panel_exact_supported_2023_2025.csv) · [Data dictionary](data/processed/data_dictionary.csv) · [Validation](reports/validation.json) · [Phase status](reports/phase_status.json)

The large event-link CSV is stored in four tracked parts (`data/processed/event_atm_links.csv.part001` through `.part004`). The offline rebuild recreates and checksum-checks the complete local CSV. To restore it without rebuilding, run `python3 scripts/large_artifacts.py restore restart5_0/data/processed/event_atm_links.csv` from the repository root.

The panels are alternative exposure definitions: do not stack continuity and exact-identity rows. Monthly membership is an assumption about continuity, not observed operation. Buffalo coordinate precision, missing earlier reporting times, facility identity and independent linkage/codebook review remain material limitations. `confirmatory_eligible=false`.

```bash
.venv/bin/python restart5_0/scripts/run_all.py
```
