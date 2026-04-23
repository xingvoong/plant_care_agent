# Phase 2: Plant Care Kubernetes Operator

## Step 1: Architecture + Big Picture

Before writing any code, you need to understand three concepts. Everything else builds on these.

---

### Concept 1: What is Kubernetes?

Kubernetes is a system that runs your code in containers and keeps it alive. You tell it what you want — "run my app, keep 3 copies running" — and it makes that happen. If a server crashes, Kubernetes restarts your app somewhere else automatically.

You talk to Kubernetes by writing YAML files and running `kubectl apply`. Kubernetes reads the file, figures out what needs to change, and makes it so.

---

### Concept 2: What is etcd?

Kubernetes needs to remember things — what apps are running, what their config is, what state they're in. It stores all of that in **etcd**, a database built into the cluster.

You never touch etcd directly. You talk to Kubernetes via `kubectl`, and Kubernetes talks to etcd. Think of etcd as Kubernetes' brain.

---

### Concept 3: What is a CRD?

Kubernetes ships with built-in resource types:

- `Pod` — a running container
- `Deployment` — a set of pods
- `Service` — a network endpoint

A **Custom Resource Definition (CRD)** lets you invent your own resource type. For this project, we define a `Plant` resource. Now instead of only having:

```bash
kubectl get pods
```

You can do:

```bash
kubectl get plants
```

Kubernetes stores `Plant` objects in etcd just like it does for Pods. You define what fields a `Plant` has — name, type, last watered date — and Kubernetes handles the storage and API.

---

### Concept 4: What is an operator?

Kubernetes has a built-in control loop for its own resources. When you say "I want 3 pods", something inside Kubernetes checks constantly:

> "Are there 3 pods running? No? Start one. Yes? Do nothing."

An **operator** is that same pattern, but for your custom resources. You write code that runs a loop:

1. Look at all `Plant` resources in the cluster
2. For each one, check if it's been watered recently
3. If overdue — send a Telegram reminder, update the plant's status in etcd

That loop runs forever. This is called the **reconcile loop**: observe → compare → act.

---

### How it all fits together

```
You write plant.yaml
        ↓
kubectl apply → Kubernetes stores Plant in etcd
                        ↓
           Operator sees the new Plant resource
                        ↓
           Operator checks: has it been watered?
                        ↓
         Overdue → send Telegram reminder
         Not overdue → do nothing
                        ↓
           Operator updates Plant status in etcd
                        ↓
           Web UI reads from etcd → shows you the plants
```

As a diagram:

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
│  │  plant.yaml  │                 │ Telegram Bot  │ │
│  │  (manifest)  │                 │  (reminder)   │ │
│  └─────────────┘                  └───────────────┘ │
│                                                      │
│  ┌──────────────────────────────────────────────┐   │
│  │              Web UI (dashboard)               │   │
│  │   shows all Plant resources + their status   │   │
│  └──────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────┘
```

---

---

## Step 2: Local K8s Cluster Setup

### What we built

A local Kubernetes cluster on macOS Monterey to run the plant care operator against.

---

### What we tried

Not everything worked. Here's the full picture:

```
                    ┌─────────────────────┐
                    │   Goal: K8s cluster  │
                    │   running locally    │
                    └──────────┬──────────┘
                               │
                    ┌──────────▼──────────┐
                    │    Docker Desktop    │
                    │    + kind            │
                    └──────────┬──────────┘
                               │
                          ✗ Docker Desktop
                            stopped opening
                               │
                    ┌──────────▼──────────┐
                    │       Colima         │
                    │   (needs qemu VM)    │
                    └──────────┬──────────┘
                               │
                          ✗ qemu formula broken
                            on Monterey (Tier 2)
                            brew install fails
                               │
                    ┌──────────▼──────────┐
                    │   Rancher Desktop    │
                    │  (bundles its own VM)│
                    └──────────┬──────────┘
                               │
                          ✓ works
```

---

### What Rancher Desktop gives you

Rancher Desktop ships with a full Kubernetes cluster (k3s) already running inside a Lima VM. No kind needed.

```
┌─────────────────────────────────────────────┐
│                 Your Mac                     │
│                                              │
│   kubectl ──────────────────────────────┐   │
│                                         │   │
│   ┌─────────────────────────────────┐   │   │
│   │         Lima VM                  │   │   │
│   │                                  │   │   │
│   │   ┌──────────────────────────┐   │   │   │
│   │   │   k3s (lightweight K8s)  │◄──┘   │   │
│   │   │                          │       │   │
│   │   │   - etcd                 │       │   │
│   │   │   - API server           │       │   │
│   │   │   - kubelet              │       │   │
│   │   │   - traefik (ingress)    │       │   │
│   │   └──────────────────────────┘       │   │
│   │                                      │   │
│   │   Docker socket (/Users/xingvoong/   │   │
│   │   .rd/docker.sock)                   │   │
│   └─────────────────────────────────────┘   │
└─────────────────────────────────────────────┘
```

---

### Verify the cluster

```bash
export DOCKER_HOST=unix://$HOME/.rd/docker.sock
kubectl config use-context rancher-desktop
kubectl get nodes
```

Expected output:
```
NAME                   STATUS   ROLES           AGE   VERSION
lima-rancher-desktop   Ready    control-plane   3m    v1.34.6+k3s1
```

---

### Takeaways

- macOS needs a Linux VM to run containers. Every tool (Docker Desktop, Colima, Rancher Desktop) is just a different way to manage that VM.
- Docker Desktop is not the only option. When it breaks, Rancher Desktop or Colima are solid replacements.
- Rancher Desktop bundles everything — VM, Kubernetes, Docker socket. Nothing to install separately.
- `kubectl` holds configs for multiple clusters. Always check your context with `kubectl config current-context` when connections fail.
- Environment setup is the hardest part of infrastructure work. The actual Kubernetes concepts are simpler than getting the tools running.

---

## Game plan

| Step | What | Status |
|------|------|--------|
| 1 | Architecture + big picture | done |
| 2 | Local K8s cluster setup with Rancher Desktop | done |
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
