# Integration handoff (research use)

**Current readiness:** See [the model-by-model checklist](results/REMAINING_WORK.md).
M5 is available as a separate synthetic research baseline; the live-system
repository is not yet available. No six-model clinical
or security verdict has been validated.

The four saved models can now be loaded with one Python class. This is an
**offline research interface**, not a patient-facing alarm service. Every
artifact is SHA-256 checked against `models/manifest.json` before it is
deserialized. Never load model files supplied by an untrusted caller.
Use the extracted [complete handoff ZIP](SentinelWard_M1-M4_M6_D_M5-review_20261017.zip)
as the working directory for the commands below. The browsable GitHub tree
omits the M6 and D component files; the full 31-file integrity check and
M6 wrapper require the extracted package.

## Install and call

Use Python 3.12 or 3.13 in a clean environment:

```bash
python -m pip install -r requirements-inference.txt
python -m pip install -e .
```

Before loading any pickled model artifacts from this trusted checkout, run
`python -m sentinelward_ml.verify`. It checks all 31 saved model and component
files against the manifests without deserializing them. This establishes file
integrity only, not model accuracy or source authenticity.

Or run from the repository root without an editable install:

```python
import numpy as np
from sentinelward_ml import SentinelWardModels

models = SentinelWardModels()
quality = models.predict_m1(ecg_12_leads_mv, sample_rate_hz=500)
vt_alarm = models.predict_m2(ecg_ppg_250hz, valid_mask_250hz, sample_rate_hz=250)
attack = models.predict_m3(preprocessed_ecg_ppg_125hz, sample_rate_hz=125)
replay = models.predict_m4(reference_250hz, candidate_250hz,
                           reference_mask, candidate_mask, sample_rate_hz=250)
```

Inputs must be NumPy-like arrays with exactly the following shapes. The
methods reject wrong shape, sample rate, nonfinite samples, and invalid masks.

| Method | Input contract | Meaning of positive score |
|---|---|---|
| `predict_m1` | 10 seconds, `(5000,12)` **mV**, original 2011 lead order `I, II, III, aVR, aVF, aVL, V1–V6` at 500 Hz | Whole recording unacceptable quality. Returns 5 seed scores and the predeclared 0.5 threshold. Not a per-lead quality label. |
| `predict_m2` | Pre-alarm 10 seconds, `(2,2500)` physical ECG/PPG, 250 Hz, ECG then PPG, plus boolean mask of same shape | True VT alarm. Internal adapter reproduces training normalization, antialias filtering, downsampling, and validity mask. Returns all 5 fixed seeds and validation-chosen thresholds; seed 20261015 is the primary reporting seed. No test-time seed selection. |
| `predict_m3` | `(2,1250)` **already preprocessed** 125 Hz CinC-2015 ECG/PPG, ECG then PPG | Synthetic attack window. Returns the supervised 22-feature model's score and validation threshold. A raw-waveform adapter is deliberately absent until the pinned CinC-2015 preprocessing is packaged and verified. |
| `predict_m4` | Two `(2,2500)` 250 Hz ECG/PPG windows and boolean masks, ECG then PPG; at least 90% valid in each channel/window | Similarity to the synthetic replay patterns used for training. Offline comparison, not a standalone live-stream detector. Bundle states `channel_order_verified=false`; source channel mapping must be checked before real integration. |

The numbers named `probability` are model scores and **are not calibrated
clinical probabilities**. M1 and M2 are trained on different sources and
answer different questions. M3 and M4 address synthetic security attacks;
neither replaces a clinical alarm classifier. Do not merge outputs into one
verdict or suppress an alarm without a separately specified and validated
decision policy.

## What the project lead needs to supply

1. A trusted waveform reader that produces physical values, original units,
   exact channel order, sampling rate, and sample-validity masks. Verify the
   M4 ECG/PPG channel mapping against the source cache before using it.
