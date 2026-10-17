"""Deterministic synthetic one-bed wiring demo; no trained model is invoked."""

import json
from math import pi, sin

from sentinelward_ml import VitalsWindowAssembler, build_research_verdict

START_MS = 1792112400000


def run():
    assembler = VitalsWindowAssembler()
    verdicts = []
    for second in range(15):
        ecg = [sin(2 * pi * 1.2 * (second + i / 125)) for i in range(125)]
        ppg = [sin(2 * pi * 1.2 * (second + i / 125 - 0.2)) for i in range(125)]
        msg = {"v": 1, "type": "vitals", "bed_id": "B01", "device_id": "MON-01",
               "seq": second, "ts": START_MS + 1000 * second, "fs": 125,
               "ecg": ecg, "ppg": ppg,
               "monitor_alarm": {"code": "VTACH", "priority": "high"} if second == 3 else None}
        window = assembler.ingest(msg)
        if window is not None:
            verdicts.append(build_research_verdict(
                bed_id=window["bed_id"], window_start=window["window_start"],
                ts=msg["ts"] + 1000,
                monitor_alarm=window["monitor_alarms"][-1] if window["monitor_alarms"] else None,
            ))
    return verdicts


if __name__ == "__main__":
    print(json.dumps(run(), indent=2))

