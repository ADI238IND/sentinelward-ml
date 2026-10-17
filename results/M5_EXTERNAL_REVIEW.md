# M5 external source and integration review — 17 October 2026

Source: [kartikDevS/IBM_Datathon](https://github.com/kartikDevS/IBM_Datathon),
commit [`a6291f0eda6f8ca1874620c55aa6a5e51eea19c2`](https://github.com/kartikDevS/IBM_Datathon/commit/a6291f0eda6f8ca1874620c55aa6a5e51eea19c2).
Saved `m5_network_witness/artifacts/m5_model_baseline.joblib` SHA-256:
`200d8c8ae43fb11071d53072193c24ce0fe833ea6e943d9a5e5ee872d669e41f`.
The model remains in Kartik's repository; this handoff does not copy or deserialize
his artifact. No license file was found in that checkout, so redistribution
permission should be resolved before bundling his source or binary here.

Kartik's package provides 11 behavioral features from rolling MQTT arrivals,
a scikit-learn random forest, and an asynchronous `M5` event with `device_id`,
`observed_at` (Unix seconds), status, and `network_suspicion_score`. Its
metadata records 133 true negatives and 197 true positives, with zero errors
on a 330-row held-out **synthetic** set. This is a software baseline check,
not measured accuracy on hospital or independent network data. The synthetic
generator assigns normal rows to devices bed1–bed7 and attacks to bed8–bed10,
and normal versus attack feature distributions are widely separated. Group
splitting by device does not make this a realistic target-domain evaluation.

The locked SentinelWard vitals contract emits one chunk per second per bed;
M5's synthetic normal traffic is centered at two messages per second. That
rate difference can itself look anomalous. The source event also lacks a
vitals `window_start`, and an arbitrary payload `device_id` cannot establish
an authenticated bed identity. `sentinelward_ml.m5_external.validate_m5_event`
therefore checks event shape, freshness, score range, status, and equality to
the **transport-authenticated** device ID, but leaves M5 outside the
per-window six-score verdict. It never treats a network score as a clinical
diagnosis or an automatic containment command.

Before live integration, the lead and Kartik need to supply an authenticated
device-to-bed map, a timing/correlation policy, a measured baseline at actual
message cadence, labelled normal/flood/replay/jitter traffic from unseen
sessions or devices, and frozen confusion counts including false alarms.
Safety testing must retain original monitor alarms under all M5 outputs.
