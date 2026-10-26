# Phase 3 work completed

Built and validated features for all 2,731 main site-years and 1,287 separately labeled partial-2023 site-periods. The three cities are New York City, Chicago and Los Angeles city. The phases 1–2 files remain unchanged and their hashes were verified.

Reused the frozen Restart 4 feature families and the national housing tables already downloaded for Restart 3. Retrieved the missing population/economic tables, California/Illinois TIGER geometry and EPA county polygons. New and reused inputs have individual hashes and original retrieval sidecars in `qa/input_manifest.csv`. Cook and DuPage counties cover Chicago; Los Angeles uses county 037; NYC uses its five borough counties.

Replaced DFS competition measures with prior-December OSM objects matching Restart 6's population. Reconstructed six nearby prior-crime candidates from source incidents; retained both report-filtered and explicitly retrospective unfiltered versions. No models, imputation, scaling, target-based feature selection or row dropping were performed.

10 validation groups passed, with 1,081,260 ACS source cells checked, all 18,579 prior-event links replayed, 36 direct spatial omission checks, and all 2,731 main ATM-competition rows reconstructed. Four synthetic regression tests cover missingness, invalid polygons, source boundaries and report/year cutoffs.
