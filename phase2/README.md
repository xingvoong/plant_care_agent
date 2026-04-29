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

---

## Step 3: Define the Plant CRD

### What we built

A `Plant` custom resource definition — Kubernetes now knows what a plant is, stores it in etcd, and exposes it through the API.

---

### What a CRD actually does

Without the CRD, running `kubectl get plants` returns an error. Kubernetes doesn't know what a plant is.

```
Before CRD:

$ kubectl get plants
Error: the server doesn't have a resource type "plants"


After CRD:

$ kubectl get plants
NAME      TYPE           LAST WATERED   CONDITION   OWNER
maranta   prayer plant   2026-04-14                 1318355077
```

The CRD is the schema. It tells Kubernetes:
- what fields a Plant has
- which fields are required
- what values are valid
- what to show in `kubectl get` output

---

### How kubectl apply works

Every time you apply a plant manifest, it goes through this flow:

```
  You write plant.yaml
          │
          ▼
  kubectl apply
          │
          ▼
  ┌───────────────────────────────────────┐
  │           API Server                  │
  │                                       │
  │  1. Is "Plant" a known resource?      │
  │     → yes, CRD registered it          │
  │                                       │
  │  2. Does this manifest match          │
  │     the CRD schema?                   │
  │     → validate required fields        │
  │     → validate enum values            │
  │     → validate date format            │
  │                                       │
  │  3. Valid? → write to etcd            │
  │     Invalid? → reject, show error     │
  └───────────────────────────────────────┘
          │
          ▼
        etcd
  (Plant object stored)
          │
          ▼
  Operator sees the change
  → runs reconcile loop
```

---

### The Plant schema

```
Plant
├── spec/                        ← what you define (desired state)
│   ├── plantName    string      required — display name ("Maranta")
│   ├── plantType    enum        required — must match a CARE_RULES key
│   │                             ("prayer plant" | "pothos" | "golden snake")
│   ├── lastWatered  date        required — YYYY-MM-DD
│   └── ownerID      string      required — Telegram user ID
│
└── status/                      ← what the operator writes (observed state)
    ├── condition    enum         "healthy" | "needsWaterSoon" | "overdue"
    ├── lastReminded date         when the owner was last sent a reminder
    └── message      string       human-readable status
```

The split between `spec` and `status` is intentional. You own `spec`. The operator owns `status`. They never write to each other's fields.

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
  │     (kubectl apply)   │     (reconcile loop)     │
  └─────────────────────────────────────────────────┘
```

---

### How it maps to the old data model

The existing `plants.json` had flat objects. The CRD mirrors those fields directly:

```
plants.json                     Plant CRD spec
───────────────────────────     ───────────────────────────
"name": "Maranta"          →    plantName: Maranta
"type": "prayer plant"     →    plantType: prayer plant
"last_watered": "2026-04-14" →  lastWatered: "2026-04-14"
<user_id key in JSON>      →    ownerID: "1318355077"
"last_reminded": "..."     →    status.lastReminded: "..."
<computed by agent.decide> →    status.condition: "overdue"
```

---

### Schema validation in action

The CRD enforces `plantType` as an enum. Bad values are rejected at apply time:

```
# Valid
plantType: prayer plant   ✓ accepted

# Invalid
plantType: cactus         ✗ rejected immediately

$ kubectl apply -f bad-plant.yaml
The Plant "cactus-plant" is invalid:
spec.plantType: Unsupported value: "cactus":
supported values: "prayer plant", "pothos", "golden snake"
```

Nothing runs. Nothing breaks silently. The cluster rejects it before it's stored.

---

### Creating a plant resource

```yaml
# phase2/crds/sample-plant.yaml
apiVersion: care.example.com/v1
kind: Plant
metadata:
  name: maranta
  namespace: default
spec:
  plantName: Maranta
  plantType: prayer plant
  lastWatered: "2026-04-14"
  ownerID: "1318355077"
