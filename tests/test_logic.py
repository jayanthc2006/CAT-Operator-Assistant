"""Unit tests for the decision logic: competencies, skill gaps, before/after verification, anomaly evidence,
task-model evaluation (temporal split, no leakage), fatigue indicator and offline assets.
Run: .venv\\Scripts\\python.exe -m unittest tests.test_logic -v      (from the project folder)
"""
import os
import sys
import tempfile
import unittest
from datetime import datetime, timedelta
from pathlib import Path

os.environ["CAT_OPERATOR_DB"] = str(Path(tempfile.mkdtemp()) / "unit.db")
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

import analytics as an  # noqa: E402
import data  # noqa: E402
import skills as sk  # noqa: E402


def sessions_df(n, start=datetime(2026, 1, 1), operator="OP1", **cols):
    """n clean sessions that meet every standard; override any column with a scalar or a list."""
    base = {"operator_id": operator, "machine_type": "Excavator", "seatbelt_status": "Fastened", "speed_vs_limit": 0.7,
            "overload_events": 0, "idle_ratio": 0.10, "fuel_per_work_h": 18.0, "m3_per_cycle": 10.0, "harsh_events": 0,
            "max_tilt_deg": 8.0, "slope_deg": 6.0, "tilt_excess_deg": 2.0, "duration_min": 60.0, "expected_min_oof": 60.0,
            "idle_fuel_l": 0.5, "load_cycles": 8, "volume_m3": 80, "alert_types": ""}
    base.update(cols)
    df = pd.DataFrame({k: (v if isinstance(v, list) else [v] * n) for k, v in base.items()})
    df["timestamp"] = [start + timedelta(hours=6 * i) for i in range(n)]
    return df


class TestCompetencies(unittest.TestCase):
    def test_standards_rules(self):
        s = sessions_df(6, seatbelt_status=["Fastened", "Unfastened", "Fastened", "Fastened", "Fastened", "Fastened"],
                        idle_ratio=[.1, .1, .35, .1, .1, .1], harsh_events=[0, 0, 0, 2, 0, 0],
                        slope_deg=[6, 6, 6, 6, 1, 6], max_tilt_deg=[8, 8, 8, 8, 8, 17], tilt_excess_deg=[2, 2, 2, 2, 7, 11])
        std = sk.session_standards(s)
        self.assertEqual(list(std.safety), [1, 0, 1, 1, 1, 1])
        self.assertEqual(list(std.fuel), [1, 1, 0, 1, 1, 1])
        self.assertEqual(list(std.handling), [1, 1, 1, 0, 1, 1])
        self.assertTrue(np.isnan(std.terrain[4]), "terrain standard must not apply on flat ground")
        self.assertEqual(std.terrain[5], 0)

    def test_cycle_standard_uses_rated_capacity_not_peers(self):
        s = sessions_df(3, m3_per_cycle=[10.0, 8.6, 8.0])  # standard: >= 85% of rated 10 m3
        self.assertEqual(list(sk.session_standards(s).cycle), [1, 1, 0])

    def test_score_is_share_of_sessions_meeting_standard(self):
        s = sessions_df(30, idle_ratio=[.4] * 12 + [.1] * 18)  # 18/30 meet the fuel standard
        prof = sk.operator_profile(s, sk.session_standards(s), "OP1").set_index("id")
        self.assertAlmostEqual(prof.loc["fuel", "score"], 60.0)
        self.assertTrue(prof.loc["fuel", "gap"])
        self.assertEqual(prof.loc["fuel", "module"], "fuel")
        self.assertFalse(prof.loc["safety", "gap"])
        self.assertIn("12 of 30 sessions above 20% idle", prof.loc["fuel", "evidence"][1])

    def test_too_few_sessions_is_not_scored(self):
        s = sessions_df(5)
        prof = sk.operator_profile(s, sk.session_standards(s), "OP1").set_index("id")
        self.assertTrue(pd.isna(prof.loc["safety", "score"]))


