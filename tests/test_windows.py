"""Windowing contract checks with deliberately incomplete and stale chunks."""

import unittest

from sentinelward_ml.windows import VitalsWindowAssembler
from examples.live_dry_run import run as run_dry_run

START = 1792112400000


def vitals(second, *, bed="B01", device="MON-01", seq=None, alarm=None):
    return {"v": 1, "type": "vitals", "bed_id": bed, "device_id": device,
            "seq": second if seq is None else seq, "ts": START + second * 1000,
            "fs": 125, "ecg": [0.0] * 125, "ppg": [None] * 125,
            "monitor_alarm": alarm}


class VitalsWindowTest(unittest.TestCase):
    def test_end_to_end_synthetic_dry_run(self):
        verdicts = run_dry_run()
        self.assertEqual([v["verdict"] for v in verdicts], ["EMERGENCY", "UNSURE"])
        self.assertEqual([v["window_start"] for v in verdicts], [START, START + 5000])

    def test_contiguous_windows_overlap_at_five_seconds(self):
        builder = VitalsWindowAssembler()
        outputs = [builder.ingest(vitals(second)) for second in range(15)]
        produced = [item for item in outputs if item is not None]
        self.assertEqual([item["window_start"] for item in produced], [START, START + 5000])
        self.assertEqual([item["seq_first"] for item in produced], [0, 5])
        self.assertEqual(len(produced[0]["ecg"]), 1250)
        self.assertEqual(produced[0]["ecg"], [0.0] * 1250)
        self.assertTrue(all(produced[0]["ecg_valid"]))
        self.assertTrue(all(value is None for value in produced[0]["ppg"]))
        self.assertFalse(any(produced[0]["ppg_valid"]))

    def test_alarm_survives_window_assembly(self):
        builder = VitalsWindowAssembler()
        alarm = {"code": "VTACH", "priority": "high"}
        for second in range(9):
            self.assertIsNone(builder.ingest(vitals(second, alarm=alarm if second == 3 else None)))
        self.assertEqual(builder.ingest(vitals(9))["monitor_alarms"], [alarm])

    def test_gap_requires_new_complete_window(self):
        builder = VitalsWindowAssembler()
        for second in range(5):
            builder.ingest(vitals(second))
        self.assertIsNone(builder.ingest(vitals(6, seq=6)))
        for second in range(7, 14):
            self.assertIsNone(builder.ingest(vitals(second)))
        self.assertIsNone(builder.ingest(vitals(14)))
        # The next aligned end is 20 seconds; no stale prior samples are reused.
        for second in range(15, 19):
            self.assertIsNone(builder.ingest(vitals(second)))
        self.assertEqual(builder.ingest(vitals(19))["window_start"], START + 10000)

    def test_duplicate_and_out_of_order_fail(self):
        builder = VitalsWindowAssembler()
        builder.ingest(vitals(0))
        for wrong in (vitals(0), vitals(1, seq=0)):
            with self.assertRaises(ValueError):
                builder.ingest(wrong)

    def test_device_change_and_reset_clear_memory(self):
        builder = VitalsWindowAssembler()
        for second in range(8):
            builder.ingest(vitals(second))
        self.assertIsNone(builder.ingest(vitals(8, device="MON-02")))
        builder.reset()
        self.assertIsNone(builder.ingest(vitals(9, device="MON-02")))

    def test_reject_malformed_samples_and_alarm(self):
        builder = VitalsWindowAssembler()
        for change in ({"ecg": [0.0] * 124}, {"ecg": [float("nan")] * 125},
                       {"ecg": [True] * 125},
                       {"monitor_alarm": {"code": "UNKNOWN", "priority": "high"}},
                       {"fs": 250}, {"ts": START + 1}):
            with self.subTest(change=change), self.assertRaises(ValueError):
                builder.ingest(vitals(0) | change)


if __name__ == "__main__":
    unittest.main()
