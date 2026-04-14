# Plant Care Agent

The goal of this project is to create a plant care agent — a Telegram bot that helps you track and care for your houseplants using natural language, backed by an AI model (MiniMax via OpenRouter).

## How to use on Telegram

1. Open Telegram and search for **@plant_care_helper_bot**
2. Tap **Start**
3. Type anything in plain English — no commands needed

## How it works

Talk to the bot in plain English:

- `"how are my plants?"` — get a status summary
- `"I watered my Maranta"` — logs the watering
- `"I got a new pothos called Pearl"` — adds the plant
- `"why are my pothos leaves yellowing?"` — AI-powered advice

## Architecture

```
┌────────────────────────────┐
│        Telegram API        │
│  (getUpdates / sendMessage)│
└─────────────┬──────────────┘
              │ HTTP (polling)
┌─────────────▼──────────────┐
│           bot.py           │
│  - Polls Telegram          │
│  - Detects intent          │
│  - Executes actions        │
└─────────────┬──────────────┘
         ┌────┴────┐
┌────────▼───┐ ┌───▼──────┐
│  agent.py  │ │  llm.py  │
│  - Status  │ │ MiniMax  │
│  - Rules   │ │ OpenRouter│
└────────────┘ └──────────┘
              │
┌─────────────▼──────────────┐
│        storage.py          │
│  - plants.json persistence │
└────────────────────────────┘
```

## Setup

```bash
cp .env.example .env  # fill in your keys
source .env && python bot.py
```

## Environment variables

| Variable | Description |
|---|---|
| `BOT_TOKEN` | Telegram bot token from @BotFather |
| `OPENROUTER_API_KEY` | API key from openrouter.ai |
