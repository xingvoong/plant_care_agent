# plant_care_agent

- make a MVP version of the bot/agent that connect with telegram

┌────────────────────────────┐
│        Telegram API        │
│  (getUpdates / sendMessage)│
└─────────────┬──────────────┘
              │ HTTP (polling)
┌─────────────▼──────────────┐
│           bot.py           │
│  - Polls Telegram          │
│  - Parses commands         │
│  - Sends responses         │
└─────────────┬──────────────┘
              │ function calls
┌─────────────▼──────────────┐
│          agent.py          │
│  - Makes care decisions    │
└─────────────┬──────────────┘
              │ reads
┌─────────────▼──────────────┐
│          rules.py          │
│  - Static care intervals   │
└─────────────┬──────────────┘
              │ reads/writes
┌─────────────▼──────────────┐
│        storage.py          │
│  - JSON persistence        │
└────────────────────────────┘


Data Model:

"user_id": [ Plant, Plant ]

{
  "name": "Living Room",
  "type": "pothos",
  "last_watered": "2026-02-09"
}




