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
- `"add avocado, name bonsai"` — adds any plant type, not just known ones
- `"why are my pothos leaves yellowing?"` — AI-powered advice

Any plant type works. Known types (prayer plant, pothos, golden snake) use built-in care rules. Unknown types fetch care rules from MiniMax automatically.

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
└─────────────┬──────────────┘
              │ HTTP (polling)
┌─────────────▼──────────────┐
│           bot.py           │
│  intent detection          │
└──────┬──────────────┬───────┘
       │              │
┌──────▼─────┐  ┌─────▼──────┐
│  agent.py  │  │   llm.py   │
│  rules.py  │  │  MiniMax   │
└──────┬─────┘  └────────────┘
       │
┌──────▼──────────────────────┐
│       k8s_storage.py        │
│  Kubernetes API → etcd      │
└─────────────────────────────┘
```

## Phase 2: Kubernetes Operator

Plants are stored as Kubernetes custom resources in etcd. The operator watches for changes, reconciles conditions, and sends Telegram reminders. Both the Telegram bot and the web dashboard read and write the same data.

See [phase2/README.md](phase2/README.md) for the full build log.

---

## Wrap-up

This project started as a Telegram bot backed by a JSON file. It ended as a full Kubernetes-native system with an operator, a web dashboard, RBAC, and a single source of truth in etcd. Both Telegram and the dashboard read and write the same data.

**What it achieves:**
- A working plant care system you can actually use — add plants, log waterings, get reminders, ask questions in natural language
- Any plant type is supported. Known types use static care rules. Unknown types fetch rules from MiniMax on demand.
- State is stored in Kubernetes etcd — versioned, auditable, and accessible via `kubectl get plants`
- The operator runs a reconcile loop continuously, updating conditions and firing Telegram reminders without any user action

**Engineering areas covered:**

*Platform / Infrastructure*
- Custom Resource Definitions — extending Kubernetes with a `Plant` resource type
- Kubernetes operator pattern with kopf — event-driven reconcile loop
- RBAC — ServiceAccount, ClusterRole, ClusterRoleBinding with least-privilege permissions
- Kubernetes-native state management — etcd as the single source of truth

*Backend*
- Telegram bot with natural language intent detection
- Perceive-think-act agent loop
- Flask web dashboard with live reads and writes to the Kubernetes API
- LLM integration via MiniMax/OpenRouter for free-text advice and dynamic care rule lookup

*ML Engineering (serving side)*
- Event-driven inference — the reconcile loop fires on data change, not a timer
- Rules-based inference with LLM fallback for unknown inputs
- The agent loop is the same pattern as a deployed ML model: observe state, run inference, act

**Key takeaway:** The operator pattern isn't just for databases and message queues. Any stateful background process — monitoring, scheduling, inference — can be modeled as a reconcile loop. You observe desired state, compare to actual state, and act. That's what this project does, with plants.

---

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
