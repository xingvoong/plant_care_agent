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


/addplant prayer_plant Maranta
/addplant pothos_Golden Pothos
/addplant golden_snake Golden Snake

/status
/care Maranta
/water "Golden Snake"


