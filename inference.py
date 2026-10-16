"""Versioned, fail-closed inference contracts for the saved research models.

Inputs are physical samples from the indicated source and sampling rate. No
alarm verdict or clinical decision is inferred from these independent scores.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np


def _array(value, shape, name):
    array = np.asarray(value, dtype=np.float64)
    if array.shape != shape or not np.isfinite(array).all():
        raise ValueError(f"{name} must have shape {shape} and only finite values")
    return array


def _rate(actual, expected):
    if float(actual) != expected:
        raise ValueError(f"Expected {expected} Hz, received {actual} Hz")


def _channel_features(x, fs):
    from scipy.stats import skew, kurtosis

    delta = np.diff(x)
    spectrum = np.abs(np.fft.rfft(x - x.mean()))
    frequencies = np.fft.rfftfreq(x.size, 1.0 / fs)
    dominant = float(frequencies[int(np.argmax(spectrum))]) if spectrum.sum() > 0 else 0.0
    p = spectrum / (spectrum.sum() + 1e-12)
    return {
        "mean": float(x.mean()), "std": float(x.std()), "ptp": float(np.ptp(x)),
        "rms": float(np.sqrt(np.mean(x ** 2))),
        "madiff": float(np.mean(np.abs(delta))),
        "iqr": float(np.subtract(*np.percentile(x, [75, 25]))),
        "skew": float(skew(x)) if x.std() > 1e-9 else 0.0,
        "kurt": float(kurtosis(x)) if x.std() > 1e-9 else 0.0,
        "dom_freq": dominant,
        "spec_ent": float(-(p * np.log(p + 1e-12)).sum()),
    }


def _m3_features(window):
    """22 features equivalent to pinned IoMT_SecAlarmBench eval_harness.py.

    Source commit 8b09a300c81348d16030c624900d27ee7d05e01f (MIT).
    """
    features = {}
    for name, values in zip(("ECG", "PPG"), window):
        features.update({f"{name}_{key}": value for key, value in _channel_features(values, 125).items()})
    a, b = window
    if a.std() > 1e-9 and b.std() > 1e-9:
        features["xcorr_01"] = float(np.corrcoef(a, b)[0, 1])
        lag = int(.2 * 125)
        scores = [abs(float(np.corrcoef(a, np.roll(b, offset))[0, 1]))
                  for offset in range(-lag, lag + 1, max(1, lag // 3))]
        features["xcorr_lag_best"] = max((s if np.isfinite(s) else 0.0) for s in scores)
    else:
        features["xcorr_01"] = features["xcorr_lag_best"] = 0.0
    return features


def _m1_features(x):
    from scipy.signal import welch

    difference = np.diff(x, axis=0)
    constant = np.ptp(x, axis=0) == 0
    lead = {
        "std_mv": np.std(x, axis=0), "range_mv": np.ptp(x, axis=0),
        "iqr_mv": np.percentile(x, 75, axis=0) - np.percentile(x, 25, axis=0),
        "abs_mean_mv": np.abs(np.mean(x, axis=0)),
        "rms_mv": np.sqrt(np.mean(x ** 2, axis=0)),
        "median_abs_step_mv": np.median(np.abs(difference), axis=0),
        "p95_abs_step_mv": np.percentile(np.abs(difference), 95, axis=0),
        "unchanged_step_fraction": np.mean(difference == 0, axis=0),
    }
    frequencies, power = welch(x, fs=500, nperseg=1000, noverlap=500,
                               detrend="constant", axis=0)

    def band(low, high):
        return power[(frequencies >= low) & (frequencies < high)].sum(axis=0)

    def ratio(numerator, denominator):
        return np.divide(numerator, denominator, out=np.zeros_like(numerator),
                         where=denominator > 0)

    total = power.sum(axis=0)
    lead.update({
        "power_fraction_below_0p5hz": ratio(band(0, .5), total),
        "power_fraction_40_100hz": ratio(band(40, 100), total),
        "power_ratio_5_15_to_5_40hz": ratio(band(5, 15), band(5, 40)),
    })
    result = {"constant_leads": int(constant.sum()),
              "all_leads_constant": int(constant.all())}
    for name, values in lead.items():
        result.update({f"{name}_min": float(np.min(values)),
                       f"{name}_median": float(np.median(values)),
                       f"{name}_max": float(np.max(values))})
    return result


def _m2_preprocess(signal, valid):
    from scipy.ndimage import minimum_filter1d
    from scipy.signal import firwin, resample_poly

    count = valid.sum(axis=-1, keepdims=True)
    mean = np.where(valid, signal, 0).sum(axis=-1, keepdims=True) / np.maximum(count, 1)
    centered = np.where(valid, signal - mean, 0)
    variance = (centered ** 2).sum(axis=-1, keepdims=True) / np.maximum(count, 1)
    normalized = centered / np.maximum(np.sqrt(variance), 1e-6)
    taps = firwin(41, cutoff=.5, window=("kaiser", 5.0))
    down = resample_poly(normalized, up=1, down=2, axis=-1,
                         window=taps, padtype="constant")
    safe = minimum_filter1d(valid.astype(np.uint8), size=41, axis=-1,
                            mode="constant", cval=0).astype(bool)[..., ::2]
    prepared = np.concatenate([np.where(safe, down, 0), safe.astype(np.float64)], axis=0)
    return prepared.astype(np.float32)


def _m4_features(ref, candidate, rm, cm):
    """Exact phase-invariant descriptor from M4 notebook Cell 11.

    Reimplemented here because cloudpickled notebook functions are not portable
    across Python minor versions; the estimator and thresholds remain unchanged.
    """
    from numpy.lib.stride_tricks import sliding_window_view

    means = np.array([ref[ch, rm[ch]].mean() for ch in range(2)])[:, None]
    stds = np.array([max(ref[ch, rm[ch]].std(), 1e-4) for ch in range(2)])[:, None]
    a, b = (ref - means) / stds, (candidate - means) / stds

    def minimum_rmse(left, right):
        if len(left) == 0 or len(right) == 0:
            return np.nan
        left = np.ascontiguousarray(left, dtype=np.float64)
        right = np.ascontiguousarray(right, dtype=np.float64)
        aa = np.sum(left * left, axis=1)[:, None]
        bb = np.sum(right * right, axis=1)[None, :]
        distances = np.maximum((aa + bb - 2 * (left @ right.T)) / left.shape[1], 0)
        return float(np.sqrt(distances.min()))

    result = {}
    for length in (100, 200):
        name = f"{length / 250:.1f}s"
        reference_windows = sliding_window_view(a, length, axis=1)[:, ::25, ::5]
        candidate_windows = sliding_window_view(b, length, axis=1)[:, :, ::5]
        reference_valid = sliding_window_view(rm, length, axis=1)[:, ::25, ::5].all(axis=2)
        candidate_valid = sliding_window_view(cm, length, axis=1)[:, :, ::5].all(axis=2)
        for ch in (0, 1):
            result[f"ch{ch}_{name}"] = minimum_rmse(
                reference_windows[ch][reference_valid[ch]],
                candidate_windows[ch][candidate_valid[ch]])
        rkeep, ckeep = reference_valid.all(axis=0), candidate_valid.all(axis=0)
        joint_r = np.concatenate([reference_windows[0, rkeep],
                                  reference_windows[1, rkeep]], axis=1)
        joint_c = np.concatenate([candidate_windows[0, ckeep],
                                  candidate_windows[1, ckeep]], axis=1)
        result[f"joint_{name}"] = minimum_rmse(joint_r, joint_c)
    return result


class SentinelWardModels:
    """Loads only SHA-256 matched, locally packaged model artifacts.

    Deserialization uses pickle-based formats and must only be done with this
    trusted repository's verified files. Do not pass user-supplied model paths.
    """

    def __init__(self, root=None):
        self.root = Path(root or Path(__file__).resolve().parents[1]).resolve()
        self.manifest = json.loads((self.root / "models" / "manifest.json").read_text())
        self._loaded = {}

    def _verified_path(self, filename, expected):
        path = self.root / "models" / filename
        if hashlib.sha256(path.read_bytes()).hexdigest() != expected:
            raise ValueError(f"Model integrity check failed: {filename}")
        return path

    def _model(self, name):
        if name in self._loaded:
            return self._loaded[name]
        spec = self.manifest["models"][name]
        if name == "M2":
            import torch
            models = {}
            for filename, digest in spec["files"].items():
                checkpoint = torch.load(self._verified_path(filename, digest),
                                        map_location="cpu", weights_only=False)
                network = _CompactM2FCN()
                network.load_state_dict(checkpoint["model_state_dict"], strict=True)
                network.eval()
                threshold = checkpoint.get("threshold")
                if threshold is None:
                    threshold = checkpoint["validation_metrics"]["threshold"]
                models[int(filename.removeprefix("m2_seed").removesuffix(".pt"))] = (network, float(threshold))
            value = models
        else:
            import joblib
            path = self._verified_path(spec["file"], spec["sha256"])
            if name == "M4":
                import cloudpickle
                with path.open("rb") as handle:
                    value = cloudpickle.load(handle)
            else:
                value = joblib.load(path)
        self._loaded[name] = value
        return value

    def predict_m1(self, ecg_mv, *, sample_rate_hz=500):
        """Whole-record 12-lead quality: 1 means unacceptable."""
        import pandas as pd

        _rate(sample_rate_hz, 500)
        x = _array(ecg_mv, (5000, 12), "M1 ECG (mV)")
        bundle = self._model("M1")
        features = _m1_features(x)
        frame = pd.DataFrame([{key: features[key] for key in bundle["feature_columns"]}])
        probabilities = [float(model.predict_proba(frame)[0, 1]) for model in bundle["models"]]
        return {"target": "unacceptable_whole_record", "seed_probabilities": probabilities,
                "mean_probability": float(np.mean(probabilities)),
                "seed_decisions": [p >= bundle["threshold"] for p in probabilities],
                "threshold": float(bundle["threshold"]), "calibrated": False}

    def predict_m2(self, ecg_ppg, valid_mask, *, sample_rate_hz=250):
        """Pre-alarm 10-second window; rows ECG then PPG, with boolean validity."""
        import torch

        _rate(sample_rate_hz, 250)
        signal = _array(ecg_ppg, (2, 2500), "M2 ECG/PPG")
        mask = np.asarray(valid_mask)
        if mask.shape != (2, 2500) or mask.dtype != np.bool_ or not mask[0].any():
            raise ValueError("M2 mask must be boolean (2,2500) with usable ECG")
        prepared = _m2_preprocess(signal, mask)
        tensor = torch.from_numpy(prepared[None])
        output = {}
        with torch.no_grad():
            for seed, (model, threshold) in sorted(self._model("M2").items()):
                score = float(torch.sigmoid(model(tensor))[0])
                output[str(seed)] = {"probability": score,
                                     "decision_true_vt": score >= threshold,
                                     "threshold": threshold}
        return {"target": "true_vt_alarm", "seeds": output,
                "primary_seed": "20261015", "calibrated": False}

    def predict_m3(self, ecg_ppg_125hz, *, sample_rate_hz=125):
        """Preprocessed 10-second ECG/PPG window, rows ECG then PPG.

        Caller must reproduce the pinned CinC-2015 loader's 125 Hz preprocessing.
        """
        import pandas as pd

        _rate(sample_rate_hz, 125)
        window = _array(ecg_ppg_125hz, (2, 1250), "M3 preprocessed ECG/PPG")
        features = _m3_features(window)
        model = self._model("M3")
        if model.n_features_in_ != 22:
            raise ValueError("M3 model feature count changed")
        score = float(model.predict_proba(np.array(list(features.values()))[None])[0, 1])
        threshold = float(self.manifest["models"]["M3"]["threshold"])
        return {"target": "synthetic_attack_window", "probability": score,
                "decision_attack": score > threshold, "threshold": threshold,
                "calibrated": False}

    def predict_m4(self, reference, candidate, reference_mask, candidate_mask,
                   *, sample_rate_hz=250):
        """Offline replay comparison on two ECG/PPG 10-second windows."""
        import pandas as pd

        _rate(sample_rate_hz, 250)
        ref = _array(reference, (2, 2500), "M4 reference")
        cand = _array(candidate, (2, 2500), "M4 candidate")
        rm = np.asarray(reference_mask)
        cm = np.asarray(candidate_mask)
        if (rm.shape != (2, 2500) or cm.shape != (2, 2500)
                or rm.dtype != np.bool_ or cm.dtype != np.bool_):
            raise ValueError("M4 masks must be boolean (2,2500)")
        bundle = self._model("M4")
        minimum = float(bundle["minimum_valid_fraction_per_channel"])
        if np.any(rm.mean(axis=1) < minimum) or np.any(cm.mean(axis=1) < minimum):
            raise ValueError("M4 requires >=90% valid samples in each channel/window")
        features = _m4_features(ref, cand, rm, cm)
        if (set(features) != set(bundle["feature_columns"])
                or not np.isfinite(list(features.values())).all()):
            raise ValueError("M4 returned missing or nonfinite features")
        frame = pd.DataFrame([{key: features[key] for key in bundle["feature_columns"]}])
        score = float(bundle["model"].predict_proba(frame)[0, 1])
        threshold = float(bundle["threshold"])
        return {"target": "synthetic_replay_similarity", "probability": score,
                "decision_replay": score >= threshold, "threshold": threshold,
                "channel_order_verified": bool(bundle["channel_order_verified"]),
                "deployment_status": bundle["deployment_status"], "calibrated": False}


def _CompactM2FCN():
    import torch.nn as nn

    class CompactM2FCN(nn.Module):
        def __init__(self):
            super().__init__()
            self.features = nn.Sequential(
                nn.Conv1d(4, 32, 15, padding=7, bias=False), nn.BatchNorm1d(32),
                nn.ReLU(), nn.MaxPool1d(2),
                nn.Conv1d(32, 64, 9, padding=4, bias=False), nn.BatchNorm1d(64),
                nn.ReLU(), nn.MaxPool1d(2),
                nn.Conv1d(64, 96, 5, padding=2, bias=False), nn.BatchNorm1d(96),
                nn.ReLU(), nn.AdaptiveAvgPool1d(1))
            self.classifier = nn.Sequential(nn.Flatten(), nn.Dropout(.25), nn.Linear(96, 1))

        def forward(self, values):
            return self.classifier(self.features(values)).squeeze(1)

    return CompactM2FCN()
