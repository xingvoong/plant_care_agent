# rules.py

CARE_RULES = {
    "prayer plant": {
        "water_days": 8,
        "light": "Bright indirect light",
        "humidity": "Moderate to high",
        "notes": "Keep soil consistently moist but not soggy. Sensitive to over-/underwatering.",
        "soon_threshold": 2,
        "overdue_threshold": 4
    },
    "pothos": {
        "water_days": 12,
        "light": "Bright indirect to low light",
        "humidity": "Medium",
        "notes": "Let top 50–75% of soil dry between waterings. Adapts to many indoor conditions.",
        "soon_threshold": 2,
        "overdue_threshold": 4
    },
    "golden snake": {
        "water_days": 21,
        "light": "Low to bright indirect light",
        "humidity": "Low to medium",
        "notes": "Drought-tolerant; water only after soil dries completely. Avoid overwatering.",
        "soon_threshold": 3,
        "overdue_threshold": 5
    }
}
