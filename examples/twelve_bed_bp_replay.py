"""Deterministic twelve-bed synthetic replay of protocol and ART/NIBP evidence.

Run: python -m examples.twelve_bed_bp_replay
No real patient data, calibrated score, broker, or clinical verdict is involved.
"""

import json
from math import pi, sin

from sentinelward_ml.live_contract import build_research_verdict
from sentinelward_ml.m6_bp_research import ResearchBPDriftWatcher
from sentinelward_ml.windows import VitalsWindowAssembler


START = 1792112400000
ALARMS = ("ASYSTOLE", "BRADY", "TACHY", "VTACH", "VFIB")
WAVE = [sin(2 * pi * i / 125) for i in range(1250)]


def _art(mean=100.0, amplitude=18.0):
    return [mean + amplitude * value for value in WAVE]


def _vitals(bed, second):
    alarm = ALARMS[bed - 1] if bed <= 5 and second == 9 else None
    return {
        "v": 1, "type": "vitals", "bed_id": f"B{bed:02d}",
        "device_id": f"MON-{bed:02d}", "ts": START + 1000 * second,
        "seq": second, "fs": 125,
        "ecg": [float(bed)] * 125,
        "ppg": None if bed == 12 else [float(bed) / 10] * 125,
        "monitor_alarm": {"code": alarm, "priority": "high"} if alarm else None,
    }


def _bp_window(bed, step, art, cuff):
    start = START + 5000 * step
    return {
        "bed_id": f"B{bed:02d}", "device_id": f"MON-{bed:02d}",
        "patient_id": f"SYNTH-P{bed:02d}",
        "window_start": start, "window_s": 10, "sample_rate_hz": 125,
        "art": art, "nibp_mbp": cuff,
        # One cuff measurement per minute, carried with its original time.
        "nibp_ts": start + 10_000 - (step % 12) * 5000 if cuff is not None else None,
        "hr_bpm": 72, "pat_ms": 180, "pulse_amp": 18,
    }


def run():
    assembler = VitalsWindowAssembler()
    verdicts = []
    windows = []
    for second in range(20):
        for bed in range(1, 13):
            if bed == 7 and second == 5:
                continue  # one bed's missing chunk must not reset other beds
            window = assembler.ingest(_vitals(bed, second))
            if window is None:
                continue
            windows.append(window)
            verdicts.append(build_research_verdict(
                bed_id=window["bed_id"], window_start=window["window_start"],
                ts=START + (second + 1) * 1000,
                monitor_alarm=(window["monitor_alarms"][-1]
                               if window["monitor_alarms"] else None),
            ))

    watcher = ResearchBPDriftWatcher()
    normal = _art()
    for step in range(180):
        for bed in range(1, 13):
            watcher.ingest(_bp_window(bed, step, normal, 100.0))

    final = {}
    for step in range(180, 240):
        for bed in range(1, 13):
            if bed == 7 and step == 200:
                continue
            art, cuff = normal, 100.0
            if bed == 1:  # ART zero-shift while cuff stays steady
                art = _art(115)
            elif bed == 2:  # true pressure fall confirmed by both sensors
                art, cuff = _art(75), 75.0
            elif bed == 3:  # cuff missing cannot become a normal result
                cuff = None
            elif bed == 4:  # unusable ART must fail closed
                art = [100.0] * 1250
            elif bed == 5:  # damped but non-flat waveform
                art = _art(100, 7)
            elif bed == 6:  # controlled 5-minute, 15 mmHg zero-drift ramp
                art = _art(100 + 15 * (step - 180) / 59)
            try:
                result = watcher.ingest(_bp_window(bed, step, art, cuff))
                extra = result["extra"]
                final[result["bed_id"]] = {
                    "score": result["score"],
                    "inputs_sufficient": extra["inputs_sufficient"],
                    "gap_mmhg": extra["gap_mmhg"],
                    "page_hinkley": extra["page_hinkley"],
                    "shape_ratio": extra["shape_ratio"],
                    "emergency_compatible": extra["emergency_compatible"],
                }
            except ValueError as exc:
                final[f"B{bed:02d}"] = {
                    "score": None, "inputs_sufficient": False,
                    "reason": str(exc),
                }

    assert len(windows) == 34 and len(verdicts) == 34
    assert [w["window_start"] for w in windows if w["bed_id"] == "B07"] == [START + 10_000]
    assert sum(v["verdict"] == "EMERGENCY" for v in verdicts) == 10
    assert all(v["scores"]["M6"] is None for v in verdicts)
    assert final["B01"]["gap_mmhg"] >= 10
    assert final["B02"]["emergency_compatible"]
    assert not final["B03"]["inputs_sufficient"]
    assert not final["B04"]["inputs_sufficient"]
    assert final["B05"]["shape_ratio"] < 0.5
    assert final["B06"]["gap_mmhg"] >= 14.9
    assert not final["B07"]["inputs_sufficient"]
    assert final["B08"]["inputs_sufficient"]
    assert all(value["score"] is None for value in final.values())
    return {
        "fixture": "synthetic research only", "beds": 12,
        "vitals_windows": len(windows), "research_verdicts": len(verdicts),
        "emergency_verdicts": sum(v["verdict"] == "EMERGENCY" for v in verdicts),
        "bp_baseline_minutes": 15,
        "bp_postbaseline_windows_per_bed": 60,
        "gap_bed": "B07", "gap_bed_vitals_windows": 1,
        "gap_bed_bp_window_missing": 200,
        "m6_calibrated_scores": 0,
        "scenario_evidence": {bed: final[bed] for bed in
                              ("B01", "B02", "B03", "B04", "B05", "B06", "B07", "B08")},
    }


if __name__ == "__main__":
    print(json.dumps(run(), indent=2, sort_keys=True))
