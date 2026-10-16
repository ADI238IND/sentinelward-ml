# Benchmark results (16 October 2026)

## M1: whole-record ECG quality

Challenge 2011 Set A: 1,000 recordings, 998 labelled (773 acceptable, 225 unacceptable); two unlabelled recordings excluded. Frozen grouped split: 698 train, 150 validation, 150 test. A 35-feature random-forest baseline was fit with five seeds. Held-out test mean across seeds: unacceptable recall **0.8353**, acceptable specificity **0.9328**, AUROC **0.9558**, average precision **0.8670**. These are whole-record quality scores and do not establish lead-level or patient-level generalization.

## M2: VTaC VT alarm adjudication

Official benchmark split: 4,060 train events (1,163 true VT), 495 validation (141 true VT), 482 test (137 true VT). Model: compact FCN, 51,553 parameters, using 10 seconds of ECG and PPG plus validity masks. Each of five fixed seeds used validation average precision for checkpoint selection, then a validation-selected threshold targeting at least 90% VT recall with maximum specificity. The five models and thresholds were frozen before scoring the test set.

| Test metric | Mean | Sample SD across five seeds |
| --- | ---: | ---: |
| True-VT recall | 0.9109 | 0.0289 |
| False-alarm specificity | 0.7594 | 0.0440 |
| True-VT precision | 0.6030 | 0.0347 |
| True-VT F1 | 0.7246 | 0.0200 |
| AUROC | 0.9031 | 0.0062 |
| Average precision | 0.7806 | 0.0135 |

Per-seed test confusion counts (TN, FP, FN, TP):

| Seed | TN | FP | FN | TP | VT recall | False-alarm specificity |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 20261015 | 267 | 78 | 12 | 125 | 0.9124 | 0.7739 |
| 20261016 | 269 | 76 | 17 | 120 | 0.8759 | 0.7797 |
| 20261017 | 275 | 70 | 15 | 122 | 0.8905 | 0.7971 |
| 20261018 | 236 | 109 | 7 | 130 | 0.9489 | 0.6841 |
| 20261019 | 263 | 82 | 10 | 127 | 0.9270 | 0.7623 |

Two seeds fell below 90% recall on the untouched test set despite meeting the validation target. The mean does not mean that every fit satisfies the target. The sample SD describes training variation, not a patient-level confidence interval. The PPG-unavailable test subgroup contained only 37 events (17 true VT), so its results are exploratory. The data are record-disjoint; patient identity across records has not been established.

Audit folder: `/content/drive/MyDrive/SentinelWard-work/data-audit/20261015T132438_754996Z/`. M2 test outputs: `m2_training/m2_five_seed_20261016T014108_258700Z/frozen_test_evaluation/` within that folder. Model checkpoints are included in `models/`; predictions remain in Drive.

## M3: ECG/PPG consistency and synthetic attack detection

The preferred 22-feature supervised HistGradientBoosting model obtained attack average precision **0.9793**, attack recall **0.9125**, normal specificity **0.9001**, and fault flag rate **0.1286** on validation. On a **previously exposed** retrospective 100-record test partition: 6,154 synthetic-attack and 5,000 normal windows, TN 4,527, FP 473, FN 548, TP 5,606; attack recall **0.9110**, normal specificity **0.9054**, average precision **0.9789**, AUROC **0.9681**. See [M3 model card](M3_MODEL_CARD.md).

## M4: replayed-window detection

The packaged version 3 RandomForest gave TN 23, FP 1, FN 6, TP 66 on a 12-record, 96-example internal synthetic test split: replay recall **0.9167**, genuine specificity **0.9583**, AUROC **0.9954**. One off-grid noisy replay variant was flagged in only 7 of 12 cases. See [M4 model card](M4_MODEL_CARD.md).

