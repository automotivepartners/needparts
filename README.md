
# Tekmetric Webhook → ClickSend SMS (Railway-ready)

Tiny FastAPI service that listens for Tekmetric Repair Order updates and sends you an SMS **when status becomes `NEEDS PARTS`** — **without** Twilio/A2P registration. Uses **ClickSend**.

## Quick Deploy (Railway)

1. **Create a new GitHub repo** and upload these files.
2. Go to **https://railway.app** → **New** → **Deploy from GitHub Repo** → select this repo.
3. In your Railway service, open **Variables** and set:
   - `CLICKSEND_USERNAME` = your ClickSend login email
   - `CLICKSEND_KEY` = API key from ClickSend Dashboard → Developers → API Credentials
   - `SMS_TO` = destination phone (e.g., `+1XXXXXXXXXX`)
   - (Optional) `PORT` = `8000` (Railway provides `$PORT` automatically; the Procfile uses it)
4. Wait for deploy → copy your public HTTPS domain from **Settings → Domains**.
5. In **Tekmetric → Settings → Integrations → Webhooks → Add Webhook**:
   - Name: `Needs Parts Alert`
   - URL: `https://<your-app>.up.railway.app/webhooks/tekmetric`
   - Event: `Repair Order Updated` (wording may vary)

## Test

From your terminal (replace domain):
```bash
curl -X POST -H "Content-Type: application/json" \
  -d '{"data":{"status":"NEEDS PARTS","number":"RO-1234"}}' \
  https://<your-app>.up.railway.app/webhooks/tekmetric
```

You should receive an SMS: `RO RO-1234 is NEEDS PARTS`.

## Notes

- Status normalization supports: `needs parts`, `need parts`, `needs-parts`, `needs_parts`.
- Endpoint `GET /` returns `{ "ok": true }` for health checks.
- For production hardening, consider adding:
  - Signature verification (shared secret header from Tekmetric, if available)
  - Duplicate-alert suppression (store previous status in Redis/DB and only alert on transitions)
  - Rate limiting / retries

## Files

- `app.py` — FastAPI webhook + ClickSend SMS send
- `requirements.txt` — Python deps
- `Procfile` — process definition for Railway (`uvicorn app:app --host 0.0.0.0 --port $PORT`)

## Local Run (optional)

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
export CLICKSEND_USERNAME="you@example.com"
export CLICKSEND_KEY="your_api_key"
export SMS_TO="+1XXXXXXXXXX"
uvicorn app:app --host 0.0.0.0 --port 8080
```

Then:
```bash
curl -X POST -H "Content-Type: application/json"   -d '{"data":{"status":"NEEDS PARTS","number":"RO-1234"}}'   http://localhost:8080/webhooks/tekmetric
```

## License

MIT
