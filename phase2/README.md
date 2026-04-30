# Phase 2: Plant Care Kubernetes Operator

## Architecture

Plants are stored as Kubernetes custom resources in etcd. The operator watches for changes and reconciles — checking watering status, updating conditions, sending Telegram reminders. The web dashboard and Telegram bot both read and write the same data.

```
┌─────────────────────────────────────────────────────┐
│                  Kubernetes Cluster                  │
│                                                      │
│  ┌─────────────┐     watches      ┌───────────────┐ │
│  │   Plant CRD  │◄────────────────│   Operator    │ │
│  │  (etcd)      │                 │  (kopf)       │ │
│  └─────────────┘                  └───────┬───────┘ │
│         ▲                                 │         │
│         │ Telegram / Dashboard            │ reconcile│
│         │                                 ▼         │
│  ┌──────┴──────┐                  ┌───────────────┐ │
│  │  k8s_storage │                 │ Telegram Bot  │ │
│  │  + UI form   │                 │  (reminder)   │ │
│  └─────────────┘                  └───────────────┘ │
│                                                      │
│  ┌──────────────────────────────────────────────┐   │
│  │              Web UI (dashboard)               │   │
│  └──────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────┘
```

---

## File structure

```
phase2/
  crds/
    plant.yaml              # Plant CRD schema
    sample-plant.yaml       # example Plant resource
  operator/
    main.py                 # kopf entry point
    reconciler.py           # reconcile logic
    Dockerfile
  ui/
    app.py                  # Flask dashboard
    templates/index.html
    Dockerfile
  rbac/
    serviceaccount.yaml
    role.yaml
    rolebinding.yaml
  deploy/
    operator.yaml           # operator Deployment
    ui.yaml                 # UI Deployment + NodePort Service
```

---

## Step 1: Key Concepts

**Kubernetes** — runs containers and keeps them alive. You declare what you want in YAML, apply it with `kubectl`, and Kubernetes makes it happen.

**etcd** — Kubernetes' built-in database. All resource state lives here. You never touch it directly — `kubectl` and the API server are the interface.

**CRD (Custom Resource Definition)** — extends Kubernetes with your own resource type. This project defines a `Plant` resource so you can run `kubectl get plants`.

**Operator** — a process that runs a reconcile loop against your custom resources: observe state → compare → act. kopf is the Python library that handles the wiring.

**spec vs status** — `spec` is desired state (you write it). `status` is observed state (the operator writes it). They never cross.

```
You (Telegram / Dashboard)          Operator (kopf)
──────────────────────────          ───────────────
writes spec:                        writes status:
  plantName                           condition
  plantType                           lastReminded
  lastWatered                         message
  ownerID
```

The reconcile loop:

```
Plant created or updated in etcd
          │
          ▼
  kopf fires handler
          │
          ▼
  read spec → agent.decide() → compute condition
          │
          ▼
  patch status → send Telegram if overdue
          │
          ▼
  wait for next change
```

---

## Step 2: Local Cluster Setup

Uses **Rancher Desktop** — bundles a Lima VM, k3s (lightweight Kubernetes), and a Docker socket. Nothing to install separately.

```
┌─────────────────────────────────────────────┐
│                 Your Mac                     │
│                                              │
│   kubectl / docker                           │
│        │                                     │
│   ┌────▼────────────────────────────────┐   │
│   │         Lima VM                      │   │
│   │   ┌──────────────────────────────┐   │   │
│   │   │   k3s (lightweight K8s)      │   │   │
│   │   │   etcd · API server          │   │   │
│   │   │   kubelet · cri-dockerd      │   │   │
│   │   └──────────────────────────────┘   │   │
│   └─────────────────────────────────────┘   │
└─────────────────────────────────────────────┘
```

```bash
kubectl config use-context rancher-desktop
kubectl get nodes
# NAME                   STATUS   ROLES           AGE
# lima-rancher-desktop   Ready    control-plane   3m
```

Rancher Desktop uses `cri-dockerd` — k3s delegates image management to Docker. Build images with `docker build` and they're immediately available to k3s.

---

## Step 3: Plant CRD

The CRD defines the `Plant` schema. Kubernetes validates every resource against it on write.

```
  ┌─────────────────────────────────────────────────┐
  │                  Plant Resource                  │
  │                                                  │
  │   spec/               │   status/                │
  │   ─────────────────   │   ─────────────────────  │
  │   plantName           │   condition              │
  │   plantType           │   lastReminded           │
  │   lastWatered         │   message                │
  │   ownerID             │                          │
  │                       │                          │
  │   ← you write this    │   ← operator writes this │
  └─────────────────────────────────────────────────┘
```

**Schema:**

```
Plant
├── spec/                    ← you write this
│   ├── plantName  string    required — display name
│   ├── plantType  string    required — any plant type
│   ├── lastWatered date     required — YYYY-MM-DD
│   └── ownerID   string     required — Telegram user ID
│
└── status/                  ← operator writes this
    ├── condition  string     "healthy" | "needsWaterSoon" | "overdue"
    ├── lastReminded date     last reminder sent
    └── message   string      human-readable status
```