class TestClosedLoop(unittest.TestCase):
    def _loop(self, pre_idle, post_idle, n_post):
        s = sessions_df(30 + n_post, idle_ratio=[pre_idle] * 30 + [post_idle] * n_post)
        when = s.timestamp.iloc[29] + timedelta(hours=1)
        log = pd.DataFrame([{"operator_id": "OP1", "module_id": "fuel", "module": "Fuel", "time": str(when), "score": 100}])
        return sk.training_loops(s, sk.session_standards(s), "OP1", log)[0]

    def test_improvement_is_verified_statistically(self):
        loop = self._loop(pre_idle=.35, post_idle=.10, n_post=20)
        self.assertEqual(loop["verdict"], "verified")
        self.assertEqual((loop["pre_rate"], loop["post_rate"]), (0.0, 100.0))
        self.assertLess(loop["p_rate"], 0.05)

    def test_no_change_escalates_to_coaching(self):
        loop = self._loop(pre_idle=.35, post_idle=.35, n_post=20)
        self.assertEqual(loop["verdict"], "adapt")

    def test_just_trained_is_monitoring_not_verified(self):
        loop = self._loop(pre_idle=.35, post_idle=.10, n_post=0)
        self.assertEqual(loop["verdict"], "monitoring")
        self.assertIsNone(loop["post_rate"], "no improvement may be shown before post-training sessions exist")
        self.assertIn("0/8", loop["verdict_text"])

    def test_few_post_sessions_keep_monitoring(self):
        self.assertEqual(self._loop(pre_idle=.35, post_idle=.10, n_post=5)["verdict"], "monitoring")

    def test_loop_stage(self):
        row = {"id": "fuel", "gap": True}
        self.assertEqual(sk.loop_stage(row, [])[0], 1)  # detected → training recommended
        self.assertEqual(sk.loop_stage(row, [{"comp": "fuel", "verdict": "verified", "verdict_text": ""}])[0], 4)
        self.assertTrue(sk.loop_stage(row, [{"comp": "fuel", "verdict": "adapt", "verdict_text": ""}])[2])

    def test_personal_improvement_direction(self):
        s = sessions_df(60, idle_ratio=[.30] * 30 + [.12] * 30)
        imp = sk.personal_improvement(s, sk.session_standards(s), "OP1").set_index("measure")
        self.assertEqual(imp.loc["Idle share", "change"], "▲ better")
        self.assertEqual(imp.loc["Idle share", "previous 30"], "30%")


