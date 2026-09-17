import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from recommender import build_suggestions, seed_weight


class SeedWeightTests(unittest.TestCase):
    def test_top_rank_heaviest(self):
        self.assertGreater(seed_weight(1), seed_weight(40))

    def test_bounds(self):
        self.assertAlmostEqual(seed_weight(1), 1.98)
        self.assertEqual(seed_weight(50), 1.0)
        self.assertEqual(seed_weight(100), 1.0)  # beyond 50 floors at 1.0

    def test_none_and_bad_rank(self):
        self.assertEqual(seed_weight(None), 1.0)
        self.assertEqual(seed_weight(0), 1.0)


class BuildSuggestionsTests(unittest.TestCase):
    def setUp(self):
        self.seeds = [{"name": "A", "weight": 2.0}, {"name": "B", "weight": 1.0}]

    def test_multi_seed_candidate_scores_higher(self):
        similar = {
            "A": [{"name": "Shared", "match": "0.5"}, {"name": "OnlyA", "match": "0.9"}],
            "B": [{"name": "Shared", "match": "0.5"}],
        }
        out = build_suggestions(self.seeds, similar, known_names=[])
        by_name = {s["name"]: s for s in out}
        # Shared: 2.0*0.5 + 1.0*0.5 = 1.5 ; OnlyA: 2.0*0.9 = 1.8
        self.assertEqual(by_name["Shared"]["seed_count"], 2)
        self.assertAlmostEqual(by_name["Shared"]["score"], 1.5)
        self.assertAlmostEqual(by_name["OnlyA"]["score"], 1.8)
        self.assertEqual(out[0]["name"], "OnlyA")  # sorted desc

    def test_excludes_known(self):
        similar = {"A": [{"name": "Radiohead", "match": "0.9"}], "B": []}
        out = build_suggestions(self.seeds, similar, known_names=["radiohead"])
        self.assertEqual(out, [])

    def test_merges_by_normalized_name(self):
        similar = {
            "A": [{"name": "The Beatles", "match": "0.4"}],
            "B": [{"name": "beatles", "match": "0.4"}],
        }
        out = build_suggestions(self.seeds, similar, known_names=[])
        self.assertEqual(len(out), 1)
        self.assertEqual(out[0]["seed_count"], 2)

    def test_reasons_ordered_by_contribution(self):
        similar = {
            "A": [{"name": "X", "match": "0.1"}],   # 2.0*0.1 = 0.2
            "B": [{"name": "X", "match": "0.9"}],   # 1.0*0.9 = 0.9 -> B contributes more
        }
        out = build_suggestions(self.seeds, similar, known_names=[], max_reasons=3)
        self.assertEqual(out[0]["reasons"], "B, A")

    def test_carries_mbid_and_url_and_handles_bad_match(self):
        similar = {
            "A": [{"name": "X", "match": None, "mbid": "", "url": None}],
            "B": [{"name": "X", "match": "not-a-number", "mbid": "abc", "url": "http://x"}],
        }
        out = build_suggestions(self.seeds, similar, known_names=[])
        self.assertEqual(out[0]["score"], 0.0)   # both matches coerced to 0
        self.assertEqual(out[0]["mbid"], "abc")  # picked up from the seed that had one
        self.assertEqual(out[0]["url"], "http://x")

    def test_limit(self):
        similar = {"A": [{"name": f"c{i}", "match": str(i / 10)} for i in range(1, 6)], "B": []}
        out = build_suggestions(self.seeds, similar, known_names=[], limit=2)
        self.assertEqual(len(out), 2)


if __name__ == "__main__":
    unittest.main()