```

```bash
kubectl apply -f phase2/crds/sample-plant.yaml
kubectl get plants
```

---

### Takeaways

- A CRD is just a schema. It doesn't run anything — it tells Kubernetes what shape your resource has.
- `spec` is desired state (you write it). `status` is observed state (the operator writes it). Never mix the two.
- Schema validation is enforced at apply time. If you put an invalid `plantType`, `kubectl apply` rejects it immediately — before anything runs.
- `additionalPrinterColumns` controls what `kubectl get plants` shows. Design it to be useful at a glance.
- The `status` subresource is declared separately so Kubernetes can apply RBAC to it independently — operators can update status without being able to change spec.

---

### Summary

The Plant CRD is done. Kubernetes now knows what a plant is, validates it on write, and stores it in etcd like any other resource.

The spec/status split is the key idea here. You declare what you want in `spec`. The operator observes reality and writes back to `status`. Those two things never cross. That contract is what makes the operator pattern work at scale — and it's what step 4 builds on.

---

## Step 4: Build the Operator with kopf

### Overview

The CRD told Kubernetes what a plant is. The operator is what acts on it.

An operator is a process that runs inside the cluster, watches for Plant resources, and does something when they change. In this case: check how long ago the plant was watered, compute a condition, update the status, and send a Telegram reminder if it's overdue.

`kopf` (Kubernetes Operator Pythonic Framework) is the library that handles the plumbing. It watches the Kubernetes API for events on your custom resources and calls your Python functions when something happens. You write the logic. kopf handles the wiring.

```
┌──────────────────────────────────────────────────────────────┐
│                     Operator Process                          │
│                                                              │
│   kopf watches K8s API ──► event fires ──► your handler()   │
│                                                  │           │
│                                          runs reconcile()    │
│                                                  │           │
│                                     ┌────────────▼─────────┐│
│                                     │  1. read spec         ││
│                                     │  2. compute condition ││
│                                     │  3. patch status      ││
│                                     │  4. send reminder     ││
│                                     └──────────────────────-┘│
└──────────────────────────────────────────────────────────────┘
```

The operator is a direct port of the existing agent logic. `agent.py` already knows how to take a plant dict and decide its condition. The operator wraps that in a kopf handler and plugs it into the Kubernetes event loop.

---

### The work in action

**What the reconcile loop does:**

Every time a Plant resource is created or updated, kopf fires the handler. The handler:

1. Reads `spec.lastWatered` and `spec.plantType` from the event
2. Calls the same `decide()` logic from `agent.py` — days since watered, thresholds from `CARE_RULES`
3. Maps the result to a CRD condition: `healthy`, `needsWaterSoon`, or `overdue`
4. Patches `status.condition`, `status.message`, and `status.lastReminded` back to etcd
5. If overdue or soon — fires a Telegram message via the bot token

```
Plant created/updated in etcd
          │
          ▼
  kopf fires @kopf.on.create / @kopf.on.update
          │
          ▼
  handler reads spec
  ┌────────────────────────────────────┐
  │  plantType  = "prayer plant"       │
  │  lastWatered = "2026-04-14"        │
  │  ownerID    = "1318355077"         │
  └────────────────────────────────────┘
          │
          ▼
  agent.decide() → "overdue" (days_since=12, water_days=8)
          │
          ▼
  patch status via K8s API
  ┌────────────────────────────────────┐
  │  condition:    overdue             │
  │  message:      Water today!        │
  │  lastReminded: 2026-04-26          │
  └────────────────────────────────────┘
          │
          ▼
  send Telegram reminder to ownerID
```

**How the existing code maps to the operator:**

```
agent.py (original)              operator/reconciler.py
───────────────────────          ─────────────────────────────
decide(plant)              →     same logic, reads from spec dict
next_action(plant)         →     inlined into handler — act if overdue/soon
brain.py PlantAgent.act()  →     kopf handler replaces the scan loop
bot.py polling loop        →     kopf's internal event loop
plants.json                →     etcd (Plant resources)
```

The logic didn't change. The infrastructure around it did.

**Operator file structure:**

```
phase2/operator/
  main.py          # kopf entry point — registers handlers, starts the loop
  reconciler.py    # reconcile logic — ports agent.decide() for K8s resources
