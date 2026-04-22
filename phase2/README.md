# Phase 2: Kubernetes Operator

This directory contains the Kubernetes operator implementation for the plant care agent.

## Planned structure

```
phase2/
  crds/          # Custom Resource Definitions (Plant, PlantCareSchedule)
  operator/      # kopf-based operator (reconcile logic)
  rbac/          # ServiceAccount, Role, RoleBinding manifests
  deploy/        # Operator deployment manifests
  ui/            # Web dashboard (shows Plant resources + status)
```

## Build plan

| Step | What we build | Status |
|------|--------------|--------|
| 1 | Architecture + big picture | done |
| 2 | Local K8s cluster setup (kind) | todo |
| 3 | Define the CRDs | todo |
| 4 | Build the operator | todo |
| 5 | RBAC + cluster management | todo |
| 6 | Web UI dashboard | todo |
| 7 | Deploy + test end to end | todo |
