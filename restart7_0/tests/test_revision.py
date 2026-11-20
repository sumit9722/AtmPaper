"""Boundary tests for consequential revision rules; no research rows fabricated."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from common import excluded


class OffenseRuleTests(unittest.TestCase):
    def test_nyc_truck_codes_are_excluded(self):
        for code in ("231", "233", "234"):
            self.assertTrue(excluded({"city": "New York City", "native_code": code}))

    def test_chicago_leading_zero_is_normalized(self):
        for code in ("760", "0760"):
            self.assertTrue(excluded({"city": "Chicago", "native_code": code}))

    def test_codes_are_city_specific(self):
        self.assertFalse(excluded({"city": "Los Angeles", "native_code": "231"}))
        self.assertFalse(excluded({"city": "New York City", "native_code": "0760"}))

    def test_structural_burglary_and_robbery_remain(self):
        for city, code in (("New York City", "221"), ("New York City", "380"),
                           ("Chicago", "0610"), ("Chicago", "0325"), ("Chicago", "033A"),
                           ("Los Angeles", "220"), ("Los Angeles", "120")):
            self.assertFalse(excluded({"city": city, "native_code": code}))


if __name__ == "__main__":
    unittest.main()
