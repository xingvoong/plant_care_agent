# bot.py

import os
import re
import time
import requests
from k8s_storage import load, save, today
from agent import decide
from rules import CARE_RULES
from llm import ask


# ==============================
# CONFIG
# ==============================

BOT_TOKEN = os.getenv("BOT_TOKEN")

if not BOT_TOKEN:
    raise RuntimeError("❌ BOT_TOKEN not set in environment")

BASE_URL = f"https://api.telegram.org/bot{BOT_TOKEN}"


# ==============================
# TELEGRAM HELPERS
# ==============================

def send(chat_id, text):
    requests.post(f"{BASE_URL}/sendMessage", json={
        "chat_id": chat_id,
        "text": text
    })


def get_updates(offset=None):
    params = {"timeout": 1}
    if offset:
        params["offset"] = offset
    r = requests.get(f"{BASE_URL}/getUpdates", params=params)
    return r.json()


# ==============================
# INTENT DETECTION
# ==============================

WATER_WORDS = ["watered", "water", "watering"]
ADD_WORDS = ["add", "added", "got", "have", "bought", "new"]


def detect_water(text, plants):
    """Return plant if user mentions watering it by name."""
    for p in plants:
        if p["name"].lower() in text:
            if any(w in text for w in WATER_WORDS):
                return p
    return None


def detect_add(text):
    """Return {type, name} if user wants to add a known plant type."""
    if not any(w in text for w in ADD_WORDS):
        return None
    for ptype in CARE_RULES:
        if ptype in text:
            match = re.search(r'(?:called|named)\s+([A-Za-z ]+)', text)
            name = match.group(1).strip().title() if match else ptype.title()
            return {"type": ptype, "name": name}
    return None


# ==============================
# MESSAGE HANDLER
# ==============================

def handle(msg):
    text = msg.get("text", "").strip()
    if not text:
        return

    chat = msg["chat"]["id"]
    user = str(msg["from"]["id"])

    data = load()
    data.setdefault(user, [])

    text_lower = text.lower()

    # Did they water a plant?
    watered = detect_water(text_lower, data[user])
    if watered:
        watered["last_watered"] = today()
        save(data)
        send(chat, f"Got it! Recorded that you watered {watered['name']} today.")
        return

    # Are they adding a plant?
    new_plant = detect_add(text_lower)
    if new_plant:
        new_plant["last_watered"] = today()
        data[user].append(new_plant)
        save(data)
        send(chat, f"Added {new_plant['name']} ({new_plant['type']})!")
        return

    # Everything else → LLM with full plant context including status
    plant_context = []
    for p in data[user]:
        status = decide(p)
        plant_context.append({**p, "status": status})

    reply = ask(text, plant_context)
    send(chat, reply)


# ==============================
# MAIN LOOP
# ==============================

def main():
    print("🌱 Plant Care Bot started...")
    offset = None

    while True:
        updates = get_updates(offset)
        for u in updates.get("result", []):
            offset = u["update_id"] + 1
            if "message" in u:
                handle(u["message"])
        time.sleep(0.1)


if __name__ == "__main__":
    print("FILE LOADED")
    main()
