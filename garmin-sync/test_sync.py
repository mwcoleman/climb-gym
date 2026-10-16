"""python -m unittest test_sync   (no Garmin account needed)"""
import unittest

from sync import compact_climbs, compact_sets, grade_label


class T(unittest.TestCase):
    def test_grade_label(self):
        self.assertEqual(grade_label({"valueKey": "_6B_PLUS", "scale": "FONT"}), "6B+")
        self.assertEqual(grade_label({"valueKey": "_6C"}), "6C")
        self.assertEqual(grade_label({"valueKey": "V5"}), "V5")
        self.assertIsNone(grade_label(None))

    def test_compact_climbs_keeps_only_climbs(self):
        splits = {"splits": [
            {"type": "CLIMB_ACTIVE", "duration": 35.86, "gradeValue": {"valueKey": "_6B_PLUS", "sortOrder": 10}, "status": "CLIMB_COMPLETED"},
            {"type": "CLIMB_REST", "duration": 259.2},
            {"type": "CLIMB_ACTIVE", "duration": 33.1, "gradeValue": {"valueKey": "_6C", "sortOrder": 11}, "status": "CLIMB_ATTEMPTED"},
        ]}
        self.assertEqual(compact_climbs(splits), [
            {"grade": "6B+", "sent": True, "sec": 36, "rank": 10},
            {"grade": "6C", "sent": False, "sec": 33, "rank": 11},
        ])

    def test_compact_sets_grams_to_kg_and_drops_rest(self):
        sets = {"exerciseSets": [
            {"setType": "ACTIVE", "exercises": [{"category": "PULL_UP", "name": "WEIGHTED_PULL_UP"}], "repetitionCount": 5, "duration": 21.726, "weight": 83000.0},
            {"setType": "REST", "exercises": [], "duration": 50.0},
        ]}
        self.assertEqual(compact_sets(sets), [
            {"exercise": "WEIGHTED_PULL_UP", "category": "PULL_UP", "reps": 5, "kg": 83.0, "sec": 21.7},
        ])

    def test_empty(self):
        self.assertEqual(compact_climbs(None), [])
        self.assertEqual(compact_sets({"exerciseSets": None}), [])


if __name__ == "__main__":
    unittest.main()