```

`main.py` is thin — it imports kopf, imports the reconciler, and runs. All the logic lives in `reconciler.py`.

**Running it locally:**

```bash
cd phase2/operator
pip install kopf kubernetes requests
kubectl apply -f ../crds/plant.yaml       # register the CRD
kopf run main.py --verbose                # start the operator
```

In another terminal:

```bash
kubectl apply -f ../crds/sample-plant.yaml
kubectl get plants
# NAME      TYPE           LAST WATERED   CONDITION   OWNER
# maranta   prayer plant   2026-04-14     overdue     1318355077
```

The operator sees the new Plant, runs reconcile, patches the status. `kubectl get plants` shows `overdue` in the Condition column immediately.

---

### Summary

The operator is the bridge between the CRD schema and real behavior. kopf handles watching the API and firing events. Your code handles the logic.

Everything in `agent.py` still applies — the thresholds, the condition labels, the Telegram reminder. The only thing that changed is where the plants live (etcd instead of `plants.json`) and what triggers the check (a Kubernetes event instead of a polling loop). Same brain, different nervous system.

---

### Takeaways

- kopf turns a Python function into a Kubernetes operator. You write the handler. kopf handles watching, retrying, and status patching.
- The reconcile loop is not a cron job. It fires on change events, not on a timer. If you need time-based checks (e.g. "check every day"), you add a kopf timer alongside the event handler.
- Porting `agent.py` was mostly copy-paste. The spec dict from the kopf event has the same shape as the plant dict in `plants.json` — the field names just changed.
- Status patching requires the `status` subresource. That's why it was declared separately in the CRD. Without it, the operator can't write to `status` independently of `spec`.
- Running the operator locally (`kopf run`) is enough for development. No cluster deployment needed until step 7.

---

## Step 5: RBAC — ServiceAccount, Role, RoleBinding

### What we built

Three Kubernetes objects that give the operator exactly the permissions it needs — no more.

```
phase2/rbac/
  serviceaccount.yaml   # identity the operator runs as
  role.yaml             # what that identity is allowed to do
  rolebinding.yaml      # connects the two
```

---

### Why RBAC exists

By default, a process running inside a Kubernetes cluster has no access to the API. It can't read resources, can't patch status, can't create events. Nothing.

RBAC (Role-Based Access Control) is the permission system that changes that. You declare:
1. An identity (ServiceAccount)
2. A set of permissions (Role or ClusterRole)
3. A binding between them (RoleBinding or ClusterRoleBinding)

Without RBAC, the operator process starts, tries to watch for Plant resources, and immediately gets a 403. The cluster refuses to serve it.

```
Without RBAC:

  Operator Pod starts
        │
        ▼
  GET /apis/care.example.com/v1/plants
        │
        ▼
  ✗ 403 Forbidden
    "plants is forbidden: User system:serviceaccount:default:default
     cannot list resource plants in API group care.example.com"
        │
        ▼
  operator crashes on startup


With RBAC:

  Operator Pod starts
        │
        ▼
  GET /apis/care.example.com/v1/plants
        │
        ▼
  API Server: does plant-operator have "list" on "plants"?
        │
        ▼
  ClusterRoleBinding → ClusterRole → rule found → ✓ allowed
        │
        ▼
  operator starts watching for Plant events
```

---

### The three objects

How they connect:

```
┌──────────────────────┐          ┌────────────────────────────┐
│    ServiceAccount    │          │        ClusterRole          │
│                      │          │                             │
│   name: plant-       │          │   name: plant-operator-role │
│         operator     │          │                             │
│   namespace: default │          │   rules:                    │
│                      │          │   · plants      → get,list  │
│   (identity the      │          │                    watch    │
│    Pod runs as)      │          │   · plants/status → patch   │
└──────────┬───────────┘          │   · CRDs        → get,list │
           │                      │   · events      → create   │
           │                      │   · leases      → get,create│
           │                      └──────────────┬─────────────┘
           │                                     │
           └──────────────┬──────────────────────┘
                          │
             ┌────────────▼────────────┐
             │    ClusterRoleBinding    │
             │                         │
             │  subject:               │
             │    plant-operator SA    │
             │  roleRef:               │
             │    plant-operator-role  │
             │                         │
             │  (the wire between      │
             │   identity + perms)     │
             └─────────────────────────┘
```

All three must exist. Missing any one: the binding has nothing to grant, the role has no subject, or the identity has no permissions.

**ServiceAccount** — the identity

```yaml
# serviceaccount.yaml
apiVersion: v1
kind: ServiceAccount
metadata:
  name: plant-operator
  namespace: default
