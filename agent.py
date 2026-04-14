# agent.py
from datetime import datetime
from rules import CARE_RULES

def decide(plant):
    care = CARE_RULES.get(plant["type"])
    if not care:
        return "🤔 No care info available"

    days_between = care["water_days"]
    soon_threshold = care.get("soon_threshold", 2)
    overdue_threshold = care.get("overdue_threshold", 4)

    last_watered = datetime.strptime(plant["last_watered"], "%Y-%m-%d")
    days_since = (datetime.now() - last_watered).days

    if days_since < days_between:
        return f"✅ Healthy (Water every {days_between} days)"
    elif days_since < days_between + soon_threshold:
        return f"💧 Needs water soon (Water every {days_between} days)"
    else:
        return f"🚨 Overdue: Water today! ({care['notes']})"

def care_info(plant):
    care = CARE_RULES.get(plant["type"])
    if not care:
        return "🤔 No care info available"

    info = (
        f"🌿 {plant['name']} ({plant['type']})\n"
        f"Water every: {care['water_days']} days\n"
        f"Light: {care['light']}\n"
        f"Humidity: {care['humidity']}\n"
        f"Notes: {care['notes']}"
    )
    return info

def next_action(plant):
    status = decide(plant)
    if "Overdue" in status or "Needs water soon" in status:
        return f"Reminder: {plant['name']} ({plant['type']}) {status}"
    return None
