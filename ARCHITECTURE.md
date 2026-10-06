# AGENT FIREWALL — Technical Architecture & Scalability

## System Architecture

```
                               ┌───────────────────────────┐
                               │     Human Interface       │
                               │  (Sponsor/Student/Expert) │
                               └─────────────┬─────────────┘
                                             │ HTTP/JWT
                                             ▼
 ┌────────────────────────────────────────────────────────────────────────┐
 │                         FastAPI Control Plane                          │
 ├──────────────────────────┬───────────────────────────┬─────────────────┤
 │     Auth & RBAC          │   Charter & Scoping       │  Reward Engine  │
 └─────────────┬────────────┴─────────────┬─────────────┴────────┬────────┘
               │                          │                      │
               │                          ▼                      │
               │            ┌───────────────────────────┐        │
               │            │   Agent Firewall Engine   │        │
               │            │ (Scope/Sens/Inject/Side)  │        │
               │            └─────────────┬─────────────┘        │
               │                          │                      │
               ▼                          ▼                      ▼
 ┌────────────────────────────────────────────────────────────────────────┐
 │                       Tamper-Evident Ledger                            │
 │                (SHA-256 Hash Chain + DB Triggers)                      │
 └────────────────────────────────────────────────────────────────────────┘
```

---

## ⚡ Scalability & Production Engineering

1. **Database Layer (PostgreSQL)**:
   - Replace SQLite with PostgreSQL featuring append-only table partitions, row-level security (RLS), and database triggers (`BEFORE UPDATE OR DELETE ON ledger_entries`).

2. **Asynchronous Agent Task Queue (Celery + Redis)**:
   - Execute LLM tool requests and background agent tasks asynchronously using Celery worker nodes backed by Redis queues.

3. **Isolated Sandboxed Containers**:
   - Each project workspace runs inside an isolated Docker container with zero inter-container networking. Agents assigned to Project A physically cannot access filesystem resources or networks of Project B.

4. **Stateless Horizontally Scalable Firewall**:
   - The Agent Firewall policy evaluation engine is pure deterministic Python code. It carries no internal state and can scale horizontally across hundreds of API instances behind an HTTP load balancer.

5. **Merkle Root Ledger Batching & Blockchain Anchoring**:
   - Periodically aggregate SHA-256 ledger entry hashes into a Merkle tree root every 100 entries and anchor the signed Merkle root onto a public blockchain (e.g., Ethereum / Polygon) for immutable public proof.
