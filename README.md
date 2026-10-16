# SentinelWard ML baselines

Reproducible research notebooks for two SentinelWard components:

- **M1:** whole-record, 12-lead ECG quality classification on Challenge 2011 Set A.
- **M2:** ventricular-tachycardia alarm adjudication on the VTaC benchmark using a 10-second ECG/PPG window.

These are benchmark baselines, not a clinical device. M3, M4, and fusion component D are not implemented in this repository. M1 has not yet been adapted to the intended single-lead/PPG deployment setting. M2 handles VT alarms only, not other alarm types.

## Notebooks

1. [`notebooks/01_data_inventory_and_split_audit.ipynb`](notebooks/01_data_inventory_and_split_audit.ipynb) audits sources and builds/evaluates the M1 baseline.
2. [`notebooks/02_m2_vt_training.ipynb`](notebooks/02_m2_vt_training.ipynb) restores audited VTaC inputs, trains five fixed seeds, freezes each model and validation-selected threshold, then evaluates the official test split once.

Use Google Colab with Drive mounted. The notebooks refer to the author's Drive folder layout and require the original datasets and audited intermediate files. Change those paths when reproducing elsewhere. Large datasets, derived waveforms, checkpoints, and per-event predictions are intentionally excluded from Git. Saved evidence remains in the author's Drive audit folder; see [`results/benchmark_results.md`](results/benchmark_results.md) for the reported aggregates. The notebooks have outputs cleared to keep the repository small and avoid publishing event-level records.

The reported splits are record-disjoint. Record IDs alone do not establish that the same person never appears in separate records. M2 thresholds were chosen on validation data for at least 90% VT recall there; the test set was used for evaluation only. No threshold or model should be selected using the test scores.

## Reproduction notes

- Run each notebook from top to bottom; the M2 notebook depends on audit outputs from notebook 01.
- The M2 training cells expect a GPU runtime. Training used a Tesla T4 and PyTorch 2.11.0+cu130; preprocessing used NumPy 2.1.3 and SciPy 1.16.3.
- The M2 notebook installs `wfdb==4.3.1` before loading test waveforms. Archive verification and checksum assertions are embedded in the audit workflow.
- Do not run the held-out test cell repeatedly to make development decisions. For changes, use a new development protocol and report the previous test exposure.

