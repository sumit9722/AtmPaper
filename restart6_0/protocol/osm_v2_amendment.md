# Historical OSM service amendment

The public v1 metadata/count endpoints worked, but both GET and POST feature extraction returned HTTP 403. Public Overpass probes also failed. The user elected to configure `OHSOME_API_KEY` for the current HeiGIT v2 service. No ATM panels had been built at this decision.

Use documented single-snapshot `/ohsome-api/v2/extraction/features.parquet` requests, one per city/date, preserving original Parquet bytes and request hashes. Authentication is sent in a header and never saved. Cache verification allows later offline reproduction without a key. An HTTP 429 stops acquisition for quota review; do not evade rate limits.

Extract node coordinates directly. For non-point features, compute centroids after projecting to the city's UTM CRS, then transform back to WGS84. Retain the centroid flag and point-only sensitivity. This replaces v1's server-returned centroids; no v1 ATM observations were obtained or mixed with v2 data. Exclude empty or invalid geometries with a recorded reason. Confirm each feature's edit/validity timestamps contain the requested date. The dates, OSM tag population, continuity thresholds and outcome definitions stay as specified.

References: [v2 endpoints](https://docs.ohsome.org/ohsome-api/stable/reference/api.html), [extraction schema](https://docs.ohsome.org/ohsome-api/stable/reference/data_model.html), [migration announcement](https://heigit.org/ohsome-2-0-has-arrived-2/).

The first authenticated run stopped after 15 snapshots with HTTP 429. The [official quota FAQ](https://docs.ohsome.org/ohsome-api/stable/faq.html) identifies 429 as the sliding limit of 15 requests per 60 seconds (daily exhaustion is 403). After this review, resumed acquisition waits at least 4.2 seconds after each successful request, reuses every cached snapshot, and still stops on any further limit response.
