# k8s_storage.py
# Drop-in replacement for storage.py that reads/writes Plant resources in Kubernetes.
# Provides the same load() / save() / today() interface so bot.py and brain.py
# need only a one-line import change.

import re
from datetime import datetime
from kubernetes import client, config
from kubernetes.client.exceptions import ApiException

GROUP = "care.example.com"
VERSION = "v1"
PLURAL = "plants"
NAMESPACE = "default"


def _load_k8s_config():
    try:
        config.load_incluster_config()
    except config.ConfigException:
        config.load_kube_config()


def _resource_name(owner_id, plant_name):
    """Derive a stable K8s resource name from owner + plant name."""
    slug = re.sub(r"[^a-z0-9-]", "-", plant_name.lower()).strip("-")
    owner_slug = re.sub(r"[^a-z0-9-]", "-", str(owner_id).lower()).strip("-")
    return f"{owner_slug}-{slug}"


def _item_to_plant(item):
    """Convert a K8s Plant resource to the flat dict shape agent.py expects."""
    spec = item.get("spec", {})
    status = item.get("status", {})
    return {
        "name": spec.get("plantName", ""),
        "type": spec.get("plantType", ""),
        "last_watered": spec.get("lastWatered", ""),
        "last_reminded": status.get("lastReminded", ""),
        "_resource_name": item["metadata"]["name"],
    }


def load():
    """
    Return all plants grouped by owner ID — same shape as storage.load():
      {"<user_id>": [{"name": ..., "type": ..., "last_watered": ...}, ...]}
    """
    _load_k8s_config()
    api = client.CustomObjectsApi()
    try:
        result = api.list_namespaced_custom_object(
            group=GROUP, version=VERSION, namespace=NAMESPACE, plural=PLURAL
        )
    except ApiException as e:
        print(f"[k8s_storage] load failed: {e}")
        return {}

    data = {}
    for item in result.get("items", []):
        owner_id = item.get("spec", {}).get("ownerID", "")
        plant = _item_to_plant(item)
        data.setdefault(owner_id, []).append(plant)
    return data


def save(data):
    """
    Persist plant dicts back to Kubernetes.
    Creates new Plant resources or patches existing ones.
    data shape: {"<user_id>": [plant_dicts]}
    """
    _load_k8s_config()
    api = client.CustomObjectsApi()

    for owner_id, plants in data.items():
        for plant in plants:
            rname = plant.get("_resource_name") or _resource_name(owner_id, plant["name"])
            spec = {
                "plantName": plant["name"],
                "plantType": plant["type"],
                "lastWatered": plant["last_watered"],
                "ownerID": str(owner_id),
            }
            try:
                api.patch_namespaced_custom_object(
                    group=GROUP, version=VERSION, namespace=NAMESPACE,
                    plural=PLURAL, name=rname, body={"spec": spec}
                )
            except ApiException as e:
                if e.status == 404:
                    # Resource doesn't exist yet — create it
                    body = {
                        "apiVersion": f"{GROUP}/{VERSION}",
                        "kind": "Plant",
                        "metadata": {"name": rname, "namespace": NAMESPACE},
                        "spec": spec,
                    }
                    try:
                        api.create_namespaced_custom_object(
                            group=GROUP, version=VERSION, namespace=NAMESPACE,
                            plural=PLURAL, body=body
                        )
                    except ApiException as ce:
                        print(f"[k8s_storage] create failed for {rname}: {ce}")
                else:
                    print(f"[k8s_storage] patch failed for {rname}: {e}")


def today():
    return datetime.now().strftime("%Y-%m-%d")
