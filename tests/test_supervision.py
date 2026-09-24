"""Unit tests for the supervisor review layer (supervision.py) and its additive database migration.
Temporary database only. Run: .venv\\Scripts\\python.exe -m unittest tests.test_supervision
"""
import os
import shutil
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path

os.environ["CAT_OPERATOR_DB"] = str(Path(tempfile.mkdtemp()) / "sup_logic.db")
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd  # noqa: E402

import analytics as an  # noqa: E402
import data  # noqa: E402
import skills as sk  # noqa: E402
import supervision as sv  # noqa: E402

HIST_END = pd.Timestamp("2026-09-22 18:36")
COLS = ["operator_id", "module_id", "module", "score", "time"]


def log(*rows):
    return pd.DataFrame([dict(zip(COLS, r)) for r in rows], columns=COLS)


def reviews(*rows):
    return pd.DataFrame([dict(zip(data.REVIEW_COLUMNS, r)) for r in rows], columns=data.REVIEW_COLUMNS)


NO_REVIEWS = reviews()


class ReviewState(unittest.TestCase):
    def test_seeded_training_is_exempt(self):
        [c] = sv.training_cases(log(("OP1001", "fuel", "Fuel", 100.0, "2026-08-14 16:00")), HIST_END)
        self.assertTrue(c["exempt"])
        self.assertEqual(sv.review_state(c, NO_REVIEWS)[0], "exempt")

    def test_new_training_awaits_review(self):
        [c] = sv.training_cases(log(("OP1001", "terrain", "Terrain", 100.0, "2026-09-24 09:00:05")), HIST_END)
        self.assertFalse(c["exempt"])
        self.assertEqual(sv.review_state(c, NO_REVIEWS)[0], "awaiting")

    def test_latest_decision_wins(self):
        [c] = sv.training_cases(log(("OP1001", "terrain", "Terrain", 100.0, "2026-09-24 09:00:05")), HIST_END)
        t = c["training_time"]
        r = reviews(("OP1001", "terrain", t, "retraining", "Needs reinforcement", "", "S", "2026-09-24 10:00:00"),
                    ("OP1001", "terrain", t, "approved", "Approved", "", "S", "2026-09-24 10:05:00"))
        self.assertEqual(sv.review_state(c, r)[0], "approved")
        self.assertEqual(sv.review_state(c, r.iloc[::-1])[0], "approved")  # order in the table does not matter

    def test_same_timestamp_decisions_keep_insertion_order(self):
        [c] = sv.training_cases(log(("OP1001", "terrain", "Terrain", 100.0, "2026-09-24 09:00:05")), HIST_END)
        t = c["training_time"]
        r = reviews(("OP1001", "terrain", t, "approved", "Approved", "", "S", "2026-09-24 10:00:00"),
                    ("OP1001", "terrain", t, "instructor", "Needs reinforcement", "", "S", "2026-09-24 10:00:00"))
        self.assertEqual(sv.review_state(c, r)[0], "instructor")

    def test_retake_is_a_new_case_and_old_decisions_are_kept(self):
        tl = log(("OP1001", "terrain", "Terrain", 66.7, "2026-09-24 09:00:05"),
                 ("OP1001", "terrain", "Terrain", 100.0, "2026-09-24 11:30:40"))
        r = reviews(("OP1001", "terrain", "2026-09-24 09:00:05", "retraining", "Needs reinforcement", "", "S", "2026-09-24 10:00:00"))
        [c] = sv.training_cases(tl, HIST_END)
        self.assertEqual(c["training_time"], "2026-09-24 11:30:40")
        self.assertEqual(c["attempts"], 2)
        self.assertEqual(sv.review_state(c, r)[0], "awaiting")  # the earlier decision stays in the table, unused
        self.assertEqual(len(r), 1)

    def test_duplicate_rows_with_same_time_are_one_attempt(self):
        tl = log(("OP1001", "terrain", "Terrain", 66.7, "2026-09-24 07:32"), ("OP1001", "terrain", "Terrain", 66.7, "2026-09-24 07:32"))
        [c] = sv.training_cases(tl, HIST_END)
        self.assertEqual(c["attempts"], 1)

    def test_only_modules_with_a_competency_are_reviewed(self):
        tl = log(("OP1001", "simulator", "Sim", 100.0, "2026-09-24 09:00:00"), ("OP1001", "walkaround", "Walk", 100.0, "2026-09-24 09:01:00"))
        self.assertEqual(sv.training_cases(tl, HIST_END), [])
        self.assertEqual(sv.REVIEWABLE_MODULES, ["fuel", "operation", "safety", "terrain"])

    def test_approval_never_produces_verified(self):
        monitoring = [{"verdict": "monitoring", "n_post": 0}]
        self.assertEqual(sv.case_group("approved", monitoring), "monitoring")
        self.assertEqual(sv.case_group("approved", []), "monitoring")
        self.assertEqual(sv.case_group("approved", [{"verdict": "insufficient", "n_post": 0}]), "monitoring")
        # Verified / escalated only ever come from the statistical verdicts themselves
        self.assertEqual(sv.case_group("approved", [{"verdict": "verified", "n_post": 30}]), "verified")
        self.assertEqual(sv.case_group("exempt", [{"verdict": "adapt", "n_post": 30}]), "escalated")

    def test_pending_decisions_are_not_statistical_groups(self):
        verified = [{"verdict": "verified", "n_post": 30}]
        self.assertEqual(sv.case_group("awaiting", verified), "awaiting")
        self.assertEqual(sv.case_group("retraining", verified), "retraining")
        self.assertEqual(sv.case_group("instructor", verified), "coaching")

    def test_post_sessions(self):
        self.assertEqual(sv.post_sessions([{"n_post": 0}, {"n_post": 3}]), 0)
        self.assertEqual(sv.post_sessions([]), 0)


