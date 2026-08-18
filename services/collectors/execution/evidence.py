"""Content addressing for acquisition evidence.

Two distinct hashes are kept, because they answer different questions:

``request_fingerprint``
    What did we ask the provider for? Derived from the canonicalised request, so
    the same logical question always produces the same fingerprint.

``artifact_hash``
    What exactly did the provider send back? Derived from the raw response bytes,
    so a payload can be proven unmodified.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping, Sequence

# Query parameters that must never enter a fingerprint, because a fingerprint is
# published in manifests and stored in the clear.
_SECRET_PARAM_NAMES = frozenset({"key", "apikey", "api_key", "token", "access_token", "password"})


def canonical_json(payload: object) -> str:
    """Serialise deterministically: sorted keys, no insignificant whitespace."""

    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def artifact_hash(raw_body: bytes) -> str:
    """Hash the exact bytes the provider returned."""

    return sha256_hex(raw_body)


def request_fingerprint(method: str, url: str, params: Mapping[str, object]) -> str:
    """Hash the canonical form of a provider request, with secrets excluded.

    Raises when a parameter name looks like a credential, so a future collector
    cannot accidentally hash (and therefore publish a distinguisher for) a key.
    """

    leaked = sorted(name for name in params if name.lower() in _SECRET_PARAM_NAMES)
    if leaked:
        raise ValueError(f"refusing to fingerprint credential-bearing parameters: {leaked}")

    normalised: dict[str, object] = {}
    for name, value in params.items():
        if isinstance(value, (list, tuple)) and not isinstance(value, (str, bytes)):
            normalised[name] = [str(item) for item in value]
        else:
            normalised[name] = str(value)

    canonical = canonical_json(
        {"method": method.upper(), "url": url, "params": normalised}
    )
    return sha256_hex(canonical.encode("utf-8"))


def record_id_for(parts: Sequence[str]) -> str:
    """Deterministic record identity from a natural key.

    Two runs that observe the same provider issue for the same cell and valid
    time derive the same identifier, which is what makes re-runs idempotent
    instead of duplicating evidence.
    """

    if not parts or any(not str(part).strip() for part in parts):
        raise ValueError("record identity parts must all be non-blank")
    return sha256_hex("\x1f".join(str(part) for part in parts).encode("utf-8"))
