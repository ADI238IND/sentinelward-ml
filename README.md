# SentinelWard ML research handoff

The [M6 blood-pressure research adapter and synthetic twelve-bed replay](results/M6_BP_RESEARCH.md) are now runnable locally. They generate ART/NIBP evidence while deliberately withholding a calibrated M6 score. The [replay source](examples/twelve_bed_bp_replay.py) and [synthetic result](results/twelve_bed_bp_replay_synthetic.json) do not replace a labelled live-ward replay or complete the lead-specified M6.


**Critical M6 correction:** The bundled M6 artifact monitors batch ECG–PPG distribution shift. It does **not** implement the arterial blood-pressure drift detector in the [lead’s M6 design](https://github.com/adityavijay3659-sketch/SentinelWard/blob/main/docs/m6-design.md): it has no ART/NIBP inputs or per-bed five-second score. Treat it as an exploratory waveform monitor, not a live M6 component or an input to the six-model verdict. See the [integration validation report](results/INTEGRATION_VALIDATION_20261017.md) for the model-by-model release gates.


The repository contains M1–M4 notebooks, saved artifacts, and offline inference adapters. The [complete updated research handoff](SentinelWard_M1-M4_M6_D_M5-review_20261017.zip) also contains an exploratory ECG–PPG batch-shift artifact (previously labelled M6), D decision engine, checked wrappers, tests, and M5 external-source review. Download and extract that ZIP for the latest complete source tree; the exploratory waveform artifact and D files are bundled there rather than expanded in this GitHub tree. Kartik's M5 source and model remain in his [separate repository](https://github.com/kartikDevS/IBM_Datathon).

- **M1:** whole-record, 12-lead ECG quality classification (Challenge 2011).
- **M2:** true versus false ventricular-tachycardia alarms (VTaC); VT only.
- **M3:** synthetic attack-window classifier on ECG/PPG data.
- **M4:** replay-similarity research prototype.
- **M5:** external network witness by Kartik, pinned and assessed in [the M5 handoff](results/M5_EXTERNAL_REVIEW.md); synthetic baseline only.
- **M6:** the required ART/NIBP blood-pressure drift model is not yet implemented. The bundled ECG–PPG batch-shift artifact is exploratory only.
- **D:** deterministic research decision engine; current package consumes M1–M4 scores, not the locked six-model live verdict contract.

**Status:** These are research components, not a clinical or security-certified system. M5 is available in Kartik's separate repository, but its saved model was trained and tested on easily separable synthetic traffic. The live-system repository is still unavailable. The exploratory artifact's 0/4 clean alerts and 4/4 alerts per synthetic change involve only four batches per scenario. D's 46/46 figure measures synthetic rule checks, not clinical accuracy. The components have not been validated together on a representative live ward. Read the [executed integration checks and live gate](results/INTEGRATION_VALIDATION_20261017.md), [model-by-model remaining work](results/REMAINING_WORK.md), [M5 review](results/M5_EXTERNAL_REVIEW.md), and [M6/D verification and integration gaps](results/M6_D_REVIEW.md) before connecting them.

For current tree installation and M1–M4 calls, see [INTEGRATION.md](INTEGRATION.md). The complete ZIP contains the updated integration guide, a conservative live-contract bridge, and all checked components. The exploratory artifact wrapper verifies its hash before loading. Do not suppress or delay a monitor alarm based on any model score.

## Reproduction

The [notebooks](notebooks/) document training and audits. The [results](results/) folder contains model cards and benchmark summaries. Original datasets, derived waveforms, and event-level predictions are excluded from Git. Model artifacts in [models](models/) are for trusted-source loading only. Reported train/validation/test splits are record-disjoint; patient-disjointness is not established by record IDs alone.


The [twelve-bed synthetic protocol test](tests/test_twelve_bed_replay.py) and its [passing automated run](https://github.com/ADI238IND/sentinelward-ml/actions/runs/39014438315) check routing and fail-closed behavior. They do not replace the independently labelled live-ward acceptance replay described in the [integration validation report](results/INTEGRATION_VALIDATION_20261017.md).
