import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from matching import normalize_name, pick_best_artist, similarity


class NormalizeNameTests(unittest.TestCase):
    def test_strips_discogs_disambiguation(self):
        self.assertEqual(normalize_name("Nirvana (2)"), normalize_name("Nirvana"))

    def test_drops_leading_the(self):
        self.assertEqual(normalize_name("The Beatles"), "beatles")

    def test_folds_accents(self):
        self.assertEqual(normalize_name("Sigur Rós"), "sigur ros")
        self.assertEqual(normalize_name("Björk"), "bjork")

    def test_punctuation_and_case_insensitive(self):
        self.assertEqual(normalize_name("GODSPEED you! Black Emperor"), "godspeed you black emperor")

    def test_empty(self):
        self.assertEqual(normalize_name(""), "")
        self.assertEqual(normalize_name(None), "")


class PickBestArtistTests(unittest.TestCase):
    def test_exact_match_wins_over_earlier_fuzzy(self):
        candidates = [
            {"id": 1, "title": "Radioheadz"},
            {"id": 2, "title": "Radiohead"},
        ]
        best, confidence = pick_best_artist("Radiohead", candidates)
        self.assertEqual(confidence, "exact")
        self.assertEqual(best["id"], 2)

    def test_disambiguated_exact(self):
        best, confidence = pick_best_artist("Alex G", [{"id": 9, "title": "Alex G (2)"}])
        self.assertEqual(confidence, "exact")
        self.assertEqual(best["id"], 9)

    def test_accents_fold_to_exact(self):
        best, confidence = pick_best_artist("Bjork", [{"id": 3, "title": "Björk"}])
        self.assertEqual(confidence, "exact")
        self.assertEqual(best["id"], 3)

    def test_fuzzy_when_close(self):
        # One transposed/edited character -> above the fuzzy threshold, not exact.
        best, confidence = pick_best_artist(
            "Portishead", [{"id": 3, "title": "Portished"}]
        )
        self.assertEqual(confidence, "fuzzy")
        self.assertEqual(best["id"], 3)

    def test_none_when_far(self):
        best, confidence = pick_best_artist("Radiohead", [{"id": 4, "title": "Metallica"}])
        self.assertIsNone(best)
        self.assertEqual(confidence, "none")

    def test_empty_candidates(self):
        best, confidence = pick_best_artist("Anyone", [])
        self.assertIsNone(best)
        self.assertEqual(confidence, "none")

    def test_similarity_bounds(self):
        self.assertEqual(similarity("a", "a"), 1.0)
        self.assertEqual(similarity("", "x"), 0.0)


if __name__ == "__main__":
    unittest.main()