```

A ServiceAccount is like a user account, but for a process instead of a person. When the operator Pod runs, Kubernetes automatically mounts credentials for this ServiceAccount into the container. The operator uses those credentials to talk to the API.

---

**ClusterRole** — the permission set

```yaml
# role.yaml
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRole
metadata:
  name: plant-operator-role
rules:
  - apiGroups: ["care.example.com"]
    resources: ["plants"]
    verbs: ["get", "list", "watch", "patch", "update"]
  - apiGroups: ["care.example.com"]
    resources: ["plants/status"]
    verbs: ["get", "patch", "update"]
  - apiGroups: ["apiextensions.k8s.io"]
    resources: ["customresourcedefinitions"]
    verbs: ["get", "list", "watch"]
  - apiGroups: [""]
    resources: ["events"]
    verbs: ["create", "patch", "update", "get", "list"]
  - apiGroups: ["coordination.k8s.io"]
    resources: ["leases"]
    verbs: ["get", "create", "update", "patch", "list", "watch"]
```

Each rule is: for these API groups, on these resource types, allow these verbs.

A Role is namespace-scoped. A ClusterRole is cluster-wide. The operator needs ClusterRole because:
- CRDs are cluster-scoped (not in any namespace)
- kopf reads the CRD schema on startup to understand the resource structure
- Leases (used for leader election) live at the cluster level

---

**ClusterRoleBinding** — the connection

```yaml
# rolebinding.yaml
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRoleBinding
metadata:
  name: plant-operator-rolebinding
subjects:
  - kind: ServiceAccount
    name: plant-operator
    namespace: default
roleRef:
  kind: ClusterRole
  name: plant-operator-role
  apiGroup: rbac.authorization.k8s.io
```

The binding says: "the `plant-operator` ServiceAccount has the permissions defined in `plant-operator-role`." Without this, the Role exists but grants nothing to anyone.

---

### What each permission is for

```
Resource                    Verbs                    Why
──────────────────────────  ───────────────────────  ──────────────────────────────────────
plants                      get, list, watch         read Plant objects to reconcile
plants/status               patch, update            write condition/message back to etcd
customresourcedefinitions   get, list, watch         kopf reads CRD schema on startup
events                      create, patch, update    kopf posts events ("reconciled Plant X")
leases                      get, create, update      kopf leader election (one active operator)
```

`plants` and `plants/status` are separate resources because the CRD declared `status` as a subresource. That means RBAC can control them independently — the operator can patch status without being able to change spec.

---

### Role vs ClusterRole

A `Role` only grants permissions within one namespace. A `ClusterRole` grants permissions cluster-wide.

```
┌────────────────────────────────────────────────────────────┐
│                      Kubernetes Cluster                     │
│                                                             │
│   cluster-scoped (no namespace):                            │
│   ┌─────────────────────────────────────────────────────┐  │
│   │  customresourcedefinitions   ← kopf reads on startup │  │
│   │  leases                      ← kopf leader election  │  │
│   │  ClusterRole                                         │  │
│   │  ClusterRoleBinding                                  │  │
│   └─────────────────────────────────────────────────────┘  │
│                                                             │
│   namespace "default":                                      │
│   ┌─────────────────────────────────────────────────────┐  │
│   │  plants         ← Plant resources, stored in etcd   │  │
│   │  events         ← kopf posts these after reconcile  │  │
│   │  ServiceAccount: plant-operator                     │  │
│   └─────────────────────────────────────────────────────┘  │
└────────────────────────────────────────────────────────────┘
```

Plants live in a namespace. CRDs and Leases don't. That's why we use ClusterRole — not because we want broad access, but because some of the resources we need are cluster-scoped.

This is a common RBAC pattern: ClusterRole for the permission definition (because some resources are cluster-level), RoleBinding in the namespace for everything namespace-scoped.

---

### Applying the RBAC

```bash
kubectl apply -f phase2/rbac/serviceaccount.yaml
kubectl apply -f phase2/rbac/role.yaml
kubectl apply -f phase2/rbac/rolebinding.yaml
```

Verify it's wired up:

```bash
kubectl get serviceaccount plant-operator
kubectl get clusterrole plant-operator-role
kubectl get clusterrolebinding plant-operator-rolebinding
```

Test that the ServiceAccount has the permissions it expects:

```bash
kubectl auth can-i watch plants \
  --as=system:serviceaccount:default:plant-operator