2. The pinned CinC-2015 loader's transformation for M3; `predict_m3` takes its
   125 Hz output, not raw 250 Hz data. Its feature order follows
   [IoMT_SecAlarmBench](https://github.com/EmmanuelUgwuabonyi/IoMT_SecAlarmBench)
   commit `8b09a300c81348d16030c624900d27ee7d05e01f` (MIT).
3. The supplied D research engine is available at
   `components/SentinelWard_D/decision_engine.py`. It takes M1–M4 research
   scores with matching window IDs; its thresholds for M1–M3 are illustrative.
   It is **not** the locked six-model live verdict interface or a calibrated
   clinical fusion layer. See `results/M6_D_REVIEW.md` before connecting it.
4. A representative end-to-end replay on held-out source files in the leader's
   environment. The repository smoke tests use synthetic arrays and validate
   execution and input contracts, not claimed field performance.

See `results/benchmark_results.md` and the model cards for measured offline
performance and its limitations. The original notebooks contain training and
test provenance.

## M6 offline drift monitor

```python
from sentinelward_ml import SentinelWardDriftMonitor

monitor = SentinelWardDriftMonitor()  # verifies saved artifact SHA-256
report = monitor.monitor(native_250hz_batch, valid_boolean_masks)
```

Both inputs have shape `(N, 2, 2500)`, with at least
`monitor.minimum_batch_size` (currently 48) windows for an alert decision.
Fewer windows return `INSUFFICIENT_DATA`. The result is advisory, not an
M6 score per live bed or a clinical action. The original runtime and research
reports are in `components/SentinelWard_M6/`. Do not infer channel mapping:
the supplied feature catalog marks it unverified.

## Conservative live-contract bridge

`VitalsWindowAssembler` accepts the locked v1 vitals message shape: one 125 Hz
ECG/PPG chunk per bed and device each second, with epoch-millisecond timestamp
and increasing sequence number. It emits a 10-second window every five seconds
only after ten contiguous messages. It retains `null` samples and all monitor
alarms. A gap, new device, or demo reset clears pending samples; duplicate or
out-of-order messages are rejected. A recording that simply stops produces no
window; silence by itself is not classified as an attack. Upstream code still
must authenticate the sender and synchronize clocks.

```python
from sentinelward_ml import VitalsWindowAssembler

assembler = VitalsWindowAssembler()
window = assembler.ingest(vitals_message)  # None until 10 contiguous seconds
# On ward/demo/control reset:
assembler.reset()
```

The window builder does not convert 125 Hz into the incompatible M1/M2/M4/M6
source domains. Do not resample and assume that their measured accuracy carries
over. M3 likewise needs its pinned full-record preprocessing reproduced and
validated before this raw live feed can be used.

For a dependency-free synthetic wiring demonstration, run
`python -m examples.live_dry_run` from the repository root. It prints two
schema-shaped verdicts: a retained monitor alarm yields `EMERGENCY`, followed
by `UNSURE` after that alarm leaves the overlapping window. All six scores
remain `null`; this demo is not a test of model accuracy.

Kartik's M5 event can be checked with `validate_m5_event` from
`sentinelward_ml`, using a device identity authenticated by the MQTT transport:

```python
from sentinelward_ml import validate_m5_event

advisory = validate_m5_event(
    m5_event,
    authenticated_device_id=authenticated_device_id,
    now_ms=received_at_ms,
)
```

The result is an asynchronous advisory event, not an M5 score bound to a
particular vitals window. Kartik's event has no `window_start` and its model
was trained on synthetic 2 Hz normal traffic, while the locked vitals stream
is 1 Hz. It remains separate from the six-score verdict until the lead defines
and validates device-to-bed mapping, event timing, and target-domain behavior.
See [M5 review](results/M5_EXTERNAL_REVIEW.md) for the pinned source commit.

`sentinelward_ml.live_contract.build_research_verdict` produces the locked
verdict-shaped fields for an integration dry run. It accepts only score
envelopes bearing the exact bed, 10-second epoch-millisecond window, model version and
positive-class target. M5 and M6 remain `null`; a claimed per-bed M6 score is
rejected because the saved M6 is a batch monitor. This bridge never outputs
`NORMAL`: without an independent monitor alarm it returns `UNSURE`, and with
one it returns `EMERGENCY` at high priority. It does not publish to the live
verdict topic, suppress an alarm, or represent a trained D replacement.

```python
from sentinelward_ml import build_research_verdict

dry_run = build_research_verdict(
    bed_id="B01",
    window_start=1792112400000,
    ts=1792112410000,
    monitor_alarm={"code": "VTACH", "priority": "high"},  # or None
    score_envelopes={
        "M2": {
            "bed_id": "B01",
            "window_start": 1792112400000,
            "target": "true_vt_alarm",
            "score": 0.75,
            "model_version": "research-v1",
        },
    },
)
```

The example score is illustrative, not a claim about a real patient or a
calibrated probability. For M1/M2/M3/M4, use the exact `target` returned by the
checked offline adapter; never relabel M2 as an all-emergency detector or M3
as a proven body-mismatch detector. Timestamp and device authenticity must be
established upstream by the leader's live system; this bridge only checks
format and consistency.
