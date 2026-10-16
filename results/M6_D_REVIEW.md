# M6 and D integration review — 16 October 2026

## Verified package contents

The user-supplied Drive archives were inspected, extracted under `components/`,
and enumerated in `components/manifest.json`. M6's saved joblib file hashes to
`1594c6ef8a4f3f3b4c22f4785e90f01287757d5c26897b13903b7e77a0dd32b8`.
The M6 wrapper verifies this hash before loading. D's example output reproduces
exactly. Nine repository tests pass, including M6 batch invocation and D's
emergency-preservation checks for every other-flag combination.

## What the reported results mean

| Component | Supplied evidence | Appropriate interpretation |
|---|---|---|
| M6 | Clean validation: 0 alerts in 4 non-overlapping batches. Each of six synthetic modifications: 4 alerts in 4 batches. | A small same-source stress test. This is **not** a clinical accuracy estimate or a robust field false-alert rate. M6 is unsupervised and has no diagnostic accuracy metric. |
| D | Supplied summary: 46/46 deterministic synthetic rule checks pass. Local tests reproduce the example and check emergency preservation, missing output, and window mismatch. | Code behavior passes rule tests. No independently labelled integrated ward test set, per-verdict F1, emergency miss-rate estimate, or calibrated confidence has been supplied. |

## Blocking mismatches with the locked live interface

1. The locked team contract requires six model scores (M1–M6) every five seconds
   and a verdict message with `bed_id`, `window_start`, `verdict`, `priority`,
   `confidence`, `trust`, and reasons. D currently accepts only M1–M4 and emits
   `medical_status`, `signal_status`, and `security_status`; no six-score verdict
   adapter or calibrated logistic layer is present.
2. D's M1–M3 thresholds are explicitly illustrative. Its M2 label suggests any
   emergency, but the saved M2 model is **VT-only**. D's M3 label says physical
   ECG–PPG inconsistency, while the saved M3 classifier is trained for synthetic
   attack windows; these meanings have not been demonstrated equivalent.
3. M6 is a **batch** drift monitor needing at least 48 native 250 Hz, 10-second
   windows; it cannot provide a meaningful per-bed M6 score every five seconds
   without a separately designed temporal aggregation and calibration protocol.
   Its channel-to-physiology mapping is marked unverified in the supplied files.
4. The live vitals contract supplies 125 Hz one-second ECG/PPG chunks. M1 expects
   500 Hz 12-lead ECG; M2/M4/M6 expect 250 Hz inputs; M3 expects its specific
   already-preprocessed 125 Hz input. Resampling alone does not establish model
   validity. M4's own channel mapping is also unverified.
5. M5 network evidence belongs to the cybersecurity workstream and is absent
   from this repository. Device identity, trusted timestamps/sequence, actual
   message authentication, and a held-out whole-ward replay are not present.

The leader can integrate these **offline research APIs** now, preserving every
monitor alarm and keeping D's advisory output separate from the live verdict
topic. A patient-facing or security-enforcing integration still requires the
above contract work and independent validation. Do not infer a `NORMAL` patient
state or suppress a monitor alarm from these scores.
