import unittest

from sentinelward_ml import validate_m5_event


NOW = 1_792_160_010_000


def event(**changes):
    value = {
        "device_id": "device-B01", "detector": "M5", "status": "active",
        "network_suspicion_score": 0.81, "model_version": "rf-baseline-v1",
        "reasons": ["high_message_rate_burst"], "observed_at": NOW / 1000 - 2,
        "schema_version": "1.0",
    }
    value.update(changes)
    return value


class M5ExternalTests(unittest.TestCase):
    def check(self, data):
        return validate_m5_event(data, authenticated_device_id="device-B01", now_ms=NOW)

    def test_active_and_unavailable(self):
        result = self.check(event())
        self.assertEqual(result["score"], 0.81)
        self.assertEqual(result["target"], "synthetic_network_anomaly")
        self.assertIsNone(self.check(event(status="unavailable", network_suspicion_score=None))["score"])

    def test_identity_and_timing(self):
        for bad in (event(device_id="device-B02"), event(detector="M4"),
                    event(observed_at=NOW / 1000 - 30),
                    event(observed_at=NOW / 1000 + 5)):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                self.check(bad)

    def test_invalid_score_and_status(self):
        for bad in (event(network_suspicion_score=float("nan")),
                    event(network_suspicion_score=1.1),
                    event(network_suspicion_score=True),
                    event(status="degraded", network_suspicion_score=0.4),
                    event(status="other")):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                self.check(bad)


if __name__ == "__main__":
    unittest.main()
