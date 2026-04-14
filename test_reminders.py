# test_reminders.py
import time
from storage import load
from agent import next_action
from bot import send  # reuse your send() function

while True:
    data = load()
    for user, plants in data.items():
        reminders = []
        for p in plants:
            msg = next_action(p)
            if msg:
                reminders.append(msg)
        if reminders:
            print(f"Sending reminders to {user}: {reminders}")
            send(int(user), "\n".join(reminders))
    time.sleep(3)
