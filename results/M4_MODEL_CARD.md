# M4 model card — version 3 research prototype

The packaged `models/sentinelward_model4_v3.pkl` is a RandomForest research detector for replayed windows. It uses two aligned 10-second windows, six correlation-style features at 0.4 s and 0.8 s offsets across two channels and jointly, and threshold **0.9338677094352905**. Sampling rate is 250 Hz with 2,500 samples per window. Channel order has not been independently verified.

Training used 36 record groups (288 examples), development used 12 groups (96), and an internal test used 12 groups (96), grouped by record ID. Internal test counts were TN 23, FP 1, FN 6, TP 66: replay recall 0.9167, genuine specificity 0.9583, AUROC 0.9954. One off-grid noisy variant was flagged in only 7 of 12 cases. The examples are correlated synthetic variants from a very small test sample.

This detector measures signal similarity. It cannot establish unauthorized replay and cannot replace authenticated data freshness, timestamps, or trusted acquisition. Patient identity across records is unknown. New devices, channel mappings, natural artifacts, adversaries, and runtime robustness need independent validation. Earlier notebook versions were brittle to shifted replay; version 3 is a saved prototype, not a validated security control.
