from fastapi import FastAPI, Request, HTTPException
import os
import logging
import requests

app = FastAPI()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("tekmetric")

CLICKSEND_USERNAME = os.environ.get("CLICKSEND_USERNAME", "")
CLICKSEND_KEY = os.environ.get("CLICKSEND_KEY", "")
SMS_TO = os.environ.get("SMS_TO", "")

def send_sms(message: str):
    payload = {
        "messages": [
            {"source": "python", "body": message, "to": SMS_TO}
        ]
    }
    r = requests.post(
        "https://rest.clicksend.com/v3/sms/send",
        json=payload,
        auth=(CLICKSEND_USERNAME, CLICKSEND_KEY),
        timeout=20
    )
    if r.status_code >= 400:
        raise HTTPException(status_code=502, detail="ClickSend SMS failed")

@app.get("/")
async def health():
    return {"ok": True}

@app.post("/webhooks/tekmetric")
async def tekmetric_webhook(request: Request):
    data = (await request.json()).get("data", {})

    # ✅ 1. Extract the label
    label = (
        data.get("repairOrderCustomLabel", {}) or {}
    ).get("name", "")
    label_norm = label.strip().lower()

    # ✅ Only trigger on EXACT business logic:
    #    custom label name is "Needs Parts"
    if label_norm != "needs parts":
        return {"ok": True}

    # ✅ 2. Get the RO number for the SMS
    ro_no = data.get("repairOrderNumber") or data.get("id") or "UNKNOWN"

    # ✅ 3. Send the SMS
    send_sms(f"RO {ro_no} is NEEDS PARTS")

    return {"ok": True}
