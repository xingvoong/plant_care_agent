import time
import requests
from storage import load, save, today
from agent import decide
import os

BOT_TOKEN = os.getenv("BOT_TOKEN")

if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN not set")

BASE_URL = f"https://api.telegram.org/bot{BOT_TOKEN}"

def send(chat_id, text):
    requests.post(f"{BASE_URL}/sendMessage", json={
        "chat_id": chat_id,
        "text": text
    })

def get_updates(offset=None):
    params = {"timeout": 30}
    if offset:
        params["offset"] = offset
    return requests.get(f"{BASE_URL}/getUpdates", params=params).json()

def handle(msg):
    text = msg.get("text", "")
    chat = msg["chat"]["id"]
    user = str(msg["from"]["id"])

    data = load()
    data.setdefault(user, [])

    if text.startswith("/addplant"):
        _, ptype, *name = text.split()
        data[user].append({
            "name": " ".join(name),
            "type": ptype.lower(),
            "last_watered": today()
        })
        save(data)
        send(chat, "✅ Plant added")

    elif text == "/status":
        reply = ""
        for p in data[user]:
            reply += f"{p['name']}: {decide(p)}\n"
        send(chat, reply or "🌱 No plants")

def main():
    offset = None
    print("🌱 MVP Plant Agent running")

    while True:
        updates = get_updates(offset)
        for u in updates.get("result", []):
            offset = u["update_id"] + 1
            if "message" in u:
                handle(u["message"])
        time.sleep(1)

if __name__ == "__main__":
    main()
