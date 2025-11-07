
from fastapi import FastAPI, Request, HTTPException
import os
import logging
import requests

app = FastAPI()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("tekmetric-webhook-clicksend")

CLICKSEND_USERNAME = os.environ.get("CLICKSEND_USERNAME", "")
CLICKSEND_KEY = os.environ.get("CLICKSEND_KEY", "")
SMS_TO = os.environ.get("SMS_TO", "")

def send_sms(message: str):
    if not (CLICKSEND_USERNAME and CLICKSEND_KEY and SMS_TO):
        raise RuntimeError("Missing CLICKSEND_USERNAME, CLICKSEND_KEY, or SMS_TO environment variables.")

    payload = {
        "messages": [
            {
                "source": "python",
                "body": message,
                "to": SMS_TO
            }
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

@app.get("/")
async def health():
    return {"ok": True}

@app.post("/webhooks/tekmetric")
async def tekmetric_webhook(request: Request):
    try:
        payload = await request.json()
    except Exception:
        logger.exception("Invalid JSON payload")
        raise HTTPException(status_code=400, detail="Invalid JSON")

    logger.info("Received payload: %s", payload)

    data = payload.get("data", {}) if isinstance(payload, dict) else {}
    status = (data.get("status") or "").strip().lower()
    ro_number = data.get("number") or data.get("id") or "UNKNOWN"

    needs_parts_aliases = {"needs parts", "need parts", "needs-parts", "needs_parts"}

    if status in needs_parts_aliases:
        msg = f"RO {ro_number} is NEEDS PARTS"
        try:
            send_sms(msg)
            logger.info("SMS sent for RO %s", ro_number)
        except Exception as e:
            logger.exception("Failed to send SMS: %s", e)
            raise

    return {"ok": True}
