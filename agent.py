from datetime import datetime
from rules import CARE_RULES

def decide(plant):
    days_between = CARE_RULES.get(plant["type"])

    if not days_between:
        return "🤔 No care info available"

    last_watered = datetime.strptime(plant["last_watered"], "%Y-%m-%d")
    days_since = (datetime.now() - last_watered).days

    if days_since >= days_between:
        if plant["type"] == "prayer plant":
            return "💧 Light watering + increase humidity"
        return "💧 Water today"

    return "✅ No action needed"
