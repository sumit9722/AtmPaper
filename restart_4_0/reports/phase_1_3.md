# Phases 1–3 execution

1. **Phase 1 complete:** the retrospective 4.0 protocol fixes the outcome,
   candidate family, model families, splits and statistical tests before fits.
2. **Phase 2 complete:** inherited official source archives and validated annual
   cohorts were audited; all 342 raw-file hashes matched the original manifest.
   There are 2,442 site-years, with exact cohort and label reuse.
3. **Phase 3 complete:** 28 predictors were reconstructed/joined. Six new lag
   features were checked independently for every site-year using direct WGS84
   distances, event-year and report-date restrictions. No outcome-year events
   enter those predictors.

These stages reuse the original data acquisition and exposure reconstruction;
they do not claim new downloads or completed human review. Provenance is in
`input_manifest.csv`; exact feature validation is in
`../results/phase3/qa/validation.json`.
