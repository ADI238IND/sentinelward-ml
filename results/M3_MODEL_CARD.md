# M3 model card — research candidate

The preferred saved candidate is a supervised 22-feature HistGradientBoosting classifier for ECG/PPG inconsistency and synthetic attack detection. Its frozen threshold is **0.33261557242722967**; artifact: `models/m3_supervised_22.joblib`.

Of 627 CinC 2015 records with ECG and PPG headers, 594 passed basic pre-alarm finite/nonconstant checks. The workflow used record-disjoint training, validation, and retrospective test partitions of 436, 91, and 100 records. Patient identities are unavailable, so patient-disjointness is unproved. Synthetic attack examples were generated within each split.

Validation attack average precision was 0.9793, attack recall 0.9125, normal specificity 0.9001, and fault flag rate 0.1286. The 22-feature model was selected after comparison with an IsolationForest baseline and a 33-feature supervised variant.

The 100-record test partition was **already exposed** during earlier baseline work; this is not a fresh independent test. With model and threshold locked, 6,154 synthetic-attack and 5,000 normal windows gave TN 4,527, FP 473, FN 548, TP 5,606; attack recall 0.9110, normal specificity 0.9054, average precision 0.9789, AUROC 0.9681. Fault flag rate was 0.1243 and genuine physiology-event flag rate was 0.2708.

The results depend on a synthetic attack generator and a small selected dataset. Patient overlap, independent real-attack generalization, calibration, and clinical robustness remain unverified. This model is not deployment-ready.
