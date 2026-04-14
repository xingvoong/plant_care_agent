# storage.py
import json
from datetime import datetime

FILE = "plants.json"

def load():
    try:
        with open(FILE) as f:
            return json.load(f)
    except FileNotFoundError:
        return {}

def save(data):
    with open(FILE, "w") as f:
        json.dump(data, f, indent=2)

def today():
    return datetime.now().strftime("%Y-%m-%d")
