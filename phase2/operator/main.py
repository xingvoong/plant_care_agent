# main.py
# kopf operator entry point for the Plant Care operator.
#
# Usage:
#   export BOT_TOKEN=<your_telegram_bot_token>
#   kopf run main.py --verbose
#
# Handles:
#   - Plant created  → reconcile immediately
#   - Plant updated  → reconcile on spec change
#   - Timer          → reconcile every 12 hours to catch plants that go overdue
#                      without a spec update

import kopf
from datetime import date
from reconciler import reconcile, send_telegram


def _run_reconcile(spec, patch, reason):
    today_str = date.today().isoformat()
    status_patch, should_remind = reconcile(spec, today_str)

    patch.status.update(status_patch)

    if should_remind:
        send_telegram(
            owner_id=spec["ownerID"],
            plant_name=spec["plantName"],
            message=status_patch["message"],
        )

    print(f"[main] reconciled ({reason}): {spec['plantName']} → {status_patch['condition']}")


@kopf.on.create("care.example.com", "v1", "plants")
def on_create(spec, patch, **kwargs):
    _run_reconcile(spec, patch, reason="create")


@kopf.on.update("care.example.com", "v1", "plants", field="spec")
def on_update(spec, patch, **kwargs):
    _run_reconcile(spec, patch, reason="update")


@kopf.timer("care.example.com", "v1", "plants", interval=43200)  # 12 hours
def on_timer(spec, patch, **kwargs):
    _run_reconcile(spec, patch, reason="timer")
