# bot.py
import time
import requests
from storage import load, save, today
from agent import decide, care_info
from rules import CARE_RULES
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

    # --- ADD PLANT ---
    if text.startswith("/addplant"):
        parts = text.split()
        if len(parts) < 3:
            send(chat, "❌ Usage: /addplant <type> <name>")
            return

        ptype = parts[1].lower().strip()
        name = " ".join(parts[2:]).strip('"')

        if ptype not in CARE_RULES:
            send(chat, f"❌ Unknown plant type '{ptype}'. Available types: {', '.join(CARE_RULES.keys())}")
            return

        data[user].append({
            "name": name,
            "type": ptype,
            "last_watered": today()
        })
        save(data)
        send(chat, f"✅ {name} added!")

    # --- WATER PLANT ---
    elif text.startswith("/water"):
        parts = text.split()
        if len(parts) < 2:
            send(chat, "❌ Usage: /water <plant_name>")
            return

        pname = " ".join(parts[1:]).strip('"')
        found = False
        for p in data[user]:
            if p["name"].lower() == pname.lower():
                p["last_watered"] = today()
                found = True
                save(data)
                send(chat, f"💧 {p['name']} watered!")
                break
        if not found:
            send(chat, f"❌ Plant '{pname}' not found")

    # --- REMOVE PLANT ---
    elif text.startswith("/removeplant"):
        parts = text.split()
        if len(parts) < 2:
            send(chat, "❌ Usage: /removeplant <plant_name>")
            return

        pname = " ".join(parts[1:]).strip('"')
        new_list = [p for p in data[user] if p["name"].lower() != pname.lower()]
        if len(new_list) == len(data[user]):
            send(chat, f"❌ Plant '{pname}' not found")
        else:
            data[user] = new_list
            save(data)
            send(chat, f"🗑️ {pname} removed!")

    # --- STATUS ---
    elif text == "/status":
        reply = ""
        for p in data[user]:
            reply += f"{p['name']}: {decide(p)}\n"
        send(chat, reply or "🌱 No plants")

    # --- CARE INFO ---
    elif text.startswith("/care"):
        parts = text.split()
        if len(parts) < 2:
            send(chat, "❌ Usage: /care <plant_name>")
            return

        pname = " ".join(parts[1:]).strip('"')
        found = False
        for p in data[user]:
            if p["name"].lower() == pname.lower():
                info = care_info(p)
                send(chat, info)
                found = True
                break
        if not found:
            send(chat, f"❌ Plant '{pname}' not found")

def main():
    offset = None
    print("🌱 Plant Care Bot running...")
    while True:
        updates = get_updates(offset)
        for u in updates.get("result", []):
            offset = u["update_id"] + 1
            if "message" in u:
                handle(u["message"])
        time.sleep(1)

if __name__ == "__main__":
    main()
