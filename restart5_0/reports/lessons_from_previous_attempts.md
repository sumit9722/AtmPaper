# Lessons applied from previous attempts

| Previous evidence or failure mode | Restart 5.0 response | Inspectable evidence |
| --- | --- | --- |
| The original current ATM list was unsuitable as a historical denominator. | Recovered continuous monthly archives set the analysis period; partial exposure remains explicit. | required_atm_months.csv, exposure intervals, scope amendment |
| The desired decade exceeded available exposure history. | User-directed scope replacement before build; preserve initial protocol and downloads. | superseded_ten_year_spec.md and both freeze records |
| Public archive requests can resolve older requested versions to the oldest retained version. | Inspect returned versions; never misdate a substituted export. | archive_resolution_audit.csv and raw discovery responses |
| Exact coordinates changed during 2024 and eliminated its strict full-year cohort. | Keep strict sensitivity; apply an auditable unique-address <=50 m rule with 10/25 m attrition sensitivity. | continuity links/eligibility and exact inventory |
| Earlier pipelines treated completed computations as a stronger milestone than source validity justified. | Separate computational PASS from independent scientific acceptance and confirmatory eligibility. | phase_status.json and research_review_gates.csv |
| Earlier incomplete offset extraction had to be isolated. | Partition source downloads by year, reconcile API counts before/after and unique source IDs; ArcGIS batches reconcile exact IDs. | acquisition.json, raw request sidecars, validation.json |
| Historical NYPD data is organized by reporting coverage, not an eventually final occurrence-year census. | Add earlier occurrences from the current-year feed; preserve/report late cases separately. | late_current raw partitions and source-completeness amendment |
| Buffalo created_at is a proxy, and missing earlier report times can materially deplete background counts. | Explicit incomplete-availability flags and coverage fraction; no inference that missing reports mean no crime. | crime quality and background_measurement_status |
| Public Buffalo coordinates are rounded on a grid larger than the 50 m endpoint's scale. | Quantify rounding and a conditional displacement scenario; retain an unresolved precision gate. | sensitivity summary and quality report |
| Crime was counted at multiple nearby sites. | Save multiplicity and nearest-exposed-site sensitivity per cohort/year; identify facility components separately. | event links and facility review |
| Municipality clipping can truncate surrounding context. | Quantify annulus coverage and boundary distance; publish boundary-clear sensitivity. | panel geometry diagnostics and sensitivity summary |
| Previous 4.0 improvement came mainly from prior nearby crime, not necessarily an environmental effect. | Keep environmental increment and temporal persistence conceptually separate in future-phase guardrails. | active study specification |
| Both earlier outcome years have already been inspected. | Do not call this preregistered or an untouched confirmatory test; no models or significance target in phases 1–2. | protocol and status |
| Automated validation can reproduce a shared implementation mistake. | Independent raw-snapshot reconstruction, source conservation, direct geodesic omission checks and count replay. | validate.py and validation.json |

The new release preserves earlier directories and does not reuse their PASS statuses as evidence. The raw source bytes inherited from previous work are separately identified and hash checked; fresh crime and February–November 2023 ATM retrievals are not mislabeled as inherited.
