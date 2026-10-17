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
