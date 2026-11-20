"""Synthetic tests of uncertainty arithmetic and separation safeguards."""
import unittest
import numpy as np
from sklearn.metrics import average_precision_score
from run import weighted_ap, purge, GROUP_FIELDS


class Phase4Tests(unittest.TestCase):
    def test_weighted_ap_matches_library_with_ties_and_omitted_blocks(self):
        y = np.array([0, 1, 1, 0, 0, 1, 0, 1])
        scores = np.array([.8, .8, .6, .6, .3, .3, .1, .1])
        weights = np.array([[1, 1, 1, 1, 1, 1, 1, 1], [0, 0, 3, 3, 0, 0, 2, 2], [4, 4, 0, 0, 1, 1, 0, 0]])
        expected = [average_precision_score(y, scores, sample_weight=w) for w in weights]
        np.testing.assert_allclose(weighted_ap(y, scores, weights), expected, atol=1e-12)

    def test_purge_removes_distance_and_shared_geography(self):
        meta = [{field: f"{field}_{i}" for field in GROUP_FIELDS} for i in range(5)]
        meta[1]["sld_geoid_2019"] = meta[4]["sld_geoid_2019"]
        meta[2]["object_group_id"] = meta[4]["object_group_id"]
        d = np.full((5, 5), 9000.0)
        d[0, 4] = 1499.9
        d[3, 4] = 1500.0
        np.testing.assert_array_equal(purge(np.arange(4), np.array([4]), d, meta), [3])

    def test_empty_geography_is_not_shared_group(self):
        meta = [{field: "" for field in GROUP_FIELDS} for _ in range(2)]
        np.testing.assert_array_equal(purge(np.array([0]), np.array([1]), np.full((2, 2), 3000.0), meta), [0])


if __name__ == "__main__":
    unittest.main()
