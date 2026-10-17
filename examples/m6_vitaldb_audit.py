"""Reproducible VitalDB ART/NIBP feasibility audit; never emits an M6 score.

Usage in a network-enabled Python 3.12/3.13 runtime::

    python -m pip install 'vitaldb>=1.7,<2' 'numpy>=2,<3'
    python -m examples.m6_vitaldb_audit --waveform-cases 12

Only metadata and aggregate signal-quality summaries are written. The source is
intraoperative surgical data, not an independently labelled ward drift set.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import random
import time
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import urlopen


API = "https://api.vitaldb.net"
TRACKS = ("SNUADC/ART", "Solar8000/ART_MBP", "Solar8000/NIBP_MBP")
SEED = 20261017


def parse_metadata(cases_csv: str, tracks_csv: str) -> dict:
    """Build a patient-disjoint split from the publisher's case and track tables."""
    tracks_by_case = defaultdict(set)
    for row in csv.DictReader(io.StringIO(tracks_csv.lstrip("\ufeff"))):
        tracks_by_case[int(row["caseid"])].add(row["tname"])

    candidate = []
    all_cases = 0
    for row in csv.DictReader(io.StringIO(cases_csv.lstrip("\ufeff"))):
        all_cases += 1
        case_id = int(row["caseid"])
        names = tracks_by_case[case_id]
        if TRACKS[0] not in names or TRACKS[2] not in names:
            continue
        subject = row.get("subjectid", "").strip()
        if not subject:
            continue
        try:
            duration_s = float(row["caseend"]) - float(row["casestart"])
        except (ValueError, KeyError):
            continue
        candidate.append({
            "caseid": case_id, "subjectid": subject,
            "duration_s": duration_s,
            "art_mbp_track": TRACKS[1] in names,
        })

    subjects = sorted({row["subjectid"] for row in candidate})
    random.Random(SEED).shuffle(subjects)
    n = len(subjects)
    cut1, cut2 = round(n * .70), round(n * .85)
    membership = {subject: ("train" if i < cut1 else
                            "validation" if i < cut2 else "test")
                  for i, subject in enumerate(subjects)}
    for row in candidate:
        row["split"] = membership[row["subjectid"]]
    assert len({row["subjectid"] for row in candidate if row["split"] == "train"}
               & {row["subjectid"] for row in candidate if row["split"] == "validation"}) == 0
    assert len({row["subjectid"] for row in candidate if row["split"] == "train"}
               & {row["subjectid"] for row in candidate if row["split"] == "test"}) == 0
    assert len({row["subjectid"] for row in candidate if row["split"] == "validation"}
               & {row["subjectid"] for row in candidate if row["split"] == "test"}) == 0

    # A replay uses distinct people and enough recorded duration for a baseline.
    selected, seen = [], set()
    for row in sorted(candidate, key=lambda r: r["caseid"]):
        if (row["split"] == "train" and row["duration_s"] >= 1800
                and row["subjectid"] not in seen):
            selected.append(row["caseid"])
            seen.add(row["subjectid"])
            if len(selected) == 12:
                break
    return {
        "source_case_count": all_cases,
        "paired_track_case_count": len(candidate),
        "paired_track_subject_count": len(subjects),
        "split_case_counts": dict(Counter(r["split"] for r in candidate)),
        "split_subject_counts": dict(Counter(membership.values())),
        "candidate_12_bed_caseids": selected,
        "split_seed": SEED,
        "candidates": candidate,
    }


def fetch_text(url: str) -> str:
    with urlopen(url, timeout=120) as response:
        return response.read().decode("utf-8-sig")


