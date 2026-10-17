# Integration validation — 17 October 2026

**Package status: verified research handoff. Live deployment status: blocked.**
The original monitor alarm remains independent of every model and must never be
suppressed by a security or quality score.

## Executed checks

- The public package ZIP matched SHA-256
  `b6be8494eb5891013a4f5a3ecbfe493f3ed793a0e58b4876a3c84bf6f68fb678`
  before extraction. Its internal CRC passed.
- In a fresh Colab Python 3 runtime, all **28** packaged tests passed in 7.239 s.
  This included model-load and synthetic-array smoke tests for M1–M4, M6 batch
  execution, D research rules, M5 event format, live-contract safety, and the
  integrity check of **31** saved files. Scientific package versions were NumPy
  2.1.3, SciPy 1.16.3, pandas 2.2.3, scikit-learn 1.6.1, PyTorch 2.11.0+cpu,
  joblib 1.6.0, and cloudpickle 3.1.2.
- After that package check, the vitals window builder was fixed to snapshot
  validated input samples. The expanded local standard-library suite passed
  **21** tests, including input-buffer mutation and two interleaved beds.
- The rebuilt, public **65-file** archive at commit
  `fcc1704b6292b6e84e72e92023f042a0384a4f90` matched SHA-256
  `035fa79499727a1b1996efecfc6a1dc82bc81e9e21865994a86687bbcf1c34cb`
  and passed ZIP CRC. Its complete suite then passed **30/30 tests** in an
  isolated Python process (3.991 s test time, exit code 0). This final run
  supersedes the earlier 28-test result. The archive contains the report as it
  stood before this final test; this public page records the later result.

These checks prove that the packaged code runs on the tested environment and
that the specified interface invariants hold. They do **not** remeasure
held-out accuracy, establish model calibration, validate real-world patient or
network traffic, or prove clinical safety.

## Model disposition

| Component | Handoff disposition | Live gate still open |
|---|---|---|
| M1 | Saved and executable offline | Needs 500 Hz 12-lead input or separately validated 125 Hz live-domain model. Frozen test unacceptable-record recall 0.8353 mean across seeds. |
| M2 | Saved and executable offline for **VT only** | Needs native 250 Hz pre-alarm ECG/PPG and target-ward validation. Two test seeds missed the 0.90 recall goal. |
| M3 | Saved and executable on already-preprocessed 125 Hz CinC-2015 windows | Pin and reproduce raw-to-model preprocessing; independently label real body/sensor mismatch. |
| M4 | Saved and executable for offline pair comparison | Verify channel mapping, trusted-reference creation/revocation, and off-grid/noisy replay behavior. |
| M5 | External pinned synthetic baseline; event-format adapter checked | Need representative 1 Hz target traffic, authenticated device-to-bed mapping, and window alignment. No M5 per-window score is emitted. |
| M6 | Saved batch drift artifact and wrapper checked | 48-window batch metric needs source-channel verification and target-domain evaluation. No validated per-bed five-second score exists. |
| D | Original research rules and conservative live-contract bridge checked | Needs six-model policy, calibrated thresholds, and independently labelled full-ward replay. It must not issue a clinical NORMAL claim from current evidence. |

## Required acceptance replay before live verdict publishing

The lead's live-system repository and a representative, independently labelled
ward replay are not supplied. Once available, freeze code, artifact hashes,
thresholds, model versions and score meanings **before** running it. Replay
the actual 125 Hz, one-second message stream on all twelve beds; include
missing and late chunks, duplicates, clock skew, bed/device reassignment,
sensor disconnection, changing channel units, each non-VT monitor alarm, VT
alarms, independent network anomalies, replay attacks, and benign periods.
Verify 10-second windows every five seconds, authenticated routing, latency,
alarm preservation, fail-closed behavior, and no cross-bed contamination.
Report confusion counts, recall, specificity, false alarms and latency by
scenario, bed, device, missing-signal subgroup and patient-independent split.
Compare against the original monitor, with explicit clinical sign-off before
any model output can affect care or suppress an alarm.

Until that acceptance evidence exists, the bridge remains a **research dry
run** and should not be wired to the production verdict topic.


## Supplemental twelve-bed protocol replay

The published [twelve-bed synthetic replay](../tests/test_twelve_bed_replay.py) checks 24 overlapping 10-second windows at five-second hops across B01–B12, all five monitor alarm codes, missing PPG, bed isolation, and a one-bed gap that does not reset the other eleven beds. The [automated protocol run #3](https://github.com/ADI238IND/sentinelward-ml/actions/runs/39014438315) passed all 21 dependency-free checks on the published source. Earlier workflow runs failed while the GitHub web editor had saved empty workflow/example files; those files were corrected before run #3.

This supplemental test is outside the unchanged 65-file handoff ZIP. It checks schema and routing behavior, not held-out model accuracy, clinical safety, or the independently labelled ward acceptance replay. The live deployment gate remains blocked until the lead supplies the live-system repository, authenticated stream, and representative labelled replay.


## Lead Phase 0 contract cross-check

The public [lead repository](https://github.com/adityavijay3659-sketch/SentinelWard) was checked on 17 October 2026. Its README identifies the checkout as Phase 0 design material only; it does not contain the running simulator, broker, backend, or labelled ward replay. The [canonical contracts](https://github.com/adityavijay3659-sketch/SentinelWard/blob/main/docs/contracts.md) and [handoff](https://github.com/adityavijay3659-sketch/SentinelWard/blob/main/docs/handoffs.md) require an aligned per-bed M6 v1 score every five seconds when inputs permit. The saved M6 artifact instead produces an advisory result from a batch of at least 48 native 250 Hz windows. That is a material interface gap, not an output-field rename; do not publish its batch metric as a per-bed five-second score. The [lead fixtures](https://github.com/adityavijay3659-sketch/SentinelWard/blob/main/fixtures/contract-examples.json) are explicitly design examples with illustrative six-model scores, not observed validation data. The full live-system repository, source-authenticated 125 Hz stream, and independently labelled twelve-bed replay are still required for live acceptance.


## Critical M6 target mismatch found in Drive audit

The saved [M6 Drive package](https://drive.google.com/drive/folders/1ENM7EtxVjla6cBpo2BDn-95KQgq0A4pk) describes a research ECG–PPG distribution-shift detector trained from VTaC windows (`N,2,2500`, 250 Hz; at least 48 windows per decision). The lead’s [M6 design](https://github.com/adityavijay3659-sketch/SentinelWard/blob/main/docs/m6-design.md) instead asks whether an arterial blood-pressure sensor drifts, using ART waveform/pressure plus paired NIBP cuff values, a per-patient baseline, and a calibrated per-bed score every five seconds. The current package has no ART–NIBP inputs, no blood-pressure gap or Page-Hinkley evidence, and no held-out genuine-hypotension safety result. Its synthetic ECG–PPG shift alerts are **not evidence for the specified M6 task**. Keep this artifact as a separately named exploratory waveform monitor; do not deploy or report it as the blood-pressure M6 score. The shared data and work folders contain no identified VitalDB ART/NIBP training set or independently labelled ward replay. The required M6 must be built and evaluated against the lead’s specification before D can consume it.

This finding supersedes the M6 row above: the saved ECG–PPG artifact is not an implementation of the lead-specified arterial-pressure M6.
