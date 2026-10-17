"""Deterministic 12-bed protocol replay; no clinical or model-performance claim."""

import unittest

from sentinelward_ml.live_contract import build_research_verdict
from sentinelward_ml.windows import VitalsWindowAssembler


START = 1792112400000  # five-second aligned epoch milliseconds
ALARM_CODES = ("ASYSTOLE", "BRADY", "TACHY", "VTACH", "VFIB")


def vitals(bed_number, second, *, device_number=None, alarm=None, ppg=True):
    bed = f"B{bed_number:02d}"
    device = f"MON-{(device_number or bed_number):02d}"
    return {
        "v": 1, "type": "vitals", "bed_id": bed, "device_id": device,
        "ts": START + second * 1000, "seq": second, "fs": 125,
        "ecg": [float(bed_number)] * 125,
        "ppg": [float(bed_number) / 10] * 125 if ppg else None,
        "monitor_alarm": ({"code": alarm, "priority": "high"} if alarm else None),
    }


class TwelveBedReplayTest(unittest.TestCase):
    def test_interleaved_beds_hops_alarm_retention_and_missing_ppg(self):
        assembler = VitalsWindowAssembler()
        windows = []
        for second in range(15):
            for bed_number in range(1, 13):
                alarm = ALARM_CODES[bed_number - 1] if second == 9 and bed_number <= 5 else None
                window = assembler.ingest(vitals(
                    bed_number, second, alarm=alarm, ppg=bed_number != 12))
                if window is not None:
                    windows.append(window)

        self.assertEqual(len(windows), 24)
        self.assertEqual({w["bed_id"] for w in windows},
                         {f"B{n:02d}" for n in range(1, 13)})
        for bed_number in range(1, 13):
            bed = f"B{bed_number:02d}"
            own = [w for w in windows if w["bed_id"] == bed]
            self.assertEqual([w["window_start"] for w in own], [START, START + 5000])
            for w in own:
                self.assertEqual(len(w["ecg"]), 1250)
                self.assertEqual(len(w["ppg"]), 1250)
                self.assertEqual(set(w["ecg"]), {float(bed_number)})
                self.assertTrue(all(w["ecg_valid"]))
                self.assertEqual(any(w["ppg_valid"]), bed_number != 12)
                if bed_number == 12:
                    self.assertEqual(set(w["ppg"]), {None})
                expected_alarm = ALARM_CODES[bed_number - 1] if bed_number <= 5 else None
                self.assertEqual([a["code"] for a in w["monitor_alarms"]],
                                 [expected_alarm] if expected_alarm else [])
                verdict = build_research_verdict(
                    bed_id=bed, window_start=w["window_start"],
                    ts=w["window_start"] + 10000,
                    monitor_alarm=w["monitor_alarms"][0] if expected_alarm else None,
                )
                self.assertEqual(verdict["verdict"],
                                 "EMERGENCY" if expected_alarm else "UNSURE")
                self.assertTrue(all(score is None for score in verdict["scores"].values()))

    def test_one_bed_gap_does_not_reset_other_beds(self):
        assembler = VitalsWindowAssembler()
        emitted = []
        for second in range(15):
            for bed_number in range(1, 13):
                if bed_number == 7 and second == 5:
                    continue
                window = assembler.ingest(vitals(bed_number, second))
                if window:
                    emitted.append(window)
        self.assertEqual(len(emitted), 22)
        self.assertFalse(any(w["bed_id"] == "B07" for w in emitted))
        self.assertEqual(sum(w["bed_id"] == "B08" for w in emitted), 2)


if __name__ == "__main__":
    unittest.main()
