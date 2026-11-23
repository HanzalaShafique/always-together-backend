# Hugging Face Space — Secrets Setup

Configure these secrets in your HF Space before deploying.

**Navigation:** Space → Settings → Variables and secrets → **New secret**

---

## Required Secrets

| Secret name | Value | Notes |
|-------------|-------|-------|
| `MONGODB_URI` | `mongodb+srv://hanzala1000:hanzala1000@cluster0.powru.mongodb.net/` | Atlas connection string. Append `?retryWrites=true&w=majority` for extra safety. |
| `JWT_SECRET` | *(generate below)* | 64-character random string used to sign JWT tokens. **Never reuse across environments.** |
| `FCB_SERVER_KEY` | *(from Firebase console)* | Firebase Cloud Messaging legacy server key — see instructions below. |
| `HF_TOKEN` | `YOUR_HF_TOKEN` | Hugging Face write token (used by `deploy.sh`). Keep private. |
| `SPACE_URL` | `https://hanzala1000-always-together-backend.hf.space` | Full URL of this Space — used by the keepalive self-ping. |

---

## Generating JWT_SECRET

Run **any one** of the following:

```bash
# Option A — Python (cross-platform)
python -c "import secrets; print(secrets.token_hex(32))"

# Option B — OpenSSL
openssl rand -hex 32

# Option C — Node.js
node -e "console.log(require('crypto').randomBytes(32).toString('hex'))"
```

Copy the 64-character hex string and paste it as the `JWT_SECRET` value.

---

## Getting FCB_SERVER_KEY (Firebase Cloud Messaging)

1. Open the [Firebase console](https://console.firebase.google.com/) and select your project.
2. Click the ⚙️ **gear icon** → **Project settings**.
3. Navigate to the **Cloud Messaging** tab.
4. Under **Cloud Messaging API (Legacy)**, copy the **Server key** value.
   - If you only see the new Firebase Cloud Messaging API, enable the legacy API or use a service-account JSON instead (update `services/notification_service.py` accordingly).
5. Paste the key as the `FCB_SERVER_KEY` secret.

---

## Verifying Secrets Are Loaded

After saving all secrets and triggering a build, SSH into the running container
(HF Spaces → Runtime → Open terminal) and run:

```bash
env | grep -E 'MONGODB_URI|JWT_SECRET|FCB_SERVER_KEY|HF_TOKEN|SPACE_URL'
```

All five variables should appear (values redacted in the terminal for security).

---

> [!CAUTION]
> Never commit secrets to Git. The `.gitignore` already excludes `.env` files,
> but double-check before pushing. HF Space secrets are injected at runtime and
> never baked into the Docker image.
