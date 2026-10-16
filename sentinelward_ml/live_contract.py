"""Fail-closed research bridge for the locked SentinelWard verdict shape.

This does not implement or replace the trained six-model decision layer. It
keeps original monitor alarms visible while live model integration is pending.
"""

from __future__ import annotations

from math import isfinite
import re

MODEL_TARGETS = {
    "M1": "unacceptable_whole_record",
    "M2": "true_vt_alarm",
    "M3": "synthetic_attack_window",
    "M4": "synthetic_replay_similarity",
    "M5": None,  # No M5 package or positive-class definition is supplied.
    "M6": None,  # Batch metric, not a live per-bed score.
}
ALARM_TYPES = frozenset({"ASYSTOLE", "BRADY", "TACHY", "VTACH", "VFIB"})


def _time(value, name):
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError(f"{name} must be Unix epoch milliseconds")
    return value


def _score_envelope(model, envelope, bed_id, start):
    """Accept a score only with explicit target, bed and window provenance."""
    if envelope is None:
        return None
    if MODEL_TARGETS[model] is None:
        raise ValueError(f"{model} has no validated per-bed score interface")
    if not isinstance(envelope, dict) or set(envelope) != {
        "bed_id", "window_start", "target", "score", "model_version"
    }:
        raise ValueError(f"{model}: incomplete score provenance")
    if envelope["bed_id"] != bed_id or _time(envelope["window_start"], "window_start") != start:
        raise ValueError(f"{model}: bed/window mismatch")
    if envelope["target"] != MODEL_TARGETS[model]:
        raise ValueError(f"{model}: positive-class meaning mismatch")
    if not isinstance(envelope["model_version"], str) or not envelope["model_version"].strip():
        raise ValueError(f"{model}: model version missing")
    value = envelope["score"]
    if isinstance(value, (bool, str, bytes)):
        raise ValueError(f"{model}: score must be numeric")
    try:
        value = float(value)
    except (TypeError, ValueError, OverflowError) as exc:
        raise ValueError(f"{model}: score must be numeric") from exc
    if not isfinite(value) or not 0 <= value <= 1:
        raise ValueError(f"{model}: score must be finite in [0,1]")
    return value


def build_research_verdict(*, bed_id, window_start, ts, monitor_alarm,
                           score_envelopes=None, last_trusted_ts=None):
    """Return a schema-shaped, conservative research verdict.

    Only an independent monitor alarm can produce EMERGENCY. With no alarm,
    research models cannot certify NORMAL, so the result is always UNSURE.
    This function never publishes messages or clears the monitor alarm.
    """
    if not isinstance(bed_id, str) or not re.fullmatch(r"B(0[1-9]|1[0-2])", bed_id):
        raise ValueError("bed_id must be B01–B12")
    start = _time(window_start, "window_start")
    issued = _time(ts, "ts")
    if start % 5000 or not 10000 <= issued - start <= 15000:
        raise ValueError("Expected a 10-second window with a 5-second hop and prompt epoch-ms timestamp")
    if monitor_alarm is not None and (
        not isinstance(monitor_alarm, dict) or
        set(monitor_alarm) != {"code", "priority"} or
        not isinstance(monitor_alarm["code"], str) or
        monitor_alarm["code"] not in ALARM_TYPES or
        not isinstance(monitor_alarm["priority"], str) or
        monitor_alarm["priority"] not in {"high", "medium", "low"}
    ):
        raise ValueError("Invalid monitor_alarm object")
    if last_trusted_ts is not None and _time(last_trusted_ts, "last_trusted_ts") > issued:
        raise ValueError("last_trusted_ts cannot be in the future")
    envelopes = {} if score_envelopes is None else score_envelopes
    if not isinstance(envelopes, dict) or set(envelopes) - set(MODEL_TARGETS):
        raise ValueError("Unknown model score")
    scores = {model: _score_envelope(model, envelopes.get(model), bed_id, start)
              for model in MODEL_TARGETS}
    missing = [model for model, score in scores.items() if score is None]
    emergency = monitor_alarm is not None
    reasons = ([f"MONITOR_{monitor_alarm['code']}"] if emergency else [])
    if missing:
        reasons.append("MISSING_MODEL_SCORES")
    reasons.append("RESEARCH_FUSION_UNVALIDATED")
    return {
        "v": 1, "type": "verdict", "bed_id": bed_id,
        "ts": issued,
        "window_start": start,
        "verdict": "EMERGENCY" if emergency else "UNSURE",
        "priority": "high" if emergency else "medium",
        "confidence": None, "trust": None,
        "last_trusted_ts": last_trusted_ts,
        "reasons": reasons[:3], "scores": scores,
    }
