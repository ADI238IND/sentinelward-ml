"""Offline ART/NIBP drift evidence for the lead-specified M6 task.

This is deliberately not a calibrated M6 score or a live publisher. The shared
Drive contains no paired, labelled ART/NIBP training set. Keeping the result
as evidence prevents a synthetic rule from masquerading as a clinical model.
"""

from __future__ import annotations

from collections import deque
from math import isfinite
from statistics import fmean, median
import re


SAMPLES_PER_WINDOW = 1250  # 125 Hz x 10 seconds
BASELINE_WINDOWS = 180     # five-second hops across 15 minutes
MAX_CUFF_AGE_MS = 60_000


def _number(value, name, low, high):
    if isinstance(value, (bool, str, bytes)):
        raise ValueError(f"{name} must be numeric")
    try:
        number = float(value)
    except (TypeError, ValueError, OverflowError) as exc:
        raise ValueError(f"{name} must be numeric") from exc
    if not isfinite(number) or not low <= number <= high:
        raise ValueError(f"{name} outside supported research range")
    return number


def _optional_number(value, name, low, high):
    return None if value is None else _number(value, name, low, high)


def extract_art_features(samples):
    """Return robust MAP and pulse range; reject absent/flat/implausible ART."""
    if not isinstance(samples, (list, tuple)) or len(samples) != SAMPLES_PER_WINDOW:
        raise ValueError("art must contain exactly 1250 native 125 Hz samples")
    values = [_number(value, "art sample", 0, 300) for value in samples]
    ordered = sorted(values)
    pulse_range = ordered[1187] - ordered[62]  # approximate P95-P5
    if pulse_range < 5:
        raise ValueError("ART is flat or too damped for reliable MAP evidence")
    return {"art_mbp": float(fmean(ordered[62:1188])),
            "art_pulse_range": float(pulse_range)}


class ResearchBPDriftWatcher:
    """Per-bed, fail-closed feature tracker for synthetic/offline study only.

    Baseline statistics and Page-Hinkley evidence are reported, but no score or
    drift label is issued. Thresholds, patient-wise evaluation and genuine-
    hypotension safety evidence must come from paired ART/NIBP cases.
    """

    def __init__(self):
        self._beds = {}

    def reset(self):
        self._beds.clear()

    def ingest(self, window):
        if not isinstance(window, dict):
            raise ValueError("Expected an ART/NIBP research window")
        bed = window.get("bed_id")
        device = window.get("device_id")
        patient = window.get("patient_id")
        start = window.get("window_start")
        if not isinstance(bed, str) or re.fullmatch(r"B(0[1-9]|1[0-2])", bed) is None:
            raise ValueError("Unknown bed_id")
        if not isinstance(device, str) or re.fullmatch(r"MON-(0[1-9]|1[0-2])", device) is None:
            raise ValueError("Unknown device_id")
        if not isinstance(patient, str) or not patient.strip() or len(patient) > 80:
            raise ValueError("patient_id is required for per-patient baseline isolation")
        if type(start) is not int or start < 0 or start % 5000:
            raise ValueError("window_start must be five-second aligned epoch milliseconds")
        if window.get("window_s") != 10 or window.get("sample_rate_hz") != 125:
            raise ValueError("Expected ten seconds of native 125 Hz ART")

        # Validate before touching state, so malformed data cannot corrupt a bed.
        features = extract_art_features(window.get("art"))
        hr = _optional_number(window.get("hr_bpm"), "hr_bpm", 20, 250)
        pat = _optional_number(window.get("pat_ms"), "pat_ms", 40, 1000)
        amplitude = _optional_number(window.get("pulse_amp"), "pulse_amp", 0, 300)
        cuff = window.get("nibp_mbp")
        cuff_ts = window.get("nibp_ts")
        if (cuff is None) != (cuff_ts is None):
            raise ValueError("NIBP value and timestamp must arrive together")
        if cuff is not None:
            cuff = _number(cuff, "nibp_mbp", 20, 250)
            if type(cuff_ts) is not int or not 0 <= start + 10_000 - cuff_ts <= MAX_CUFF_AGE_MS:
                raise ValueError("NIBP timestamp is future or stale")

        state = self._beds.get(bed)
        if state is None or state["device"] != device or state["patient"] != patient:
            state = {"device": device, "patient": patient, "last_start": None,
                     "baseline": deque(maxlen=BASELINE_WINDOWS), "reference": None,
                     "ph_mean": 0.0, "ph_sum": 0.0, "ph_min": 0.0,
                     "ph_max": 0.0, "ph_count": 0}
            self._beds[bed] = state
        last = state["last_start"]
        if last is not None and start <= last:
            raise ValueError("Duplicate or out-of-order M6 window")
        if last is not None and start != last + 5000:
            # A missing interval invalidates temporal evidence and baseline.
            state["baseline"].clear()
            state["reference"] = None
            state.update(ph_mean=0.0, ph_sum=0.0, ph_min=0.0,
                         ph_max=0.0, ph_count=0)
        state["last_start"] = start

        art_mbp = features["art_mbp"]
        gap = None if cuff is None else art_mbp - cuff
        if state["reference"] is None and gap is not None:
            state["baseline"].append((art_mbp, cuff, gap,
                                      features["art_pulse_range"]))
            if len(state["baseline"]) == BASELINE_WINDOWS:
                rows = list(state["baseline"])
                state["reference"] = {
                    "art_mbp": median(row[0] for row in rows),
                    "nibp_mbp": median(row[1] for row in rows),
                    "gap_mmhg": median(row[2] for row in rows),
                    "pulse_range": median(row[3] for row in rows),
                }
                state["ph_count"] = BASELINE_WINDOWS

        reference = state["reference"]
        emergency_compatible = False
        ph = None
        shape_ratio = None
        if reference is not None and gap is not None:
            # Both measurements falling is emergency-compatible, not a drift
            # declaration. This is only an offline safeguard candidate.
            emergency_compatible = (
                cuff <= reference["nibp_mbp"] - 10
                and art_mbp <= reference["art_mbp"] - 10
            )
            residual = gap - reference["gap_mmhg"]
            count = state["ph_count"] + 1
            state["ph_mean"] += (residual - state["ph_mean"]) / count
            state["ph_sum"] += residual - state["ph_mean"]
            state["ph_min"] = min(state["ph_min"], state["ph_sum"])
            state["ph_max"] = max(state["ph_max"], state["ph_sum"])
            state["ph_count"] = count
            ph = max(state["ph_sum"] - state["ph_min"],
                     state["ph_max"] - state["ph_sum"])
            shape_ratio = features["art_pulse_range"] / reference["pulse_range"]

        return {
            "bed_id": bed, "device_id": device, "patient_id": patient,
            "window_start": start,
            "type": "research_bp_evidence", "model": "M6",
            "model_version": "m6-bp-research-v0-uncalibrated",
            "score": None, "label": "insufficient_data",
            "reason": "Uncalibrated research evidence; no live M6 score",
            "extra": {
                **features, "nibp_mbp": cuff, "gap_mmhg": gap,
                "baseline_windows": len(state["baseline"]),
                "baseline_ready": reference is not None,
                "page_hinkley": ph, "shape_ratio": shape_ratio,
                "emergency_compatible": emergency_compatible,
                "hr_bpm": hr, "pat_ms": pat, "pulse_amp": amplitude,
                "inputs_sufficient": reference is not None and cuff is not None,
            },
        }
