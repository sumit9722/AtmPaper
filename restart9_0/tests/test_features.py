import sys
import unittest
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from build_features import CAP, count_and_dist, hours_features  # noqa: E402


class Hours(unittest.TestCase):
    def test_cases(self):
        self.assertEqual(hours_features({}), (0, 0, 0))
        self.assertEqual(hours_features({"opening_hours": "24/7"}), (1, 1, 1))
        self.assertEqual(hours_features({"opening_hours": "Mo-Fr 09:00-17:00; Sa 09:00-14:00; Su closed"}), (1, 1, 0))
        self.assertEqual(hours_features({"opening_hours": "Mo-Fr 09:00-17:00; Sa-Su closed"}), (1, 0, 0))
        self.assertEqual(hours_features({"opening_hours": "Mo-Th 09:00-17:00; Fr 09:00-18:00"}), (1, 0, 1))
        self.assertEqual(hours_features({"opening_hours": "Mo-Su 08:00-22:00"}), (1, 1, 1))
        self.assertEqual(hours_features({"opening_hours": "Fr-Mo 10:00-16:00"}), (1, 1, 0))


class Distances(unittest.TestCase):
    def test_counts_and_focal_exclusion(self):
        sites = np.array([[0.0, 0.0], [1000.0, 0.0]])
        pts = np.array([[0.0, 0.0], [100.0, 0.0], [300.0, 0.0]])
        c, d = count_and_dist(sites, pts, 250)
        np.testing.assert_array_equal(c, [2, 0])
        np.testing.assert_allclose(d, [0, 700])
        c, d = count_and_dist(sites, pts, 250, exclude=np.array(["a", "b", "c"]), site_ids=np.array(["a", "z"]))
        np.testing.assert_array_equal(c, [1, 0])
        np.testing.assert_allclose(d, [100, 700])
        c, d = count_and_dist(sites, np.empty((0, 2)), 250)
        np.testing.assert_allclose(d, [CAP, CAP])


if __name__ == "__main__":
    unittest.main()
