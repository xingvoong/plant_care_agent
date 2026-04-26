# reconciler.py
# Core reconcile logic — ports agent.decide() for Kubernetes Plant resources.
# Called by kopf handlers in main.py.

import os
import requests
from datetime import datetime

CARE_RULES = {
    "prayer plant": {
        "water_days": 8,
        "light": "Bright indirect light",
        "humidity": "Moderate to high",
        "notes": "Keep soil consistently moist but not soggy. Sensitive to over-/underwatering.",
        "soon_threshold": 2,
        "overdue_threshold": 4,
    },
    "pothos": {
        "water_days": 12,
        "light": "Bright indirect to low light",
        "humidity": "Medium",
        "notes": "Let top 50–75% of soil dry between waterings. Adapts to many indoor conditions.",
        "soon_threshold": 2,
        "overdue_threshold": 4,
    },
    "golden snake": {
        "water_days": 21,
        "light": "Low to bright indirect light",
        "humidity": "Low to medium",
        "notes": "Drought-tolerant; water only after soil dries completely. Avoid overwatering.",
        "soon_threshold": 3,
        "overdue_threshold": 5,
    },
}

BOT_TOKEN = os.getenv("BOT_TOKEN")
BASE_URL = f"https://api.telegram.org/bot{BOT_TOKEN}" if BOT_TOKEN else None


def decide(plant_type, last_watered_str):
    """
    Compute condition for a plant given its type and last watered date.
    Returns (condition, message) where condition is one of:
      "healthy" | "needsWaterSoon" | "overdue"
    """
    care = CARE_RULES.get(plant_type)
    if not care:
        return "healthy", f"Unknown plant type: {plant_type}"

    last_watered = datetime.strptime(last_watered_str, "%Y-%m-%d")
    days_since = (datetime.now() - last_watered).days
    water_days = care["water_days"]
    soon_threshold = care.get("soon_threshold", 2)

    if days_since < water_days:
        return "healthy", f"Watered {days_since}d ago. Next watering in {water_days - days_since}d."
    elif days_since < water_days + soon_threshold:
        return "needsWaterSoon", f"Water soon. {days_since}d since last watered (every {water_days}d)."
    else:
        return "overdue", f"Overdue by {days_since - water_days}d. {care['notes']}"


def send_telegram(owner_id, plant_name, message):
    """Send a Telegram reminder to the plant owner. No-ops if BOT_TOKEN is unset."""
    if not BASE_URL:
        print(f"[reconciler] BOT_TOKEN not set — skipping Telegram for {owner_id}")
        return
    requests.post(f"{BASE_URL}/sendMessage", json={
        "chat_id": int(owner_id),
        "text": f"Plant reminder: {plant_name} — {message}",
    })


def reconcile(spec, today_str):
    """
    Given a Plant spec dict and today's date string (YYYY-MM-DD), return:
      - status_patch: dict to write back to status
      - should_remind: bool — True if a Telegram reminder should fire
    """
    plant_type = spec["plantType"]
    last_watered = spec["lastWatered"]
    plant_name = spec["plantName"]

    condition, message = decide(plant_type, last_watered)
    should_remind = condition in ("needsWaterSoon", "overdue")

    status_patch = {
        "condition": condition,
        "message": message,
    }
    if should_remind:
        status_patch["lastReminded"] = today_str

    print(f"[reconciler] {plant_name} ({plant_type}): {condition} — {message}")
    return status_patch, should_remind