def audit_waveform(case_id: int, max_minutes: int = 40) -> dict:
    """Check 125 Hz paired samples; do not infer true cuff event times."""
    import numpy as np
    import vitaldb

    # The publisher's per-case Parquet URL preserves the original track names.
    vf = vitaldb.VitalFile(f"{API}/{case_id}.parquet")
    values = np.asarray(vf.to_numpy([TRACKS[0], TRACKS[2]], 1 / 125))
    if values.ndim != 2 or values.shape[1] != 2:
        raise RuntimeError(f"Unexpected VitalDB output shape for case {case_id}: {values.shape}")
    values = values[:max_minutes * 60 * 125]
    art, nibp = values[:, 0], values[:, 1]
    valid_art = np.isfinite(art) & (art >= 0) & (art <= 300)
    valid_nibp = np.isfinite(nibp) & (nibp >= 20) & (nibp <= 250)
    window_samples, hop_samples = 1250, 625
    window_count = max(0, (len(values) - window_samples) // hop_samples + 1)
    art_usable = paired_present = 0
    first_usable_second = None
    for i in range(window_count):
        start = i * hop_samples
        stop = start + window_samples
        segment = art[start:stop]
        good = valid_art[start:stop]
        if good.mean() >= .99 and np.ptp(segment[good]) >= 5:
            art_usable += 1
            if first_usable_second is None:
                first_usable_second = start / 125
            if valid_nibp[start:stop].any():
                paired_present += 1
    return {
        "caseid": case_id,
        "audited_minutes": round(len(values) / 125 / 60, 2),
        "total_ten_second_windows_at_five_second_hop": window_count,
        "art_technically_usable_windows": art_usable,
        "windows_with_art_and_a_displayed_nibp_value": paired_present,
        "first_usable_art_second": first_usable_second,
        "art_finite_plausible_fraction": round(float(valid_art.mean()), 4) if len(values) else 0,
        "nibp_finite_plausible_fraction": round(float(valid_nibp.mean()), 4) if len(values) else 0,
        "cuff_measurement_timestamps_verified": False,
        "note": "Displayed/held cuff values do not establish measurement times or freshness.",
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--waveform-cases", type=int, default=12,
                        help="Number of patient-distinct training cases to audit (0-12)")
    parser.add_argument("--output", type=Path, default=Path("results/m6_vitaldb_audit.json"))
    args = parser.parse_args()
    if not 0 <= args.waveform_cases <= 12:
        parser.error("--waveform-cases must be between 0 and 12")

    started = time.monotonic()
    print("Fetching official VitalDB metadata; initial ETA ~10-60 s.", flush=True)
    cases_csv = fetch_text(f"{API}/cases")
    tracks_csv = fetch_text(f"{API}/trks")
    parsed = parse_metadata(cases_csv, tracks_csv)
    candidate = parsed.pop("candidates")
    report = {
        "status": "technical_feasibility_only_no_drift_labels",
        "source": API,
        "retrieved_utc": datetime.now(timezone.utc).isoformat(),
        "cases_csv_sha256": hashlib.sha256(cases_csv.encode()).hexdigest(),
        "tracks_csv_sha256": hashlib.sha256(tracks_csv.encode()).hexdigest(),
        **parsed,
        "waveform_audit": [],
        "limitations": [
            "VitalDB cases are intraoperative surgical cases, not target-ward cases.",
            "Track presence does not establish usable synchronized samples.",
            "A displayed or held NIBP value is not a verified cuff measurement timestamp.",
            "No independently labelled arterial-sensor drift or genuine-hypotension outcomes.",
        ],
        "m6_live_score_authorized": False,
    }
    assert len(report["candidate_12_bed_caseids"]) == 12, "Fewer than 12 eligible train subjects"
    print("Paired-track cases:", report["paired_track_case_count"],
          "| patient-disjoint split:", report["split_case_counts"], flush=True)
    print("Candidate 12-bed case IDs:", report["candidate_12_bed_caseids"], flush=True)
    for index, case_id in enumerate(report["candidate_12_bed_caseids"][:args.waveform_cases], 1):
        item = audit_waveform(case_id)
        report["waveform_audit"].append(item)
        elapsed = time.monotonic() - started
        eta = elapsed / index * (args.waveform_cases - index) if index else 0
        print(f"Waveform {index}/{args.waveform_cases}: case {case_id}, "
              f"usable ART+displayed NIBP windows {item['windows_with_art_and_a_displayed_nibp_value']} "
              f"| elapsed {elapsed:.0f}s | ETA ~{eta:.0f}s", flush=True)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print("Saved:", args.output, "| M6 score issued: NO", flush=True)


if __name__ == "__main__":
    main()