**Apply:**

```bash
kubectl apply -f phase2/crds/plant.yaml
kubectl apply -f phase2/crds/sample-plant.yaml
kubectl get plants
```

---

## Step 4: Operator

The operator watches Plant resources and reconciles on every create/update. A 12-hour timer catches plants that go overdue without a spec change.

```
┌──────────────────────────────────────────────────────┐
│                   Operator Process                    │
│                                                      │
│  kopf watches K8s API → event fires → handler()     │
│                                           │          │
│                               ┌───────────▼────────┐ │
│                               │  1. read spec       │ │
│                               │  2. agent.decide()  │ │
│                               │  3. patch status    │ │
│                               │  4. send reminder   │ │
│                               └────────────────────┘ │
└──────────────────────────────────────────────────────┘
```

**Reconcile loop:**
1. Read `spec.plantType` and `spec.lastWatered`
2. Compute condition via `agent.decide()`
3. Patch `status.condition`, `status.message`, `status.lastReminded`
4. Send Telegram reminder if overdue or soon

**Run locally:**

```bash
cd phase2/operator
pip install kopf kubernetes requests
kubectl apply -f ../crds/plant.yaml
kopf run main.py --verbose
```

---

## Step 5: RBAC

Three objects give the operator and UI the permissions they need.

```
┌──────────────────────┐          ┌────────────────────────────┐
│    ServiceAccount    │          │        ClusterRole          │
│   plant-operator     │          │   plant-operator-role       │
│   namespace: default │          │                             │
│                      │          │   plants      → get,list,   │
│   identity the       │          │                watch,patch, │
│   Pod runs as        │          │                update,create│
└──────────┬───────────┘          │   plants/status → patch     │
           │                      │   CRDs          → get,list  │
           │                      │   events        → create    │
           │                      │   leases        → get,create│
           │                      └──────────────┬─────────────┘
           │                                     │
           └──────────────┬──────────────────────┘
                          │
             ┌────────────▼────────────┐
             │    ClusterRoleBinding    │
             │  plant-operator-        │
             │  rolebinding            │
             │                         │
             │  connects identity      │
             │  to permissions         │
             └─────────────────────────┘
```

| Object | Name | Purpose |
|--------|------|---------|
| ServiceAccount | `plant-operator` | identity Pods run as |
| ClusterRole | `plant-operator-role` | permission set |
| ClusterRoleBinding | `plant-operator-rolebinding` | connects the two |

**Permissions:**

```
Resource                    Verbs                    Why
──────────────────────────  ───────────────────────  ──────────────────────────────
plants                      get, list, watch,        read + write Plant objects
                            patch, update, create
plants/status               get, patch, update       write condition/message
customresourcedefinitions   get, list, watch         kopf reads schema on startup
events                      create, patch, update    kopf posts reconcile events
leases                      get, create, update      kopf leader election
```

ClusterRole is used (not Role) because CRDs and Leases are cluster-scoped resources.

**Apply:**

```bash
kubectl apply -f phase2/rbac/serviceaccount.yaml
kubectl apply -f phase2/rbac/role.yaml
kubectl apply -f phase2/rbac/rolebinding.yaml
```

**Verify:**

```bash
kubectl auth can-i watch plants --as=system:serviceaccount:default:plant-operator
# yes
kubectl auth can-i delete plants --as=system:serviceaccount:default:plant-operator
# no
```

---

## Step 6: Web UI Dashboard

Flask app that reads and writes Plant resources via the Kubernetes API. No separate database — every page load hits etcd directly.

```
┌──────────────────────────────────────────────────────────────┐
│                  Plant Care Dashboard                         │
│                                                              │
│  [ Plant Name ] [ Type ▼ ] [ Last Watered ] [ Owner ID ]    │
│  [ Add ]                                                     │
│                                                              │
│  ┌──────┐  ┌─────────┐  ┌────────────┐  ┌─────────┐        │
│  │  3   │  │    1    │  │     1      │  │    1    │        │
│  │Total │  │ Overdue │  │ Water Soon │  │ Healthy │        │
│  └──────┘  └─────────┘  └────────────┘  └─────────┘        │
│                                                              │
│  Plant     Type          Last Watered  Condition    Action  │
│  ──────────────────────────────────────────────────────     │
│  Maranta   prayer plant  2026-04-14    OVERDUE    [Water]   │
│  Pothos    pothos        2026-04-20    SOON       [Water]   │
│  Snake     golden snake  2026-04-29    HEALTHY    [Water]   │
└──────────────────────────────────────────────────────────────┘
```

**Features:**
- Add plant form (name, type, last watered, owner ID)
- Water button per row — patches `spec.lastWatered` to today
- Summary bar (total / overdue / soon / healthy)
- Rows sorted by urgency, color-coded by condition

**Run locally:**

```bash
cd phase2/ui
pip install flask kubernetes
python app.py
# open http://localhost:5000
```

