# Plant Care Agent

A Telegram bot that tracks and cares for your houseplants using natural language, backed by MiniMax via OpenRouter. Plant state lives in Kubernetes etcd — the bot, operator, and web dashboard all share the same data.

## Usage

Search for **@plant_care_helper_bot** on Telegram and start chatting:

```
"how are my plants?"              → status summary
"I watered my Maranta"            → logs the watering
"add monstera, name Pearl"        → adds any plant type
"why are my pothos leaves yellow?" → AI-powered advice
```

Any plant type works. Known types (prayer plant, pothos, golden snake) use built-in care rules. Unknown types fetch rules from MiniMax automatically.

## Architecture

```
┌────────────────────────────┐
│        Telegram API        │
└─────────────┬──────────────┘
              │
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

**bot.py** — polls Telegram, detects intent, executes actions

**agent.py + rules.py** — applies care rules, computes watering conditions

**llm.py** — asks MiniMax for advice and care rules for unknown plant types

**k8s_storage.py** — reads/writes Plant resources in Kubernetes instead of a local file

## Phase 2: Kubernetes Operator

Plants are stored as Kubernetes custom resources. The operator reconciles conditions and sends Telegram reminders. The web dashboard lets you add plants and log waterings without using `kubectl`.

See [phase2/README.md](phase2/README.md) for setup, deployment, and teardown.

## Wrap-up

Started as a Telegram bot backed by a JSON file. Ended as a Kubernetes-native system with a CRD, reconcile loop operator, RBAC, web dashboard, and a single source of truth in etcd.

**Engineering areas:**

*Platform / Infrastructure* — CRDs, Kubernetes operator pattern with kopf, RBAC with least-privilege permissions, etcd as state store

*Backend* — Telegram bot with natural language intent detection, perceive-think-act agent loop, Flask dashboard with live K8s API reads and writes

*ML Engineering (serving)* — event-driven inference, rules-based reasoning with LLM fallback, same observe-infer-act pattern as a deployed model

The operator pattern applies beyond infrastructure. Any background process that watches state and acts on it — monitoring, scheduling, inference — is a reconcile loop.

## Running locally

```bash
git clone https://github.com/xingvoong/plant_care_agent.git
cd plant_care_agent
pip install requests kubernetes flask
cp .env.example .env   # fill in BOT_TOKEN and OPENROUTER_API_KEY
source .env && python bot.py
```

Requires a running Kubernetes cluster with the Plant CRD applied. See [phase2/README.md](phase2/README.md).

## Environment variables

| Variable | Description |
|---|---|
| `BOT_TOKEN` | Telegram bot token from @BotFather |
| `OPENROUTER_API_KEY` | API key from openrouter.ai (used for MiniMax) |

## Demo

[![Plant Care Agent Demo](https://img.youtube.com/vi/uITz0FG0pEc/0.jpg)](https://youtu.be/uITz0FG0pEc)
