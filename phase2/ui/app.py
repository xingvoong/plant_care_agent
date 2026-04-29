# app.py
# Flask web dashboard for the Plant Care operator.
# Reads Plant resources from the Kubernetes cluster via the K8s API.
#
# Usage:
#   pip install flask kubernetes
#   python app.py
#
# Requires a valid kubeconfig (~/.kube/config) or runs in-cluster if deployed as a Pod.
# The Plant CRD and at least one Plant resource must exist in the cluster.

from flask import Flask, render_template, request, redirect, url_for, flash
from kubernetes import client, config
from kubernetes.client.exceptions import ApiException
import os
import re

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "dev-secret-change-in-prod")

PLANT_TYPES = ["prayer plant", "pothos", "golden snake"]

GROUP = "care.example.com"
VERSION = "v1"
PLURAL = "plants"
NAMESPACE = os.getenv("PLANT_NAMESPACE", "default")


def load_k8s_config():
    """Load kubeconfig from file (local dev) or in-cluster service account (Pod)."""
    try:
        config.load_incluster_config()
    except config.ConfigException:
        config.load_kube_config()


def get_plants():
    """
    Fetch all Plant resources from the cluster.
    Returns a list of dicts with flattened spec + status fields.
    """
    load_k8s_config()
    api = client.CustomObjectsApi()

    try:
        result = api.list_namespaced_custom_object(
            group=GROUP,
            version=VERSION,
            namespace=NAMESPACE,
            plural=PLURAL,
        )
    except ApiException as e:
        print(f"[app] K8s API error: {e}")
        return [], str(e)

    plants = []
    for item in result.get("items", []):
        spec = item.get("spec", {})
        status = item.get("status", {})
        metadata = item.get("metadata", {})

        condition = status.get("condition", "unknown")
        plants.append({
            "resource_name": metadata.get("name", ""),
            "plant_name": spec.get("plantName", ""),
            "plant_type": spec.get("plantType", ""),
            "last_watered": spec.get("lastWatered", ""),
            "owner_id": spec.get("ownerID", ""),
            "condition": condition,
            "message": status.get("message", ""),
            "last_reminded": status.get("lastReminded", ""),
            "condition_class": condition_css_class(condition),
        })

    plants.sort(key=lambda p: condition_sort_order(p["condition"]))
    return plants, None


def condition_css_class(condition):
    return {
        "overdue": "overdue",
        "needsWaterSoon": "soon",
        "healthy": "healthy",
    }.get(condition, "unknown")


def condition_sort_order(condition):
    """Overdue first, then soon, then healthy."""
    return {"overdue": 0, "needsWaterSoon": 1, "healthy": 2}.get(condition, 3)


@app.route("/")
def index():
    plants, error = get_plants()
    counts = {
        "total": len(plants),
        "overdue": sum(1 for p in plants if p["condition"] == "overdue"),
        "soon": sum(1 for p in plants if p["condition"] == "needsWaterSoon"),
        "healthy": sum(1 for p in plants if p["condition"] == "healthy"),
    }
    return render_template("index.html", plants=plants, counts=counts, error=error,
                           plant_types=PLANT_TYPES)


@app.route("/add", methods=["POST"])
def add_plant():
    plant_name = request.form.get("plantName", "").strip()
    plant_type = request.form.get("plantType", "").strip()
    last_watered = request.form.get("lastWatered", "").strip()
    owner_id = request.form.get("ownerID", "").strip()

    if not all([plant_name, plant_type, last_watered, owner_id]):
        flash("All fields are required.", "error")
        return redirect(url_for("index"))

    if plant_type not in PLANT_TYPES:
        flash(f"Invalid plant type: {plant_type}", "error")
        return redirect(url_for("index"))

    # Derive a valid K8s resource name from the plant name
    resource_name = re.sub(r"[^a-z0-9-]", "-", plant_name.lower()).strip("-")

    body = {
        "apiVersion": f"{GROUP}/{VERSION}",
        "kind": "Plant",
        "metadata": {"name": resource_name, "namespace": NAMESPACE},
        "spec": {
            "plantName": plant_name,
            "plantType": plant_type,
            "lastWatered": last_watered,
            "ownerID": owner_id,
        },
    }

    load_k8s_config()
    api = client.CustomObjectsApi()

    try:
        api.create_namespaced_custom_object(
            group=GROUP, version=VERSION, namespace=NAMESPACE, plural=PLURAL, body=body
        )
        flash(f"{plant_name} added successfully.", "success")
    except ApiException as e:
        flash(f"Failed to add plant: {e.reason}", "error")

    return redirect(url_for("index"))


@app.route("/water/<resource_name>", methods=["POST"])
def water_plant(resource_name):
    from datetime import date
    today = date.today().isoformat()

    load_k8s_config()
    api = client.CustomObjectsApi()

    try:
        api.patch_namespaced_custom_object(
            group=GROUP,
            version=VERSION,
            namespace=NAMESPACE,
            plural=PLURAL,
            name=resource_name,
            body={"spec": {"lastWatered": today}},
        )
        flash(f"Watered! Last watered set to {today}.", "success")
    except ApiException as e:
        flash(f"Failed to water plant: {e.reason}", "error")

    return redirect(url_for("index"))


if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)