class TestModelsOnGeneratedData(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        data.init_db(force=True)
        s = an.enrich(data.read("sessions"), data.read("machines"), data.read("operators"))
        cls.tmod = an.train_time_model(s)
        s["expected_min_oof"] = cls.tmod["oof"]
        cls.s = an.detect_anomalies(s)

    def test_no_post_task_information_in_features(self):
        post_task = {"duration_min", "idling_time_min", "fuel_used_l", "load_cycles", "estimated_time_min",
                     "safety_alert_triggered", "alert_types", "injected_event", "pace_ratio", "harsh_events"}
        self.assertFalse(post_task & set(an.TIME_FEATURES))

    def test_temporal_split(self):
        (tr0, tr1), (te0, te1) = self.tmod["metrics"]["train_period"], self.tmod["metrics"]["test_period"]
        self.assertLess(tr1, te0, "every test session must be later than every training session")

    def test_operator_pace_uses_only_earlier_days(self):
        s = self.s
        row = s[s.operator_id == "OP1003"].iloc[60]
        prior = s[(s.operator_id == "OP1003") & (s.timestamp.dt.date < row.timestamp.date())].sort_values("timestamp")
        self.assertAlmostEqual(row.operator_pace_hist, prior.pace_ratio.tail(an.PACE_WINDOW).median())

    def test_metrics_are_consistent(self):
        m = self.tmod["metrics"]
        self.assertAlmostEqual(m["reduction"], 1 - m["ai_mae"] / m["planner_mae"])
        self.assertLessEqual(m["reduction_ci"][0], m["reduction"])
        self.assertGreaterEqual(m["reduction_ci"][1], m["reduction"])
        self.assertGreater(m["ai_mae"], 1.0, "a near-zero error would indicate leakage")

    def test_oof_expected_time_covers_all_sessions(self):
        self.assertEqual(int(self.tmod["oof"].isna().sum()), 0)

    def test_anomaly_evidence_uses_real_baselines(self):
        s = self.s
        i = s.index[s.is_anomaly][0]
        ex = an.explain_anomaly(s, i)
        row = s.loc[i]
        f = next(k for k, v in an.ANOMALY_FEATURES.items() if v == ex["evidence"].iloc[0]["signal"])
        op_med = s.drop(index=i)[s.drop(index=i).operator_id == row.operator_id][f].median()
        self.assertEqual(ex["evidence"].iloc[0]["operator baseline"], an._FMT[f](op_med))
        self.assertTrue(ex["recommendation"])

    def test_detector_validation(self):
        ev = an.evaluate_detector(self.s)
        self.assertGreater(ev["n_usage"], 0)
        self.assertGreater(ev["flag_explained"], ev["base_rate_known"], "flags should be enriched for known anomalies")

    def test_explanation_lists_only_model_inputs(self):
        feats = dict(task_type="Trenching", weather="Rainy", operator_skill="Beginner", machine_age_yrs=6,
                     machine_type="Excavator", soil="Rock", temp_c=40, slope_deg=9, volume_m3=120, operator_pace_hist=1.3)
        est, why = an.explain_prediction(self.tmod["model"], feats, self.tmod["reference"])
        self.assertGreater(est, 0)
        self.assertTrue(set(why.factor) <= set(an.FEATURE_LABELS.values()))

    def test_hidden_traits_not_in_database(self):
        self.assertFalse({"belt_habit", "idle_habit"} & set(data.read("operators").columns))

    def test_seeded_training_story(self):
        std = sk.session_standards(self.s)
        log = data.read("training_log")
        verdicts = {(l["module_id"], op): l["verdict"] for op in ("OP1001", "OP1002", "OP1004")
                    for l in sk.training_loops(self.s, std, op, log)}
        self.assertEqual(verdicts[("fuel", "OP1001")], "verified")
        self.assertEqual(verdicts[("fuel", "OP1004")], "adapt")


class TestLiveSimulation(unittest.TestCase):
    """Demo scenarios are deterministic: no spontaneous proximity alerts, and the worker scenario persists."""

    def nearest(self, demo, tick):
        r = data.live_reading("Excavator", tick, np.random.default_rng(tick), demo)
        return min(r["objects"], key=lambda o: o[1])

    def test_normal_state_stays_outside_caution_zone(self):
        for tick in range(1, 500):
            self.assertGreater(self.nearest({}, tick)[1], 6.0, f"object entered the 6 m caution zone at tick {tick}")

    def test_worker_approaching_persists_at_fixed_position(self):
        for tick in range(1, 200):
            bearing, dist, kind = self.nearest({"person_close": True}, tick)
            self.assertEqual((kind, dist, bearing), ("Worker", 1.6, 20.0))

    def test_clearing_worker_returns_to_normal(self):
        self.assertLess(self.nearest({"person_close": True}, 42)[1], 3.0)
        self.assertGreater(self.nearest({"person_close": False}, 43)[1], 6.0)


class TestRuleEnginesAndOffline(unittest.TestCase):
    def test_fatigue_indicator(self):
        low = an.fatigue_risk_indicator(2, 1, 25, 0)
        high = an.fatigue_risk_indicator(11, 5, 42, 6)
        self.assertEqual(low[1], "Low")
        self.assertEqual(high[1], "High")
        self.assertLessEqual(high[0], 100)
        self.assertIn("not a medical", an.fatigue_risk_indicator.__doc__.lower())

    def test_offline_lesson_video_is_a_valid_mp4(self):
        mp4 = data.ROOT / "training_videos" / "terrain.mp4"
        self.assertTrue(mp4.exists())
        self.assertEqual(mp4.read_bytes()[4:8], b"ftyp")

    def test_planner_baseline(self):
        self.assertEqual(data.planner_estimate_min("Trenching", "Gravel", 60), 60.0)
        self.assertEqual(data.planner_estimate_min("Trenching", "Gravel", 60, "Rainy"), 70.0)  # 69 → rounded to 5
        vol = data.volume_from_estimate("Trenching", "Gravel", 60)
        self.assertAlmostEqual(vol, 60.0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