**Development tip:** run locally (`localhost:5000`) for fast iteration — Flask auto-reloads on file changes. Deploy to the cluster (`localhost:30080`) only to verify the final image.

---

## Step 7: Deploy

```
┌─────────────────────────────────────────────────┐
│               Kubernetes Cluster                 │
│                                                  │
│  ┌──────────────────────┐                        │
│  │   plant-operator Pod │  watches Plant CRD     │
│  │   SA: plant-operator │  patches status        │
│  └──────────────────────┘  sends Telegram        │
│                                                  │
│  ┌──────────────────────┐                        │
│  │   plant-ui Pod        │  reads/creates Plants  │
│  │   SA: plant-operator │                        │
│  └──────────┬───────────┘                        │
│             │ NodePort :30080                    │
└─────────────┼──────────────────────────────────-─┘
              │
       localhost:30080
```

### Build images

Rancher Desktop uses `cri-dockerd` — `docker build` is enough:

```bash
docker context use rancher-desktop
docker build -t plant-operator:latest phase2/operator/
docker build -t plant-ui:latest phase2/ui/
```

`imagePullPolicy: Never` in the manifests tells k3s to use the local image.

### Create the bot token secret

```bash
kubectl create secret generic plant-secrets --from-literal=BOT_TOKEN=your_token_here
```

### Deploy

Apply in order — CRD and RBAC before the workloads:

```bash
kubectl apply -f phase2/crds/plant.yaml
kubectl apply -f phase2/rbac/
kubectl apply -f phase2/deploy/operator.yaml
kubectl apply -f phase2/deploy/ui.yaml
```

### Verify

```bash
kubectl get pods
# plant-operator-<hash>   1/1   Running
# plant-ui-<hash>         1/1   Running

kubectl logs -l app=plant-operator --follow
open http://localhost:30080
```

### Teardown

```bash
kubectl delete -f phase2/deploy/
kubectl delete -f phase2/rbac/
kubectl delete secret plant-secrets
kubectl delete plants --all
```

If the plant delete hangs (kopf finalizers with no operator running to process them):

```bash
kubectl patch crd plants.care.example.com -p '{"metadata":{"finalizers":[]}}' --type=merge
kubectl delete crd plants.care.example.com
```

---

## Step 8: Connect Telegram to the Cluster

```
BEFORE — two separate stores

  ┌──────────┐     ┌────────┐     ┌────────────┐     ┌─────────────┐
  │ Telegram │────▶│ bot.py │────▶│ storage.py │────▶│ plants.json │
  └──────────┘     └────────┘     └────────────┘     └─────────────┘

  ┌───────────┐                   ┌─────────┐         ┌──────┐
  │ Dashboard │──────────────────▶│ K8s API │────────▶│ etcd │
  └───────────┘                   └─────────┘         └──────┘

  Two write paths. Two stores. Dashboard and Telegram never see the same data.


AFTER — single source of truth

  ┌──────────┐     ┌────────┐     ┌────────────────┐     ┌─────────┐     ┌──────┐
  │ Telegram │────▶│ bot.py │────▶│ k8s_storage.py │────▶│ K8s API │────▶│ etcd │
  └──────────┘     └────────┘     └────────────────┘     └────┬────┘     └──┬───┘
                                                               │             │
  ┌───────────┐                                                │             │
  │ Dashboard │────────────────────────────────────────────────┘     reads ◀─┘
  └───────────┘

  One write path. etcd is the store. Telegram and Dashboard always see the same data.
```

`k8s_storage.py` replaces `storage.py` — same `load()` / `save()` / `today()` interface, backed by the Kubernetes API instead of `plants.json`. `bot.py` and `brain.py` each needed one import line changed.

Telegram now reads and writes the same Plant resources as the dashboard. etcd is the single source of truth. `plants.json` is retired.

**Any plant type works.** Known types (prayer plant, pothos, golden snake) use static `CARE_RULES`. Unknown types fetch care rules from MiniMax via `rules.lookup()` and cache the result for the session.

**Telegram commands:**
```
add monstera, name Pearl          → creates Plant in etcd
I watered my Maranta              → patches spec.lastWatered
how are my plants?                → reads from etcd, asks MiniMax
```

**Run the bot:**

```bash
kubectl config use-context rancher-desktop
kubectl apply -f phase2/crds/plant.yaml
kubectl apply -f phase2/rbac/
kubectl apply -f phase2/deploy/operator.yaml
source .env
python bot.py
```

Verify a plant was saved:

```bash
kubectl get plants
```

---

## Steps

| Step | What | Status |
|------|------|--------|
| 1 | Architecture + key concepts | done |
| 2 | Local K8s cluster setup with Rancher Desktop | done |
| 3 | Plant CRD with schema validation | done |
| 4 | Operator with kopf (reconcile loop) | done |
| 5 | RBAC — ServiceAccount, ClusterRole, ClusterRoleBinding | done |
| 6 | Web UI dashboard | done |
| 7 | Deploy + test end to end | done |
| 8 | Connect Telegram to etcd — single source of truth | done |
