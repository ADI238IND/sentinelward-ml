"""Prove that package integrity checking detects altered bytes."""

import hashlib
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from sentinelward_ml.verify import verify_artifacts


class ArtifactVerificationTest(unittest.TestCase):
    def test_repository_artifacts(self):
        self.assertEqual(verify_artifacts()["verified_artifacts"], 31)

    def test_tampered_file_is_rejected(self):
        with TemporaryDirectory(dir=Path(__file__).resolve().parents[1]) as directory:
            root = Path(directory)
            (root / "models").mkdir()
            (root / "components" / "SentinelWard_D").mkdir(parents=True)
            (root / "models" / "safe.bin").write_bytes(b"original")
            (root / "components" / "SentinelWard_D" / "rules.txt").write_bytes(b"rules")
            (root / "models" / "manifest.json").write_text(json.dumps({"models": {
                "M1": {"file": "safe.bin", "sha256": hashlib.sha256(b"original").hexdigest()}}}))
            (root / "components" / "manifest.json").write_text(json.dumps({"sha256": {
                "SentinelWard_D/rules.txt": hashlib.sha256(b"rules").hexdigest()}}))
            self.assertEqual(verify_artifacts(root)["verified_artifacts"], 2)
            (root / "models" / "safe.bin").write_bytes(b"tampered")
            with self.assertRaisesRegex(ValueError, "SHA-256 mismatch"):
                verify_artifacts(root)


if __name__ == "__main__":
    unittest.main()
