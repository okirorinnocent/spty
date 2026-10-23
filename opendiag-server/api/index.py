"""OpenDiag report receiver for Vercel (Flask) + Supabase (Postgres via REST).

Environment variables (set in the Vercel dashboard, never in code):
  OPENDIAG_TOKEN        shared bearer token the agents send
  SUPABASE_URL          e.g. https://abcdxyz.supabase.co
  SUPABASE_SERVICE_KEY  service_role key (server-side only; never shipped to agents)
"""
import hmac
import os

import requests
from flask import Flask, jsonify, request


# ---- strict payload validation (inlined so the function is one self-contained file) ----
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


app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 64 * 1024  # reject oversized bodies


def _authorised() -> bool:
    expected = os.environ.get("OPENDIAG_TOKEN", "")
    header = request.headers.get("Authorization", "")
    supplied = header[7:] if header.startswith("Bearer ") else ""
    return bool(expected) and hmac.compare_digest(supplied, expected)


def _to_rows(payload: dict) -> list:
    """Map validated records to table rows (only known columns)."""
    rows = []
    for rec in payload["records"]:
        rows.append({
            "device_id": payload["device_id"],
            "local_id": rec.get("id"),
            "recorded_at": rec["recorded_at"],
            "cpu_percent": rec.get("cpu_percent"),
            "memory_percent": rec.get("memory_percent"),
            "disk_free_gb": rec.get("disk_free_gb"),
            "disk_total_gb": rec.get("disk_total_gb"),
            "health_status": rec["health_status"],
        })
    return rows


@app.get("/")
def home():
    return "OpenDiag report receiver. Hardware health telemetry only. See your organisation's privacy notice.", 200


@app.get("/api/health")
def health():
    return jsonify(status="ok"), 200


@app.post("/api/v1/reports")
def receive_report():
    if not _authorised():
        return jsonify(error="unauthorised"), 401
    payload = request.get_json(silent=True)
    errors = validate_payload(payload)
    if errors:
        return jsonify(error="invalid payload", details=errors), 400

    base = os.environ.get("SUPABASE_URL", "").rstrip("/")
    key = os.environ.get("SUPABASE_SERVICE_KEY", "")
    if not base or not key:
        return jsonify(error="server not configured"), 500
    try:
        resp = requests.post(
            f"{base}/rest/v1/reports?on_conflict=device_id,recorded_at",
            json=_to_rows(payload),
            headers={
                "apikey": key,
                "Authorization": f"Bearer {key}",
                "Content-Type": "application/json",
                # duplicates (agent retries) are ignored, so retries are safe
                "Prefer": "resolution=ignore-duplicates,return=minimal",
            },
            timeout=10,
        )
    except requests.RequestException:
        return jsonify(error="storage unavailable"), 502
    if resp.status_code >= 300:
        return jsonify(error="storage rejected the data"), 502
    return jsonify(accepted=len(payload["records"])), 201