# yes

kubectl auth can-i delete plants \
  --as=system:serviceaccount:default:plant-operator
# no
```

`kubectl auth can-i` is the fastest way to verify that RBAC is doing what you expect.

---

### When this matters

Running `kopf run main.py` locally uses your kubeconfig credentials — whatever `kubectl config current-context` points to. Your user probably has admin access. RBAC doesn't matter yet.

RBAC kicks in when the operator runs as a Pod inside the cluster. The Pod runs as the `plant-operator` ServiceAccount. If the ServiceAccount doesn't have the right permissions, the operator fails with 403s. That's step 7.

For now: the files exist, the objects are applied, and the permissions are verified. When deployment comes, this is already done.

---

### Takeaways

- Every process in the cluster needs a ServiceAccount, a Role, and a binding. All three are required — missing any one of them and nothing works.
- ClusterRole doesn't mean "admin". It means "cluster-scoped resource". You can write a ClusterRole with minimal permissions.
- `plants` and `plants/status` are separate in RBAC because the CRD declared the status subresource. That split is what lets you give the operator write access to status without giving it write access to spec.
- `kubectl auth can-i` with `--as` is the right way to test RBAC. Don't guess — verify.
- RBAC is least-privilege by default. If you don't explicitly grant a verb on a resource, it's denied.

---

## Step 6: Web UI Dashboard

### What we built

A Flask dashboard that reads all `Plant` resources from the cluster via the Kubernetes API, displays them with condition-based color coding, and lets you add new plants through a form — no `kubectl` or YAML files required.

```
phase2/ui/
  app.py              # Flask app — queries K8s custom objects API, handles form POST
  templates/
    index.html        # dashboard — add form + summary bar + plant table
```

---

### What it shows

The dashboard is a live read from etcd. Every page load hits the Kubernetes API directly — no separate database, no cache. What `kubectl get plants` shows and what the dashboard shows are the same data.

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
│  Plant     Type          Last Watered  Condition  Status    │
│  ──────────────────────────────────────────────────────     │
│  Maranta   prayer plant  2026-04-14    OVERDUE    Overdue   │
│  Pothos    pothos        2026-04-20    SOON       Water...  │
│  Snake     golden snake  2026-04-01    HEALTHY    Healthy   │
└──────────────────────────────────────────────────────────────┘
```

Rows are sorted: overdue first, then soon, then healthy. Each row has a left-border accent in red, orange, or green.

---

### How it reads from the cluster

The Kubernetes Python client provides `CustomObjectsApi` — the same resource group the CRD registered:

```
GET /apis/care.example.com/v1/namespaces/default/plants
```

```python
api = client.CustomObjectsApi()
result = api.list_namespaced_custom_object(
    group="care.example.com",
    version="v1",
    namespace="default",
    plural="plants",
)
```

The response is the same shape as `kubectl get plants -o json`. Each item has `metadata`, `spec`, and `status` — the dashboard flattens those into a display dict.

```
K8s API response
  items[0]:
    metadata.name     → resource_name
    spec.plantName    → plant_name
    spec.plantType    → plant_type
    spec.lastWatered  → last_watered
    spec.ownerID      → owner_id
    status.condition  → condition  (written by operator)
    status.message    → message    (written by operator)
    status.lastReminded → last_reminded
```

`status.*` fields are empty until the operator has run a reconcile. The dashboard handles that gracefully — it displays "—" for missing fields rather than crashing.

---

### Config loading

```python
def load_k8s_config():
    try:
        config.load_incluster_config()   # running as a Pod inside the cluster
    except config.ConfigException:
        config.load_kube_config()        # local dev — reads ~/.kube/config
```

The same code works locally and when deployed as a Pod. In-cluster config uses the ServiceAccount token mounted at `/var/run/secrets/kubernetes.io/serviceaccount`. Local config uses whichever context `kubectl config current-context` points to.

---

### Adding a plant through the UI

Fill in the form at the top of the dashboard and click Add:

- **Plant Name** — display name (e.g. "Maranta")
- **Type** — dropdown limited to valid CRD enum values
- **Last Watered** — date picker
- **Owner ID** — Telegram user ID

