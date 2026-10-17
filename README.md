# SentinelWard ML research handoff

The repository contains M1–M4 notebooks, saved artifacts, and offline inference adapters. The [complete updated research handoff](SentinelWard_M1-M4_M6_D_M5-review_20261017.zip) also contains the M6 drift monitor, D decision engine, checked wrappers, tests, and M5 external-source review. Download and extract that ZIP for the latest complete source tree; the M6 and D files are bundled there rather than expanded in this GitHub tree. Kartik's M5 source and model remain in his [separate repository](https://github.com/kartikDevS/IBM_Datathon).

- **M1:** whole-record, 12-lead ECG quality classification (Challenge 2011).
- **M2:** true versus false ventricular-tachycardia alarms (VTaC); VT only.
- **M3:** synthetic attack-window classifier on ECG/PPG data.
- **M4:** replay-similarity research prototype.
- **M5:** external network witness by Kartik, pinned and assessed in [the M5 handoff](results/M5_EXTERNAL_REVIEW.md); synthetic baseline only.
- **M6:** advisory batch waveform drift monitor; requires at least 48 native 250 Hz windows.
- **D:** deterministic research decision engine; current package consumes M1–M4 scores, not the locked six-model live verdict contract.

**Status:** These are research components, not a clinical or security-certified system. M5 is available in Kartik's separate repository, but its saved model was trained and tested on easily separable synthetic traffic. The live-system repository is still unavailable. M6's 0/4 clean alerts and 4/4 alerts per synthetic change involve only four batches per scenario. D's 46/46 figure measures synthetic rule checks, not clinical accuracy. The components have not been validated together on a representative live ward. Read the [executed integration checks and live gate](results/INTEGRATION_VALIDATION_20261017.md), [model-by-model remaining work](results/REMAINING_WORK.md), [M5 review](results/M5_EXTERNAL_REVIEW.md), and [M6/D verification and integration gaps](results/M6_D_REVIEW.md) before connecting them.

For current tree installation and M1–M4 calls, see [INTEGRATION.md](INTEGRATION.md). The complete ZIP contains the updated integration guide, a conservative live-contract bridge, and all checked components. Its M6 wrapper verifies the artifact hash before loading. Do not suppress or delay a monitor alarm based on any model score.

## Reproduction

The [notebooks](notebooks/) document training and audits. The [results](results/) folder contains model cards and benchmark summaries. Original datasets, derived waveforms, and event-level predictions are excluded from Git. Model artifacts in [models](models/) are for trusted-source loading only. Reported train/validation/test splits are record-disjoint; patient-disjointness is not established by record IDs alone.
