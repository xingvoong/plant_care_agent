# Phase 2: Plant Care Kubernetes Operator

A Kubernetes operator that manages houseplants as native cluster resources.

## What we're building

Instead of storing plants in `plants.json`, plants live as Kubernetes custom resources in etcd. An operator watches them, checks watering schedules, and fires Telegram reminders. A web dashboard shows all plants and their status in real time.

## Architecture

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

## Game plan

| Step | What | Status |
|------|------|--------|
| 1 | Architecture + big picture | done |
| 2 | Local K8s cluster setup with `kind` | todo |
| 3 | Define the `Plant` CRD with schema validation | todo |
| 4 | Build the operator with `kopf` (reconcile loop) | todo |
| 5 | RBAC — ServiceAccount, Role, RoleBinding | todo |
| 6 | Web UI dashboard | todo |
| 7 | Deploy + test everything end to end | todo |

## Planned file structure

```
phase2/
  crds/
    plant.yaml              # Plant custom resource definition
    plantschedule.yaml      # PlantCareSchedule CRD
  operator/
    main.py                 # kopf operator entry point
    reconciler.py           # reconcile logic (ports agent.py)
  rbac/
    serviceaccount.yaml
    role.yaml
    rolebinding.yaml
  deploy/
    operator.yaml           # operator Deployment manifest
  ui/
    app.py                  # web dashboard (Flask)
    templates/
      index.html
  cluster/
    kind-config.yaml        # local cluster config
```

## Why this matters

- `kubectl get plants` — plants are first-class K8s objects
- State is versioned and auditable in etcd
- Operator pattern is how production platforms (Datadog, Elastic, Postgres) automate stateful workloads
- Demonstrates CRDs, operators, RBAC, and cluster management in a real domain
