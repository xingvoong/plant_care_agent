# brain.py
import time
from storage import load, save, today
from agent import decide, next_action

class PlantAgent:

    def __init__(self):
        self.goal = "Keep all plants healthy"
        self.last_scan = 0
        self.scan_interval = 3  # seconds (testing)

    def perceive(self):
        """Read world state"""
        return load()

    def think(self, data):
        """Analyze plant conditions, skip plants already reminded today"""
        actions = []
        for user, plants in data.items():
            for plant in plants:
                if plant.get("last_reminded") == today():
                    continue
                action = next_action(plant)
                if action:
                    actions.append((user, plant["name"], action))
        return actions

    def act(self, actions, send_function):
        """Execute actions and mark plants as reminded today"""
        if not actions:
            return
        data = load()
        for user, plant_name, message in actions:
            print(f"[AGENT ACTION] Sending to {user}: {message}")
            send_function(int(user), message)
            for plant in data.get(user, []):
                if plant["name"] == plant_name:
                    plant["last_reminded"] = today()
        save(data)

    def should_scan(self):
        return time.time() - self.last_scan >= self.scan_interval

    def update_scan_time(self):
        self.last_scan = time.time()