The form POSTs to `/add`. The handler calls `create_namespaced_custom_object` — the same effect as `kubectl apply`, no YAML file needed. The resource name is derived automatically from the plant name (lowercased, spaces replaced with hyphens).

```
User fills form → POST /add
                       │
                       ▼
          create_namespaced_custom_object()
                       │
                       ▼
          Plant stored in etcd
                       │
                       ▼
          Operator sees new Plant → reconciles → writes status
                       │
                       ▼
          Redirect → dashboard shows new plant with condition
```

---

### Running it locally

```bash
cd phase2/ui
pip install flask kubernetes
python app.py
```

Open `http://localhost:5000`. The dashboard reads from whichever cluster your kubeconfig points to.

To test with real data:

```bash
kubectl apply -f ../crds/plant.yaml          # CRD must exist
kopf run ../operator/main.py --verbose       # operator writes status
```

Then add a plant through the form — no `kubectl apply` needed.

To seed data manually (optional):

```bash
kubectl apply -f ../crds/sample-plant.yaml
```

---

### What RBAC the UI needs

The dashboard reads and writes. It needs `get`, `list`, and `create` on `plants`. When deployed as a Pod, it runs as a ServiceAccount — either reuse `plant-operator` (which already has those verbs) or create a separate ServiceAccount scoped to just what the UI needs.

For now the dashboard runs locally under your kubeconfig credentials. RBAC for the deployed Pod is part of step 7.

---

### Takeaways

- The dashboard reads and writes directly to etcd via the K8s API. There's no separate data layer. You add plants through the form — the operator picks them up and writes status back.
- `CustomObjectsApi.list_namespaced_custom_object` reads. `create_namespaced_custom_object` writes. Same group, version, and plural as the CRD definition.
- In-cluster config and kubeconfig are the same function call — the client picks the right one automatically.
- The status fields are empty until the operator runs. Design the UI to handle that, not assume it.
- The resource name is derived from the plant name — lowercased, spaces replaced with hyphens. The CRD enforces uniqueness, so duplicate names get a 409 from the API.

---

## Step 7: Deploy + Test End to End

### What we built

Docker images and Kubernetes manifests for deploying both the operator and the web UI as Pods inside the cluster.

```
phase2/
  operator/
    Dockerfile          # operator image — kopf + reconciler
  ui/
    Dockerfile          # UI image — gunicorn + Flask app
  deploy/
    operator.yaml       # Deployment for the operator Pod
    ui.yaml             # Deployment + NodePort Service for the UI
  rbac/
    role.yaml           # updated: added "create" verb for plants (UI needs it)
```

---

### How deployment works

Running `kopf run main.py` locally uses your kubeconfig credentials. When deployed as a Pod, the operator runs as the `plant-operator` ServiceAccount. Kubernetes auto-mounts the ServiceAccount token — the operator uses it to talk to the API server without any extra config.

The same applies to the UI. Same ServiceAccount, same token, same API access pattern.

```
┌─────────────────────────────────────────────────┐
│               Kubernetes Cluster                 │
│                                                  │
│  ┌──────────────────────┐                        │
│  │   plant-operator Pod │                        │
│  │   image: plant-      │  watches Plant CRD     │
│  │   operator:latest    │──────────────────────► │
│  │   SA: plant-operator │  patches status        │
│  └──────────────────────┘  sends Telegram        │
│                                                  │
│  ┌──────────────────────┐                        │
│  │   plant-ui Pod        │                       │
│  │   image: plant-      │  reads/creates Plants  │
│  │   ui:latest          │──────────────────────► │
│  │   SA: plant-operator │                        │
│  └──────────────────────┘                        │
│           │                                      │
│   NodePort :30080                                │
│           │                                      │
└───────────┼──────────────────────────────────────┘
            │
     browser at localhost:30080
```

---

### Build the images

Rancher Desktop on macOS uses `cri-dockerd` — k3s delegates image management to Docker. Build with Docker and the images are immediately available to k3s.

First confirm the Docker context is set to Rancher Desktop:

```bash
docker context use rancher-desktop
```

Then build:

```bash
docker build -t plant-operator:latest phase2/operator/
docker build -t plant-ui:latest phase2/ui/
```

`imagePullPolicy: Never` in the manifests tells k3s to use the local image — no registry push needed.

