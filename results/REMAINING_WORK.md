# Model-by-model readiness and remaining evidence — 17 October 2026

This is a research handoff, not a claim of clinical or security readiness. The
original monitor alarm must remain visible regardless of any model output.

| Component | Completed here | Still required for live use |
|---|---|---|
| M1, ECG quality | Saved five-seed 500 Hz, 12-lead model, frozen test and checked offline adapter. Mean test recall of unacceptable records 0.8353; specificity 0.9328. | A 12-lead 500 Hz live source or a new validated live-domain model. Define handling of missed unacceptable ECGs and validate on actual ward devices and patient-independent data. The 125 Hz two-channel feed cannot directly supply this model. |
| M2, VT alarm | Saved five-seed 250 Hz ECG/PPG VT classifier, frozen test and checked adapter. Mean test VT recall 0.9109; false-alarm specificity 0.7594. | Validate threshold and alarm timing on the target ward. Two of five seeds fell below 0.90 recall on the frozen test. Non-VT emergencies require other monitor logic or separately trained models; M2 cannot stand for all medical emergencies. |
| M3, attack windows | Saved synthetic attack-window classifier and feature adapter for already-preprocessed 125 Hz windows. | Package and verify the pinned raw-to-125 Hz transformation; test real body/sensor mismatch examples across devices and people. Synthetic attack accuracy does not establish clinical body-mismatch detection. |
| M4, replay similarity | Saved offline pairwise replay-similarity model and checked adapter. | Verify raw source channels and implement a defensible trusted reference-window lifecycle. Study off-grid/noisy and unseen-device replay; the supplied off-grid noisy test found 7/12. Do not treat a match as conclusive attack evidence. |
| M5, network model | Kartik's separate public repository has feature extraction, a saved random-forest baseline, event schema and local tests. The source commit and artifact hash are pinned in `M5_EXTERNAL_REVIEW.md`. A new adapter validates asynchronous M5 event identity, freshness and score shape. | The model was trained/tested only on strongly separable synthetic traffic; its reported 330/330 test decisions are not real-network accuracy. Normal synthetic traffic is 2 Hz while the locked vitals stream is 1 Hz. Obtain representative target traffic, independent labels, realistic grouped evaluation, authenticated device-to-bed mapping and timing alignment. M5 remains `null` in the per-window verdict until those are validated. |
| M6, blood-pressure drift | The supplied SHA-256-checked artifact is an exploratory ECG–PPG batch distribution-shift monitor, not the specified blood-pressure M6. | Build and evaluate the lead’s [ART/NIBP arterial-pressure drift design](https://github.com/adityavijay3659-sketch/SentinelWard/blob/main/docs/m6-design.md) with appropriate paired data, patient-wise splits, genuine-hypotension safety cases, a per-bed five-second score, and target-device validation. The ECG–PPG artifact must not be substituted for live M6. |
| D, decision engine | Original M1–M4 research rule engine retained; new schema-shaped fail-closed bridge validates bed/window/target/score provenance and preserves monitor alarms. | The lead must supply the live-system repository, M5 package, authenticated timestamps and sequence, then train/calibrate and evaluate the six-model policy on independently labelled full-ward replays. Current D has illustrative thresholds and no validated NORMAL/TAMPERING/BOTH inference. |

The source-cache channel order is documented in the user's
[VTaC cache policy](https://drive.google.com/file/d/1HF8I_Rutz8zswUrcRdHKKZ5IHYGabk-m/view).
This is provenance for the cache construction, not independent verification
of every decoded waveform or proof that live channel order is the same.

## Verification in this repository

`python -m sentinelward_ml.verify` checks SHA-256 for all 31 packaged model and
component files without loading pickle/joblib objects. `tests/test_windows.py`
checks 125 Hz chunk assembly, five-second hopping, missing values, gaps,
duplicate sequence numbers, device changes, reset and alarm retention.
`examples/live_dry_run.py` exercises one synthetic bed from vitals to verdict
without representing clinical performance.
`tests/test_live_contract.py` checks missing-score behavior, alarm preservation,
positive-class and bed/window alignment, invalid scores, unsupported M5/M6
per-bed claims, and stale/off-grid windows. These tests verify code invariants,
not model performance or patient safety. The original offline model tests need
the scientific packages in `requirements-inference.txt` and trusted artifacts.

The next critical end-to-end acceptance test is a replay of synchronized
authenticated live-format inputs across several beds, including gaps, clock
skew, duplicate packets, sensor changes, non-VT emergencies, and independent
attack scenarios. Freeze thresholds before this test and report confusion
counts by verdict and subgroup. None of that evidence is present yet.
