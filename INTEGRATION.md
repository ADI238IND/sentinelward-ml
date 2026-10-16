# Integration handoff (research use)

The four saved models can now be loaded with one Python class. This is an
**offline research interface**, not a patient-facing alarm service. Every
artifact is SHA-256 checked against `models/manifest.json` before it is
deserialized. Never load model files supplied by an untrusted caller.

## Install and call

Use Python 3.12 or 3.13 in a clean environment:

```bash
python -m pip install -r requirements-inference.txt
python -m pip install -e .
```

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
3. A decision/fusion specification (`D`): when to abstain, how to combine
   model outputs, routing, audit logs, and the required clinical/security
   validation. `D` is **not yet implemented or trained**. There are **zero of
   the planned four model slots left**, but the end-to-end system is unfinished.
4. A representative end-to-end replay on held-out source files in the leader's
   environment. The repository smoke tests use synthetic arrays and validate
   execution and input contracts, not claimed field performance.

See `results/benchmark_results.md` and the model cards for measured offline
performance and its limitations. The original notebooks contain training and
test provenance.


## Current integration status (16 October 2026)

The [complete updated handoff](SentinelWard_M1-M4_M6_D_integration_handoff_20261016.zip) includes the M6 batch monitor, the D research engine, a fail-closed live-contract bridge, and safety tests. Read the [model-by-model readiness checklist](results/REMAINING_WORK.md). M5 and the lead's live-system repository have not been supplied, so a validated six-model ward verdict is not available.

`build_research_verdict` checks bed/window alignment and score meanings against the locked v1.1 message shape. Its timestamps are Unix epoch milliseconds. Missing scores remain `null`; a monitor alarm still produces `EMERGENCY`, while the absence of an alarm produces `UNSURE`, never `NORMAL`. M5 and M6 per-bed scores are rejected. The bridge is for a dry run only and does not publish to the live verdict topic or replace a trained, calibrated decision layer.
