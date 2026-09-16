import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scoring import flag_notable, suggestion_score


class FlagNotableTests(unittest.TestCase):
    def test_floor_makes_notable(self):
        records = [{"master_id": 1, "have": 5000}]
        flag_notable(records, top_n=0, min_have=2000)
        self.assertEqual(records[0]["notable"], 1)

    def test_below_floor_not_notable_without_rank(self):
        records = [{"master_id": 1, "have": 10}]
        flag_notable(records, top_n=0, min_have=2000)
        self.assertEqual(records[0]["notable"], 0)

    def test_top_n_rank_makes_notable(self):
        records = [
            {"master_id": 1, "have": 100},
            {"master_id": 2, "have": 50},
            {"master_id": 3, "have": 5},
        ]
        flag_notable(records, top_n=2, min_have=100000)
        by_id = {r["master_id"]: r["notable"] for r in records}
        self.assertEqual(by_id, {1: 1, 2: 1, 3: 0})

    def test_zero_have_never_notable_by_rank(self):
        records = [{"master_id": 1, "have": None}, {"master_id": 2, "have": 0}]
        flag_notable(records, top_n=5, min_have=2000)
        self.assertTrue(all(r["notable"] == 0 for r in records))

    def test_missing_have_treated_as_zero(self):
        records = [{"master_id": 1}]  # no 'have' key at all
        flag_notable(records, top_n=5, min_have=2000)
        self.assertEqual(records[0]["notable"], 0)


class SuggestionScoreTests(unittest.TestCase):
    def test_want_weighted_double(self):
        self.assertEqual(suggestion_score({"have": 100, "want": 10}), 120)

    def test_handles_missing_and_null(self):
        self.assertEqual(suggestion_score({}), 0)
        self.assertEqual(suggestion_score({"have": None, "want": None}), 0)

    def test_sought_after_outranks_owned(self):
        owned = {"have": 500, "want": 5}      # 510
        sought = {"have": 200, "want": 200}   # 600
        self.assertGreater(suggestion_score(sought), suggestion_score(owned))


if __name__ == "__main__":
    unittest.main()
