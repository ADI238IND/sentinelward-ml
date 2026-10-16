# SentinelWard ML research models

Reproducible research notebooks and saved model artifacts for four SentinelWard components:

- **M1:** whole-record, 12-lead ECG quality classification on Challenge 2011 Set A.
- **M2:** ventricular-tachycardia alarm adjudication on the VTaC benchmark using a 10-second ECG/PPG window.
- **M3:** ECG/PPG consistency and synthetic attack detection on CinC 2015 data.
- **M4:** replayed-window detection research prototype.

These are research models, not a clinical device or a security-certified system. Fusion component D is not implemented. The four components have not been validated as an integrated pipeline. M1 has not yet been adapted to the intended single-lead/PPG deployment setting. M2 handles VT alarms only, not other alarm types.

## Notebooks

1. [`notebooks/01_data_inventory_and_split_audit.ipynb`](notebooks/01_data_inventory_and_split_audit.ipynb) audits sources and builds/evaluates the M1 baseline.
2. [`notebooks/02_m2_vt_training.ipynb`](notebooks/02_m2_vt_training.ipynb) restores audited VTaC inputs, trains five fixed seeds, freezes each model and validation-selected threshold, then evaluates the official test split once.
3. [`notebooks/03_m3_ecg_ppg_consistency.ipynb`](notebooks/03_m3_ecg_ppg_consistency.ipynb) develops and evaluates the M3 detector.
4. [`notebooks/04_m4_replay_detection.ipynb`](notebooks/04_m4_replay_detection.ipynb) records the M4 development through the packaged version 3 prototype.

Use Google Colab with Drive mounted. The notebooks refer to the author's Drive folder layout and require the original datasets and audited intermediate files. Change those paths when reproducing elsewhere. Original datasets, derived waveforms, and per-event predictions are excluded from Git; model artifacts are in [`models/`](models/). See [`results/benchmark_results.md`](results/benchmark_results.md), the [M3 model card](results/M3_MODEL_CARD.md), the [M4 model card](results/M4_MODEL_CARD.md), and the [model hash manifest](models/manifest.json). Notebook outputs were cleared to avoid publishing event-level records. Load pickle/joblib files only from trusted sources.

The reported splits are record-disjoint. Record IDs alone do not establish that the same person never appears in separate records. M2 thresholds were chosen on validation data for at least 90% VT recall there; the test set was used for evaluation only. No threshold or model should be selected using the test scores.

## Reproduction notes

- Run each notebook from top to bottom; the M2 notebook depends on audit outputs from notebook 01.
- The M2 training cells expect a GPU runtime. Training used a Tesla T4 and PyTorch 2.11.0+cu130; preprocessing used NumPy 2.1.3 and SciPy 1.16.3.
- The M2 notebook installs `wfdb==4.3.1` before loading test waveforms. Archive verification and checksum assertions are embedded in the audit workflow.
- Do not run the held-out test cell repeatedly to make development decisions. For changes, use a new development protocol and report the previous test exposure.

# Integration

The four saved research artifacts have callable, checksum-verified adapters.
See [INTEGRATION.md](INTEGRATION.md) for installation, waveform contracts,
example calls, and the remaining decision/fusion work.

