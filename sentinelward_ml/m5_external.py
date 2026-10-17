"""Validate Kartik's asynchronous M5 event without treating it as a ward verdict.

The caller must supply the device ID authenticated by the MQTT transport. This
module intentionally does not load or redistribute Kartik's model artifact.
"""

from __future__ import annotations

from math import isfinite


def validate_m5_event(event, *, authenticated_device_id, now_ms, max_age_ms=15000):
    """Return a bounded advisory M5 observation, or raise ValueError.

    M5 has no vitals ``window_start`` in its source contract, so its score
    cannot be inserted into the locked per-bed, per-window verdict as M5.
    """
    required = {"device_id", "detector", "status", "network_suspicion_score",
                "model_version", "reasons", "observed_at"}
    if not isinstance(event, dict) or not required <= event.keys():
        raise ValueError("M5 event is incomplete")
    if not isinstance(authenticated_device_id, str) or not authenticated_device_id:
        raise ValueError("Authenticated device ID is required")
    if event["device_id"] != authenticated_device_id or event["detector"] != "M5":
        raise ValueError("M5 event device or detector mismatch")
    if event["status"] not in {"active", "degraded", "unavailable"}:
        raise ValueError("Invalid M5 status")
    if not isinstance(event["model_version"], str) or not event["model_version"].strip():
        raise ValueError("M5 model version is missing")
    if (not isinstance(event["reasons"], list) or
            any(not isinstance(item, str) for item in event["reasons"])):
        raise ValueError("Invalid M5 reasons")
    stamp = event["observed_at"]
    if isinstance(stamp, bool) or not isinstance(stamp, (int, float)) or not isfinite(stamp):
        raise ValueError("M5 observed_at must be Unix seconds")
    if isinstance(now_ms, bool) or not isinstance(now_ms, int) or now_ms < 0:
        raise ValueError("now_ms must be Unix milliseconds")
    if isinstance(max_age_ms, bool) or not isinstance(max_age_ms, int) or max_age_ms <= 0:
        raise ValueError("Invalid maximum M5 age")
    observed_ms = round(stamp * 1000)
    if observed_ms > now_ms + 2000 or now_ms - observed_ms > max_age_ms:
        raise ValueError("M5 event is stale or future-dated")
    score = event["network_suspicion_score"]
    if event["status"] == "active":
        if isinstance(score, (bool, str, bytes)):
            raise ValueError("Active M5 score must be numeric")
        try:
            score = float(score)
        except (TypeError, ValueError, OverflowError) as exc:
            raise ValueError("Active M5 score must be numeric") from exc
        if not isfinite(score) or not 0 <= score <= 1:
            raise ValueError("Active M5 score must be finite in [0,1]")
    elif score is not None:
        raise ValueError("Unavailable or degraded M5 must have null score")
    return {
        "device_id": authenticated_device_id,
        "observed_at_ms": observed_ms,
        "status": event["status"],
        "score": score,
        "target": "synthetic_network_anomaly",
        "model_version": event["model_version"],
        "reasons": list(event["reasons"]),
    }
