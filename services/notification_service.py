import os
import httpx

FCB_SERVER_KEY = os.getenv("FCB_SERVER_KEY", "")
FCM_URL = "https://fcm.googleapis.com/fcm/send"

async def send_push(fcm_token: str, title: str, body: str, data: dict = None):
    if not FCB_SERVER_KEY or not fcm_token:
        print("[FCM] Skipping — no key or token")
        return
    payload = {
        "to": fcm_token,
        "notification": {"title": title, "body": body, "sound": "default"},
        "data": data or {},
        "priority": "high",
    }
    headers = {"Authorization": f"key={FCB_SERVER_KEY}", "Content-Type": "application/json"}
    try:
        async with httpx.AsyncClient() as c:
            r = await c.post(FCM_URL, json=payload, headers=headers, timeout=10)
            print(f"[FCM] {r.status_code}")
    except Exception as e:
        print(f"[FCM] Error: {e}")