class SeededOutcomesUnchanged(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        data.init_db()
        s = an.enrich(data.read("sessions"), data.read("machines"), data.read("operators"))
        s["expected_min_oof"] = an.train_time_model(s)["oof"]
        cls.s, cls.std, cls.tl = s, sk.session_standards(s), data.read("training_log")

    def group_of(self, op, module):
        [c] = [c for c in sv.training_cases(self.tl, self.s.timestamp.max()) if c["operator_id"] == op and c["module_id"] == module]
        loops = [l for l in sk.training_loops(self.s, self.std, op, self.tl) if l["completed"] == c["training_time"]]
        state, _ = sv.review_state(c, data.read_reviews())
        return state, sv.case_group(state, loops), loops

    def test_ravi_and_anita_remain_verified_priya_escalated(self):
        for op, mod, group in [("OP1001", "fuel", "verified"), ("OP1002", "safety", "verified"), ("OP1004", "fuel", "escalated")]:
            state, g, loops = self.group_of(op, mod)
            self.assertEqual((state, g), ("exempt", group), op)
            self.assertEqual(loops[0]["verdict"], {"verified": "verified", "escalated": "adapt"}[group])

    def test_seeded_numbers_unchanged(self):
        _, _, [ravi] = self.group_of("OP1001", "fuel")
        self.assertAlmostEqual(ravi["pre_rate"], 26.67, 1)
        self.assertAlmostEqual(ravi["post_rate"], 80.0, 1)


class AdditiveMigration(unittest.TestCase):
    def test_review_table_is_added_without_touching_existing_data(self):
        data.init_db()
        old = Path(tempfile.mkdtemp()) / "old.db"
        shutil.copy(data.DB_PATH, old)
        with sqlite3.connect(old) as con:  # simulate a database created before the review layer existed
            con.execute("DROP TABLE supervisor_reviews")
            con.execute("INSERT INTO bookings VALUES ('OP1001', 'Fuel', '2026-09-30', '08:00–10:00', 'R. Menon (Safety)')")
        with sqlite3.connect(old) as con:
            tables = [t for (t,) in con.execute("SELECT name FROM sqlite_master WHERE type='table'")]
            before = {t: con.execute(f"SELECT * FROM {t}").fetchall() for t in tables}
        saved, data.DB_PATH = data.DB_PATH, old
        try:
            data.ensure_review_table()
            data.ensure_review_table()  # idempotent
            self.assertEqual(len(data.read_reviews()), 0)
            data.log_review("OP1001", "terrain", "2026-09-24 09:00:05", "approved", "Approved", "ok")
            data.log_review("OP1001", "terrain", "2026-09-24 09:00:05", "retraining", "Needs reinforcement")
            r = data.read_reviews()
            self.assertEqual(list(r.decision), ["approved", "retraining"])  # append-only
            self.assertEqual(list(r.columns), data.REVIEW_COLUMNS)
        finally:
            data.DB_PATH = saved
        with sqlite3.connect(old) as con:
            after = {t: con.execute(f"SELECT * FROM {t}").fetchall() for t in tables}
        self.assertEqual(before, after)  # every pre-existing table and row (incl. the booking) is untouched


if __name__ == "__main__":
    unittest.main()
