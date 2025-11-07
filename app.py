
from fastapi import FastAPI, Request, HTTPException
from twilio.rest import Client
import os
import logging

app = FastAPI()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("tekmetric-webhook")

# Twilio client (initialized lazily in case env vars are added later)
def get_twilio_client():
    sid = os.environ.get("TWILIO_SID")
    token = os.environ.get("TWILIO_TOKEN")
    if not sid or not token:
        raise RuntimeError("Missing TWILIO_SID or TWILIO_TOKEN environment variables.")
    return Client(sid, token)

FROM = os.environ.get("TWILIO_FROM", "")
TO = os.environ.get("SMS_TO", "")

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

    # Log the raw payload for initial verification (consider redacting in production)
    logger.info("Received payload: %s", payload)

    data = payload.get("data", {}) if isinstance(payload, dict) else {}
    status = (data.get("status") or "").strip().lower()
    ro_number = data.get("number") or data.get("id") or "UNKNOWN"

    # Normalize common variants
    needs_parts_aliases = {"needs parts", "need parts", "needs-parts", "needs_parts"}

    if status in needs_parts_aliases:
        if not (FROM and TO):
            logger.error("Missing TWILIO_FROM or SMS_TO environment variables.")
            raise HTTPException(status_code=500, detail="SMS not configured on server")

        try:
            client = get_twilio_client()
            client.messages.create(
                to=TO,
                from_=FROM,
                body=f"RO {ro_number} is NEEDS PARTS"
            )
            logger.info("SMS sent for RO %s", ro_number)
        except Exception as e:
            logger.exception("Failed to send SMS: %s", e)
            raise HTTPException(status_code=502, detail="Failed to send SMS")

    return {"ok": True}
