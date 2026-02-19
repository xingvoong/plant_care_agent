# agent.py
from datetime import datetime
from rules import CARE_RULES

def decide(plant):
    """
    Decide watering status for a plant based on last watered date
    and care info from CARE_RULES.
    """
    care = CARE_RULES.get(plant["type"])
    if not care:
        return "🤔 No care info available"

    days_between = care["water_days"]
    last_watered = datetime.strptime(plant["last_watered"], "%Y-%m-%d")
    days_since = (datetime.now() - last_watered).days

    if days_since < days_between:
        return f"✅ Healthy (Water every {days_between} days)"
    elif days_since < days_between + 2:
        return f"💧 Needs water soon (Water every {days_between} days)"
    else:
        return f"🚨 Overdue: Water today! ({care['notes']})"

def care_info(plant):
    """
    Return detailed care info for a plant (light, humidity, notes)
    """
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
