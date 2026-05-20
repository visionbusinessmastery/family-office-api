import hashlib
import json


def opportunity_fingerprint(payload: dict):
    raw = json.dumps(payload, sort_keys=True, default=str, separators=(",", ":"))
    return hashlib.sha256(raw.encode()).hexdigest()
