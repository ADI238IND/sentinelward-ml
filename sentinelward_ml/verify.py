"""Verify every packaged research artifact without deserializing model files."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path


def _expected_files(root):
    model_spec = json.loads((root / "models" / "manifest.json").read_text())
    component_spec = json.loads((root / "components" / "manifest.json").read_text())
    expected = {}
    for name, spec in model_spec["models"].items():
        if "files" in spec:
            for filename, digest in spec["files"].items():
                expected[f"models/{filename}"] = digest
        else:
            expected[f"models/{spec['file']}"] = spec["sha256"]
    for filename, digest in component_spec["sha256"].items():
        expected[f"components/{filename}"] = digest
    return expected


def verify_artifacts(root=None):
    """Return counts, failing on missing, tampered or unsafe manifest entries."""
    base = Path(root or Path(__file__).resolve().parents[1]).resolve()
    expected = _expected_files(base)
    if not expected:
        raise ValueError("No model artifacts listed")
    for relative, digest in expected.items():
        path = (base / relative).resolve()
        if not path.is_relative_to(base) or not path.is_file():
            raise ValueError(f"Missing or unsafe artifact: {relative}")
        if not isinstance(digest, str) or len(digest) != 64:
            raise ValueError(f"Invalid manifest digest: {relative}")
        actual = hashlib.sha256()
        with path.open("rb") as handle:
            for block in iter(lambda: handle.read(1024 * 1024), b""):
                actual.update(block)
        if actual.hexdigest() != digest.lower():
            raise ValueError(f"Artifact SHA-256 mismatch: {relative}")
    return {"verified_artifacts": len(expected), "status": "sha256_pass",
            "meaning": "Integrity only; no model performance or deployment validation"}


if __name__ == "__main__":
    print(json.dumps(verify_artifacts(), indent=2))
