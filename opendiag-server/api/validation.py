"""Strict, server-side validation of incoming reports (framework independent)."""

ALLOWED_RECORD_FIELDS = {
    "id": int, "recorded_at": str, "health_status": str,
    "cpu_percent": (int, float), "memory_percent": (int, float),
    "disk_free_gb": (int, float), "disk_total_gb": (int, float),
}
MAX_RECORDS = 100


def validate_payload(payload) -> list:
    """Return a list of problems (empty list = valid)."""
    errors = []
    if not isinstance(payload, dict):
        return ["payload must be a JSON object"]
    if set(payload) != {"device_id", "records"}:
        return ["payload keys must be exactly: device_id, records"]
    if not isinstance(payload["device_id"], str) or not 0 < len(payload["device_id"]) <= 64:
        errors.append("device_id must be a string of 1-64 characters")
    records = payload["records"]
    if not isinstance(records, list) or not 0 < len(records) <= MAX_RECORDS:
        return errors + [f"records must be a list of 1-{MAX_RECORDS} items"]
    for i, rec in enumerate(records):
        if not isinstance(rec, dict):
            errors.append(f"record {i}: must be an object")
            continue
        for key, value in rec.items():
            expected = ALLOWED_RECORD_FIELDS.get(key)
            if expected is None:
                errors.append(f"record {i}: unexpected field '{key}'")
            elif isinstance(value, bool) or (value is not None and not isinstance(value, expected)):
                errors.append(f"record {i}: wrong type for '{key}'")
        if not isinstance(rec.get("recorded_at"), str):
            errors.append(f"record {i}: recorded_at is required")
        if rec.get("health_status") not in {"ok", "warn", "critical"}:
            errors.append(f"record {i}: invalid health_status")
    return errors
