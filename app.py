from fastapi import FastAPI, Request, HTTPException
import os
import logging
import requests
from typing import Any, Dict, List, Tuple, Union

app = FastAPI()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("tekmetric-webhook-clicksend")

CLICKSEND_USERNAME = os.environ.get("CLICKSEND_USERNAME", "")
CLICKSEND_KEY = os.environ.get("CLICKSEND_KEY", "")
SMS_TO = os.environ.get("SMS_TO", "")

# We normalize strings (lowercase, collapse separators) and compare to this
NEEDS_PARTS_NORMALIZED = {
    "needs parts", "need parts"
}

def send_sms(message: str):
    if not (CLICKSEND_USERNAME and CLICKSEND_KEY and SMS_TO):
        raise RuntimeError("Missing CLICKSEND_USERNAME, CLICKSEND_KEY, or SMS_TO environment variables.")

    payload = {
        "messages": [
            {"source": "python", "body": message, "to": SMS_TO}
        ]
    }
    resp = requests.post(
        "https://rest.clicksend.com/v3/sms/send",
        json=payload,
        auth=(CLICKSEND_USERNAME, CLICKSEND_KEY),
        timeout=20
    )
    if resp.status_code >= 400:
        logger.error("ClickSend error %s: %s", resp.status_code, resp.text)
        raise HTTPException(status_code=502, detail="Failed to send SMS via ClickSend")
    return resp.json()

def _normalize(s: str) -> str:
    """lowercase and collapse spaces/underscores/dashes for robust compare"""
    s = (s or "").strip().lower()
    s = s.replace("_", " ").replace("-", " ")
    s = " ".join(s.split())
    return s

def _is_needs_parts(value: Any) -> bool:
    if not isinstance(value, str):
        return False
    return _normalize(value) in NEEDS_PARTS_NORMALIZED

Json = Union[Dict[str, Any], List[Any], Any]

def find_ro_number(payload: Dict[str, Any]) -> str:
    """Try several common keys to get a human-friendly RO number."""
    if not isinstance(payload, dict):
        return "UNKNOWN"

    candidate_keys = [
        "number", "roNumber", "repairOrderNumber", "orderNumber",
        "ro_number", "repair_order_number", "order_number",
        "ticketNumber", "ticket_number",
        "id", "roId", "repairOrderId", "orderId", "ro_id", "order_id"
    ]

    queue = [payload]
    while queue:
        cur = queue.pop(0)
        if isinstance(cur, dict):
            for ck in candidate_keys:
                if ck in cur and isinstance(cur[ck], (str, int)):
                    return str(cur[ck])
                for k in cur.keys():
                    lowerk = k.lower()
                    if any(pk in lowerk for pk in ["ronumber", "repairordernumber", "ordernumber"]):
                        val = cur.get(k)
                        if isinstance(val, (str, int)):
                            return str(val)
            for v in cur.values():
                if isinstance(v, (dict, list)):
                    queue.append(v)
        elif isinstance(cur, list):
            for v in cur:
                if isinstance(v, (dict, list)):
                    queue.append(v)

    return "UNKNOWN"

@app.get("/")
async def health():
    return {"ok": True}

@app.post("/webhooks/tekmetric")
async def tekmetric_webhook(request: Request):
    # We ONLY care about: data.repairOrderCustomLabel.name
    try:
        payload = await request.json()
    except Exception:
        logger.exception("Invalid JSON payload")
        raise HTTPException(status_code=400, detail="Invalid JSON")

    logger.info(
        "Received payload (top-level keys): %s",
        list(payload.keys()) if isinstance(payload, dict) else type(payload)
    )

    data = payload.get("data", payload) if isinstance(payload, dict) else payload
    if not isinstance(data, dict):
        return {"ok": True, "note": "payload not a dict"}

    # ---- ONLY look under repairOrderCustomLabel.name ----
    label_obj = data.get("repairOrderCustomLabel", {})
    label_name = label_obj.get("name") if isinstance(label_obj, dict) else None

    if not _is_needs_parts(label_name):
        # Not our event — ack without doing anything
        return {"ok": True, "note": "repairOrderCustomLabel.name is not NEEDS PARTS"}

    # If we got here, it IS Needs Parts (as defined by our normalization)
    ro_no = find_ro_number(data)
    msg = f"RO {ro_no} is NEEDS PARTS"

    try:
        send_sms(msg)
        logger.info("SMS sent for RO %s", ro_no)
    except Exception as e:
        logger.exception("Failed to send SMS: %s", e)
        raise

    return {"ok": True}
