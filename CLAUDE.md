# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Running the bot

```bash
export BOT_TOKEN=<your_telegram_bot_token>
export MINIMAX_API_KEY=<your_minimax_api_key>
export MINIMAX_GROUP_ID=<your_minimax_group_id>
source venv/bin/activate
python bot.py
```

`BOT_TOKEN` is required (raises `RuntimeError` on startup if missing). `MINIMAX_API_KEY` and `MINIMAX_GROUP_ID` are optional — free-text messages will return a config error message to the user if unset.

## Installing dependencies

```bash
pip install requests
# or restore from requirements.txt (note: requirements.txt lists aiogram but the codebase uses requests directly)
```

## Manual reminder test script

```bash
python test_reminders.py  # polls every 3s, sends reminders to all users with overdue plants
```

## Architecture

The system follows a perceive-think-act agent loop integrated with a Telegram polling loop.

**Data flow:**
- `plants.json` — persistent store, keyed by Telegram user ID (`{"<user_id>": [plant_objects]}`)
- `storage.py` — thin I/O wrapper (`load`, `save`, `today`)
- `rules.py` — static `CARE_RULES` dict defining watering frequency, light, humidity, and thresholds per plant type
- `agent.py` — pure logic functions (`decide`, `care_info`, `next_action`) that evaluate a single plant against CARE_RULES
- `brain.py` — `PlantAgent` class: `perceive()` loads all plants, `think()` calls `next_action` per plant, `act()` fires Telegram messages for any that need attention
- `bot.py` — main entry point: Telegram long-poll loop handling `/addplant`, `/water`, `/status`, `/care` commands + runs `PlantAgent` cycle every `scan_interval` seconds (currently 3s)

**Adding a new plant type:** add an entry to `CARE_RULES` in `rules.py`. The keys `water_days`, `light`, `humidity`, `notes`, `soon_threshold`, and `overdue_threshold` are all used by `agent.decide()`.

`llm.py` — wraps the MiniMax `minimax-m2-7` chat API; called by `bot.py` for any free-text message (non-command). Passes the user's plant list as context so MiniMax can give personalized advice.

`knowledge.py` is an older/alternate plant profiles module (not imported by current code) with simpler profiles — it was a precursor to `rules.py` and is intended to eventually be replaced by live API calls.

**Agent scan interval:** `PlantAgent.scan_interval` in `brain.py` (default 3 seconds for testing).
