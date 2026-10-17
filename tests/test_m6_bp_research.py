"""Guardrails for the uncalibrated blood-pressure M6 research adapter."""

import unittest

from examples.twelve_bed_bp_replay import START, _art, _bp_window, run
from sentinelward_ml.m6_bp_research import ResearchBPDriftWatcher


class M6BPResearchTest(unittest.TestCase):
    def test_twelve_bed_replay_has_safety_and_missing_data_cases(self):
        report = run()
        self.assertEqual(report["beds"], 12)
        self.assertEqual(report["vitals_windows"], 34)
        self.assertEqual(report["gap_bed"], "B07")
        self.assertEqual(report["gap_bed_vitals_windows"], 1)
        self.assertEqual(report["m6_calibrated_scores"], 0)
        evidence = report["scenario_evidence"]
        self.assertGreaterEqual(evidence["B01"]["gap_mmhg"], 10)
        self.assertTrue(evidence["B02"]["emergency_compatible"])
        self.assertFalse(evidence["B03"]["inputs_sufficient"])
        self.assertFalse(evidence["B04"]["inputs_sufficient"])
        self.assertLess(evidence["B05"]["shape_ratio"], 0.5)
        self.assertGreaterEqual(evidence["B06"]["gap_mmhg"], 14.9)
        self.assertFalse(evidence["B07"]["inputs_sufficient"])
        self.assertTrue(evidence["B08"]["inputs_sufficient"])

    def test_bad_cuff_does_not_advance_bed_and_other_bed_is_independent(self):
        watcher = ResearchBPDriftWatcher()
        good = _bp_window(1, 0, _art(), 100)
        stale = good | {"nibp_ts": START - 60_000}
        with self.assertRaises(ValueError):
            watcher.ingest(stale)
        self.assertEqual(watcher.ingest(good)["extra"]["baseline_windows"], 1)
        self.assertEqual(watcher.ingest(_bp_window(2, 0, _art(), 100))
                         ["extra"]["baseline_windows"], 1)
        with self.assertRaises(ValueError):
            watcher.ingest(good)
        # A gap resets only B01's temporal evidence.
        self.assertEqual(watcher.ingest(_bp_window(1, 2, _art(), 100))
                         ["extra"]["baseline_windows"], 1)
        self.assertEqual(watcher.ingest(_bp_window(2, 1, _art(), 100))
                         ["extra"]["baseline_windows"], 2)
        # A new patient on the same bed and device starts a new baseline.
        changed = _bp_window(2, 2, _art(), 100) | {"patient_id": "SYNTH-NEW"}
        self.assertEqual(watcher.ingest(changed)["extra"]["baseline_windows"], 1)

    def test_flat_art_and_malformed_alignment_fail_closed(self):
        watcher = ResearchBPDriftWatcher()
        for window in (
            _bp_window(1, 0, [100.0] * 1250, 100),
            _bp_window(1, 0, _art()[:1249], 100),
            _bp_window(1, 0, _art(), 100) | {"window_start": START + 1},
            _bp_window(1, 0, _art(), 100) | {"nibp_mbp": None},
        ):
            with self.subTest(window=str(window.keys())), self.assertRaises(ValueError):
                watcher.ingest(window)


if __name__ == "__main__":
    unittest.main()
