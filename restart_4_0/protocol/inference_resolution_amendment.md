# Permutation resolution amendment

Recorded after Phase 4 fitting, before Phase 4 uncertainty calculations,
before Phase 5 fitting and before any Phase 5 inference.

Increase the fixed Phase 5 permutation count from 999 to 9,999 for every
comparison. With add-one correction, 999 permutations have minimum p=.001;
the first Holm threshold in a family of 54 is .05/54=.000926. The original
resolution would make rejection mathematically impossible. With 9,999
permutations the minimum p is .0001. Keep the complete 54-test family,
two-sided block-swap statistic, 2,000 bootstrap replicates, effect threshold
and every other analysis choice. This correction is motivated by arithmetic,
not observed significance, and does not introduce adaptive stopping.
