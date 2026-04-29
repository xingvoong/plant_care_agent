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

## Demo

[![Plant Care Agent Demo](https://img.youtube.com/vi/uITz0FG0pEc/0.jpg)](https://youtu.be/uITz0FG0pEc)

## What is the Bot vs the Agent?

**Bot** (`bot.py`) is the interface layer — it listens for messages on Telegram, understands what the user wants (watering a plant, adding a plant, asking a question), and sends back a reply. Without the bot, there's no way to interact with the system.

**Agent** (`agent.py` + `brain.py`) is the reasoning layer — it looks at each plant's data, applies care rules, and decides what action to take (e.g. "this plant is overdue for water"). The agent doesn't talk to users directly; it produces decisions that the bot acts on.

In short: the **bot talks**, the **agent thinks**.

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

## Phase 2: Kubernetes Operator

The next phase moves the plant care agent into Kubernetes — turning plants into native cluster resources, managed by an operator.

### Architecture

```
┌─────────────────────────────────────────────────────┐
│                  Kubernetes Cluster                  │
│                                                      │
│  ┌─────────────┐     watches      ┌───────────────┐ │
│  │   Plant CRD  │◄────────────────│   Operator    │ │
│  │  (etcd)      │                 │  (your code)  │ │
│  └─────────────┘                  └───────┬───────┘ │
│         ▲                                 │         │
│         │ kubectl apply                   │ reconcile│
│         │                                 ▼         │
│  ┌──────┴──────┐                  ┌───────────────┐ │
│  │  plant.yaml  │                 │  Telegram Bot  │ │
│  │  (manifest)  │                 │  (reminder)   │ │
│  └─────────────┘                  └───────────────┘ │
│                                                      │
│  ┌──────────────────────────────────────────────┐   │
│  │              Web UI (dashboard)               │   │
│  │   shows all Plant resources + their status   │   │
│  └──────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────┘
```

### How it works

1. Add a plant through the web dashboard — no YAML or `kubectl` needed
2. The dashboard calls the Kubernetes API directly, storing the plant as a `Plant` custom resource in etcd
3. The operator watches for `Plant` resources — when one is created or updated, it runs the reconcile loop
4. The reconcile loop checks if a plant is overdue for watering and acts (updates status, sends Telegram reminder)
5. The web dashboard reads from the K8s API and shows all plants with their current condition

### Build plan

| Step | What we build |
|------|--------------|
| 1 | Architecture + big picture |
| 2 | Local K8s cluster setup (kind) |
| 3 | Define the CRDs (Plant as a K8s resource) |
| 4 | Build the operator (reconcile loop with kopf) |
| 5 | RBAC + cluster management configs |
| 6 | Web UI dashboard |
| 7 | Deploy + test everything end to end |

### Engineering areas

This project covers three areas:

**Platform / Infrastructure Engineering**
- Kubernetes CRDs, operators, RBAC, etcd as a state store
- The operator pattern is how production platforms (Datadog, Elastic, Postgres) manage stateful workloads on K8s

**Backend Engineering**
- Telegram bot with a perceive-think-act agent loop
- Flask API serving the web dashboard
- LLM integration via MiniMax for free-text plant advice

**ML Engineering (serving patterns)**
- Event-driven inference: the reconcile loop fires on data change, not on a cron
- The agent loop mirrors how deployed models observe state, run inference, and act
- No training pipeline — this is the serving and infrastructure side only

---

## Areas to improve

- **Reminders** — proactively send a daily message when a plant is overdue for watering, without the user having to ask
- **More plant types** — expand `rules.py` with more species beyond the current three
- **Remove a plant** — let users say "remove my Maranta" to delete a plant from their list
- **Multi-language support** — respond in the user's language
- **Web dashboard** — a simple UI to view and manage plants outside of Telegram

## Running locally

**Requirements:**
- Python 3.10+
- A Telegram bot token — create one via [@BotFather](https://t.me/BotFather) on Telegram
- An OpenRouter API key — sign up free at [openrouter.ai](https://openrouter.ai)

**Steps:**

```bash
# 1. Clone the repo
git clone https://github.com/xingvoong/plant_care_agent.git
cd plant_care_agent

# 2. Install dependencies
pip install requests

# 3. Set up environment variables
cp .env.example .env
# Edit .env and fill in BOT_TOKEN and OPENROUTER_API_KEY

# 4. Run the bot
source .env && python bot.py
```

## Environment variables

| Variable | Description |
|---|---|
| `BOT_TOKEN` | Telegram bot token from @BotFather |
| `OPENROUTER_API_KEY` | API key from openrouter.ai |