> **Note:** `nerdctl --namespace k8s.io build` is the documented approach but requires `buildkitd` running inside the Lima VM, which Rancher Desktop doesn't start by default. The `docker build` + cri-dockerd path works out of the box.

---

### Create the bot token secret

The operator reads `BOT_TOKEN` from a Kubernetes Secret. Pass it as a single command (no line break around the token):

```bash
kubectl create secret generic plant-secrets --from-literal=BOT_TOKEN=your_token_here
```

Do this once. The Deployment references it via `secretKeyRef` — the token never appears in the manifest file.

---

### Deploy everything

Apply in order — CRD and RBAC before the workloads that depend on them:

```bash
# 1. CRD
kubectl apply -f phase2/crds/plant.yaml

# 2. RBAC
kubectl apply -f phase2/rbac/serviceaccount.yaml
kubectl apply -f phase2/rbac/role.yaml
kubectl apply -f phase2/rbac/rolebinding.yaml

# 3. Operator
kubectl apply -f phase2/deploy/operator.yaml

# 4. UI
kubectl apply -f phase2/deploy/ui.yaml
```

---

### Verify

```bash
# Pods are running
kubectl get pods
# NAME                              READY   STATUS    RESTARTS
# plant-operator-<hash>             1/1     Running   0
# plant-ui-<hash>                   1/1     Running   0

# Operator logs
kubectl logs -l app=plant-operator --follow

# UI is reachable
open http://localhost:30080
```

---

### Test the full flow

1. Open `http://localhost:30080`
2. Add a plant through the form — set `lastWatered` to a date 2+ weeks ago
3. Click **Water** on any overdue plant to reset `lastWatered` to today
4. Watch the operator logs: it fires a reconcile within seconds of any change
5. Refresh the dashboard — condition updates immediately
6. If `BOT_TOKEN` is set, the Telegram reminder fires for overdue plants

```
Browser form submit (add) or Water button click
      │
      ▼
plant-ui Pod → create or patch Plant in etcd
      │
      ▼
plant-operator Pod sees change → reconcile
      │
      ▼
status.condition written to etcd
      │
      ├─► Telegram reminder sent (if overdue/soon)
      │
      ▼
Browser refresh → dashboard shows updated condition
```

---

### Development workflow

The in-cluster UI requires a full image rebuild on every code change:

```bash
docker build -t plant-ui:latest phase2/ui/
kubectl rollout restart deployment/plant-ui
```

For faster iteration, run the UI locally — it talks to the same cluster:

```bash
kubectl delete deployment plant-ui   # remove the in-cluster pod
cd phase2/ui
python app.py                        # auto-reloads on file changes
# open http://localhost:5000
```

Use `localhost:5000` while developing. Redeploy to the cluster (`localhost:30080`) when done.

---

### Teardown

```bash
kubectl delete -f phase2/deploy/
kubectl delete -f phase2/rbac/
kubectl delete -f phase2/crds/plant.yaml
kubectl delete secret plant-secrets
```

---

### Takeaways

- `imagePullPolicy: Never` is the right setting for local images. Without it, k3s tries to pull from Docker Hub and fails.
- Secrets go in `kubectl create secret`, not in YAML files. Never commit tokens to the repo.
- Apply order matters: CRD before the operator (it reads the schema on startup), RBAC before the Pods (they need the ServiceAccount to exist).
- The operator and UI use the same ServiceAccount. In production you'd separate them — the UI only needs `get`, `list`, `create` on plants; the operator needs `patch` and `update` on status too.
- Rancher Desktop on macOS uses `cri-dockerd` — k3s uses Docker as its container runtime. `docker build` is enough. `nerdctl` requires `buildkitd` which isn't running by default.
- For development, run the UI locally (`python app.py`) and only deploy to the cluster to verify the final image. Rebuilding the image on every change is slow.

---

## Game plan

| Step | What | Status |
|------|------|--------|
| 1 | Architecture + big picture | done |
| 2 | Local K8s cluster setup with Rancher Desktop | done |
| 3 | Define the `Plant` CRD with schema validation | done |
| 4 | Build the operator with `kopf` (reconcile loop) | done |
| 5 | RBAC — ServiceAccount, Role, RoleBinding | done |
| 6 | Web UI dashboard | done |
| 7 | Deploy + test everything end to end | done |

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
