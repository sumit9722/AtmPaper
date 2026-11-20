# Methods and interpretation

The [frozen specification](../protocol/study_spec.md) defines the revision.
Raw observations, historical membership and geodesic distances are inherited
from Restart 6. The input manifest verifies the exact consumed artifacts against
the base release's recorded hashes. The revision performs no global spatial
search. A small direct-geodesic sample checks omissions independently.

Excluded NYC truck-burglary and Chicago motor-vehicle-burglary cases are removed
from both outcome and prior-year links. Counts are replayed from retained links.
The duplicated-case audit confirms that no excluded winning case hides an eligible
discarded alternative. LA source-code/description contradictions are flagged;
the supplementary no-source-conflicts matrix and labels omit those same cases
from both baseline and outcome. Structural offense comparability still needs
independent review.

The conservative subset consists of full-year point objects with <=10 m inherited
drift, a clear inherited 500 m municipal buffer and no other object within 10 m
in either the annual facility audit or prior-December inventory. The historical
inventory includes objects that do not survive the outcome year. These safeguards
reduce centroid, co-location and boundary concerns, but do not validate physical
ATM locations. `amenity=bank, atm=yes` point objects remain in the core; the
explicit-ATM-tag sensitivity excludes them.

Counts at each site retain all qualifying nearby cases. Nearest-site assignment
is a separate sensitivity recomputed within the master, point-only, conservative
core and explicit-ATM core populations using cached distances. A single crime
may still label several sites in the main endpoint. Stable OSM IDs, nearby-object
components, 2 km projected blocks and source block-group IDs are metadata for
future grouped evaluation; components do not certify physical identity. No folds
or models have been fitted.

Primary crime predictors are uniformly retrospective occurrence-year quantities.
The NYC/LA report-filtered sensitivity uses usable report dates strictly before
January 1; report-filtered training-label alternatives use the next January 1.
Chicago values are never filled with zero. The common baseline's complete values
do not imply that they were available in real time. Full-year inclusion still
uses future OSM mapping presence and therefore selects a survivor population.

Main environmental matrices retain the inherited 19 deterministic transforms;
expanded matrices retain raw units. The expanded field decisions were specified
before this build and verified against all 4,018 inherited rows without using
outcome values. Their removal does not guarantee independence of the remaining
fields. Any later scaling, missing-value handling or feature search must happen
inside training folds. Partial 2023 remains distinct and lacks 11 ACS and two
ATM-competition quantities at its cutoff.

EPA/ACS are neighborhood context from fixed older vintages. They do not measure
ATM visibility, lighting, security, foot traffic or use. Outcome labels measure
released-coordinate proximity; they do not establish ATM targeting or the effect
of an ATM's presence. No non-ATM controls or causal identification were added.

Original source record paths refer to Restart 6 for `release_root`, or the
repository for `project_root`. OSM attribution and all source decisions are in
[the source notes](../protocol/source_decisions.md).
