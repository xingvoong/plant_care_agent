def get_plant_knowledge(plant_type):
    """
    Dynamic knowledge resolver.
    Can be replaced with live API calls.
    """
    profiles = {
        "snake plant": {
            "water_days": 14,
            "humidity": False
        },
        "pothos": {
            "water_days": 7,
            "humidity": False
        },
        "prayer plant": {
            "water_days": 4,
            "humidity": True
        }
    }

    return profiles.get(plant_type)
