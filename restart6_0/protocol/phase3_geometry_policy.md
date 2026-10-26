# Phase 3 geometry exception — conservative missingness

Recorded during the first feature build, before any successful feature release
or model fitting. EPA SLD block group 170317104004 has a source polygon
self-intersection. GEOS make_valid yields a MultiPolygon with relative area
change 9.653715470488297e-05, exceeding the frozen 1e-6 tolerance. The raw source
is unchanged. The original build correctly stopped.

Do not relax the repair tolerance or accept this repaired polygon. Instead,
retain the source record and diagnostic, omit its unusable geometry from the
join index, and conservatively mark all candidate sites covered by its raw
bounding rectangle as `invalid_source_geometry`. Such sites receive missing
values for the entire EPA feature family, even if another polygon also covers
them. This prevents a silently accepted neighboring-polygon assignment. Site
rows and other feature families are retained. Save the invalid source GEOID,
area-change diagnostic and affected row IDs for scientific review.

This exception replaces only the requirement to stop the whole release for
an unusable source polygon. Other polygons retain the original repair
tolerance and unique-covers rule. Generalize the same conservative missingness
rule to any additional source geometry exceeding that tolerance; do not invent
context values. The original input manifest is retained as
`input_manifest_before_geometry_policy.csv`; the final manifest includes this
policy. Independent scientific acceptance remains pending.
