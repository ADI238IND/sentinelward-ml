"""Safety invariants for the research-only live contract bridge."""

import unittest

from sentinelward_ml.live_contract import build_research_verdict


START = 1792112400000
ISSUED = START + 10000


def envelope(target, score=0.8, **changes):
    value = {"bed_id": "B01", "window_start": START, "target": target,
             "score": score, "model_version": "research-v1"}
    return value | changes


class LiveContractTest(unittest.TestCase):
    def verdict(self, **changes):
        arguments = {"bed_id": "B01", "window_start": START, "ts": ISSUED,
                     "monitor_alarm": None}
        return build_research_verdict(**(arguments | changes))

    def test_missing_models_never_claim_normal(self):
        result = self.verdict()
        self.assertEqual(result["verdict"], "UNSURE")
        self.assertEqual(set(result["scores"]), {f"M{i}" for i in range(1, 7)})
        self.assertTrue(all(value is None for value in result["scores"].values()))
        self.assertIsNone(result["confidence"])

    def test_monitor_emergency_survives_missing_or_suspicious_models(self):
        result = self.verdict(monitor_alarm={"code": "VTACH", "priority": "high"}, score_envelopes={
            "M3": envelope("synthetic_attack_window", 0.99)})
        self.assertEqual((result["verdict"], result["priority"]), ("EMERGENCY", "high"))
        self.assertIn("MONITOR_VTACH", result["reasons"])
        self.assertIsNone(result["scores"]["M5"])

    def test_correct_score_keeps_source_specific_meaning(self):
        result = self.verdict(score_envelopes={
            "M2": envelope("true_vt_alarm", 0.91)})
        self.assertEqual(result["scores"]["M2"], 0.91)
        self.assertEqual(result["verdict"], "UNSURE")

    def test_reject_wrong_target_bed_window_and_invalid_scores(self):
        good = envelope("true_vt_alarm")
        for bad in [good | {"target": "potential_medical_emergency"},
                    good | {"bed_id": "B02"},
                    good | {"window_start": START + 5000},
                    good | {"score": float("nan")},
                    good | {"score": True}, good | {"score": 1.1}]:
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                self.verdict(score_envelopes={"M2": bad})

    def test_reject_unavailable_m5_and_batch_m6_as_per_bed_scores(self):
        for model in ("M5", "M6"):
            with self.subTest(model=model), self.assertRaises(ValueError):
                self.verdict(score_envelopes={model: envelope("unknown")})

    def test_reject_stale_and_off_grid_windows(self):
        for changes in [{"ts": START + 60000},
                        {"window_start": START + 1},
                        {"ts": START + 9000}]:
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                self.verdict(**changes)

    def test_invalid_alarm_never_silently_clears(self):
        with self.assertRaises(ValueError):
            self.verdict(monitor_alarm={"code": "UNKNOWN", "priority": "high"})


if __name__ == "__main__":
    unittest.main()
