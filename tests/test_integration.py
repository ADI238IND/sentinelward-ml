"""Execution and input-contract smoke checks; not performance validation."""

import unittest

import numpy as np

from sentinelward_ml import SentinelWardModels


class InferenceSmokeTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.models = SentinelWardModels()
        cls.rng = np.random.default_rng(314159)

    def test_m1_full_record(self):
        signal = self.rng.normal(size=(5000, 12))
        result = self.models.predict_m1(signal)
        self.assertEqual(len(result["seed_probabilities"]), 5)
        self.assertTrue(all(0 <= score <= 1 for score in result["seed_probabilities"]))
        with self.assertRaises(ValueError):
            self.models.predict_m1(signal, sample_rate_hz=250)

    def test_m2_all_checkpoints(self):
        signal = self.rng.normal(size=(2, 2500))
        mask = np.ones_like(signal, dtype=bool)
        result = self.models.predict_m2(signal, mask)
        self.assertEqual(len(result["seeds"]), 5)
        self.assertEqual(result["primary_seed"], "20261015")
        with self.assertRaises(ValueError):
            self.models.predict_m2(signal, mask.astype(int))

    def test_m3_fixed_feature_count(self):
        signal = self.rng.normal(size=(2, 1250))
        result = self.models.predict_m3(signal)
        self.assertTrue(0 <= result["probability"] <= 1)
        with self.assertRaises(ValueError):
            self.models.predict_m3(signal[:, :-1])

    def test_m4_replay_and_mask_guard(self):
        signal = self.rng.normal(size=(2, 2500))
        mask = np.ones_like(signal, dtype=bool)
        result = self.models.predict_m4(signal, signal, mask, mask)
        self.assertTrue(0 <= result["probability"] <= 1)
        self.assertFalse(result["channel_order_verified"])
        bad_mask = mask.copy()
        bad_mask[0, :300] = False
        with self.assertRaises(ValueError):
            self.models.predict_m4(signal, signal, bad_mask, mask)


if __name__ == "__main__":
    unittest.main()
