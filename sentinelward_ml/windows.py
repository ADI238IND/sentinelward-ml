"""Strict, per-bed 10-second windows from the locked 125 Hz vitals messages.

This module assembles data; it does not resample, infer an attack, or make a
clinical decision. Malformed or missing chunks cannot be silently zero-filled.
"""

from __future__ import annotations

from collections import deque
from math import isfinite
import re

ALARM_CODES = frozenset({"ASYSTOLE", "BRADY", "TACHY", "VTACH", "VFIB"})


def _samples(message, name):
    values = message.get(name)
    if values is None:
        return None
    if not isinstance(values, list) or len(values) != 125:
        raise ValueError(f"{name} must be null or 125 samples")
    validated = []
    for item in values:
        if item is None:
            validated.append(None)
            continue
        if isinstance(item, (bool, str, bytes)):
            raise ValueError(f"{name} contains a nonnumeric sample")
        try:
            number = float(item)
        except (TypeError, ValueError, OverflowError) as exc:
            raise ValueError(f"{name} contains a nonnumeric sample") from exc
        if not isfinite(number):
            raise ValueError(f"{name} contains a nonfinite sample")
        validated.append(number)
    # Snapshot the validated numbers: callers may reuse or mutate their input
    # buffer after ingest, but that must not alter a pending clinical window.
    return validated


def _alarm(value):
    if value is None:
        return None
    if (not isinstance(value, dict) or set(value) != {"code", "priority"}
            or not isinstance(value["code"], str) or value["code"] not in ALARM_CODES
            or not isinstance(value["priority"], str)
            or value["priority"] not in {"high", "medium", "low"}):
        raise ValueError("Invalid monitor_alarm")
    return value.copy()


class VitalsWindowAssembler:
    """Emit a window only after 10 contiguous one-second messages for a bed.

    Sequence or timestamp gaps clear that bed's pending window. Device changes
    also clear it. Upstream authentication and clock synchronization are required.
    """

    def __init__(self):
        self._beds = {}

    def reset(self):
        """Clear all per-bed memory on the locked demo-control reset."""
        self._beds.clear()

    def ingest(self, message):
        if (not isinstance(message, dict) or type(message.get("v")) is not int
                or message["v"] != 1 or message.get("type") != "vitals"):
            raise ValueError("Expected v1 vitals message")
        bed = message.get("bed_id")
        device = message.get("device_id")
        if not isinstance(bed, str) or re.fullmatch(r"B(0[1-9]|1[0-2])", bed) is None:
            raise ValueError("Unknown bed_id")
        if not isinstance(device, str) or re.fullmatch(r"MON-(0[1-9]|1[0-2])", device) is None:
            raise ValueError("Unknown device_id")
        seq = message.get("seq")
        ts = message.get("ts")
        if isinstance(seq, bool) or not isinstance(seq, int) or seq < 0:
            raise ValueError("seq must be a nonnegative integer")
        if isinstance(ts, bool) or not isinstance(ts, int) or ts < 0 or ts % 1000:
            raise ValueError("ts must be an aligned epoch-millisecond integer")
        if message.get("fs") != 125:
            raise ValueError("Expected exactly 125 Hz")
        ecg, ppg = _samples(message, "ecg"), _samples(message, "ppg")
        alarm = _alarm(message.get("monitor_alarm"))
        chunk = {"ts": ts, "seq": seq, "ecg": ecg, "ppg": ppg, "monitor_alarm": alarm}

        state = self._beds.get(bed)
        if state is None or state["device"] != device:
            state = {"device": device, "chunks": deque(maxlen=10), "last_seq": None,
                     "last_ts": None}
            self._beds[bed] = state
        if state["last_seq"] is not None:
            if seq <= state["last_seq"] or ts <= state["last_ts"]:
                raise ValueError("Duplicate or out-of-order vitals message")
            if seq != state["last_seq"] + 1 or ts != state["last_ts"] + 1000:
                state["chunks"].clear()
        state["chunks"].append(chunk)
        state["last_seq"], state["last_ts"] = seq, ts
        end = ts + 1000
        if end % 5000 or len(state["chunks"]) != 10:
            return None

        chunks = list(state["chunks"])
        if chunks[0]["ts"] != end - 10000:
            raise AssertionError("Window lost contiguity")
        ecg = [v for c in chunks for v in (c["ecg"] or [None] * 125)]
        ppg = [v for c in chunks for v in (c["ppg"] or [None] * 125)]
        return {
            "bed_id": bed, "device_id": device, "window_start": end - 10000,
            "window_s": 10, "sample_rate_hz": 125,
            "ecg": ecg, "ppg": ppg,
            "ecg_valid": [v is not None for v in ecg],
            "ppg_valid": [v is not None for v in ppg],
            "monitor_alarms": [c["monitor_alarm"] for c in chunks if c["monitor_alarm"]],
            "seq_first": chunks[0]["seq"], "seq_last": chunks[-1]["seq"],
        }
