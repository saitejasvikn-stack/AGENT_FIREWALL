# AGENT FIREWALL — Collaborative Research Ecosystem

> **Core Principle:**
> *«AI can act. AI cannot decide what it is allowed to do.»*

---

## 🛡️ Overview

**Agent Firewall** is an end-to-end access control, governance, and tamper-evident auditing platform for collaborative human-AI research projects. 

It solves two critical AI security and credit challenges:
1. **Confidentiality & Prompt Injection Protection**: How to prevent AI agents from leaking confidential sponsor data or executing malicious side-effect tools when exposed to untrusted user input or prompt injections.
2. **Fair Credit & Reward Distribution**: How to distribute monetary funding and Credit Units (CU) fairly among student contributors, expert mentors, and sponsors according to pre-agreed charter terms and measured impact.

---

## 🏗️ Architectural Flow

```
CHARTER  ──>  AGENT FIREWALL  ──>  HUMAN DECISION  ──>  TAMPER-EVIDENT LEDGER
(Trust)        (Policy Engine)      (Approval Queue)      (Append-Only Hash Chain)
```

1. **Charter**: Pre-agreed rules, IP terms, confidentiality levels (`PUBLIC` / `CONFIDENTIAL`), and split formulas.
2. **Agent Firewall**: Pure Python deterministic policy engine enforcing priority:
   $$\text{BLOCK} > \text{APPROVAL} > \text{ALLOW}$$
3. **Human Decision**: Side-effect tools (e.g., `send_email`, `export`, `publish`) require explicit human owner approval. Hard security blocks can **never** be overridden by human approval or LLM prompts.
4. **Ledger**: Append-only SQLite hash chain with `SHA-256` prev-hash linkage and `UPDATE`/`DELETE` trigger blocks.

---

## 🚀 How to Run

### Prerequisites
- Python 3.11+

### Quick Start (PowerShell / Windows)
```powershell
# 1. Install Dependencies
pip install fastapi uvicorn sqlalchemy pydantic pyjwt passlib bcrypt pytest requests python-multipart reportlab httpx

# 2. Run Backend & Serve Frontend
python backend/main.py
# Or run with Uvicorn:
uvicorn main:app --app-dir backend --host 127.0.0.1 --port 8000 --reload
```

Open your browser at:
`http://localhost:8000/`

---

## 👥 Synthetic Demo Users (Password for all: `demo123`)

| User | Role | Verification | Institution / Notes |
| :--- | :--- | :--- | :--- |
| **Dr. Anita Rao** | `SPONSOR` | L2 | MediVision Labs (Sponsor) |
| **Prof. Kiran Shah** | `EXPERT` | L2 | IISc Bangalore |
| **Dr. Rohan Mehta** | `EXPERT` | L2 | MediVision Competitor (Conflict of Interest) |
| **Priya** | `STUDENT` | L2 | IIT Madras |
| **Arun** | `STUDENT` | L1 | NIT Surathkal |
| **Meera** | `STUDENT` | L1 | PES University |
| **Admin** | `ADMIN` | L2 | Agent Firewall Governance |

---

## 🧪 Running Automated Tests

Run the complete test suite:
```bash
pytest backend/tests/ -v
```

Verified Test Suite:
- `test_rewards.py`: Validates exact rupee split math ($\text{Rs } 1,00,000 \rightarrow \text{Priya: } 25,783, \text{Arun: } 18,643, \text{Meera: } 15,074, \text{Expert: } 25,500$) and exact Credit Unit split ($100 \text{ CU} \rightarrow \text{Priya: } 36.0, \text{Arun: } 24.8, \text{Meera: } 19.2, \text{Expert: } 20.0$).
- `test_ledger.py`: Verifies hash chain linkage, tamper detection (`HASH_MISMATCH` / `CHAIN_BROKEN`), and SQLite `UPDATE`/`DELETE` trigger prevention.
- `test_firewall.py`: Validates decision order (Scope $\rightarrow$ Sensitivity $\rightarrow$ Injection $\rightarrow$ Side-effect $\rightarrow$ Allow) and ownerless agent rejection.
- `test_access.py`: Verifies HTTP 403 on non-member confidential brief access and absence of currency symbols (`Rs`/`₹`) on unpaid project pages.

---

## 📊 MOCKED → PRODUCTION Mapping

| Component | Hackathon Prototype (`MOCK`) | Production System |
| :--- | :--- | :--- |
| **Escrow & Payments** | Simulated status (`HELD` / `RELEASED`) | Stripe / Razorpay Escrow Gateway |
| **KYC / Identity** | Simulated levels (`L0`, `L1`, `L2`) | Aadhaar / DigiLocker / Shibboleth OAuth |
| **Similarity** | Word 5-gram Jaccard overlap ($\ge 0.35$) | Vector embeddings (OpenAI / BGE-M3) + Qdrant |
| **LLM Provider** | Deterministic `MockLLM` / Local Ollama | Self-hosted GPU cluster / vLLM / Claude API |
| **Ledger** | Local SQLite SHA-256 hash chain | Signed Ed25519 entries + Public Ethereum/Solana anchoring |

---

## 🤖 AI Tools Declaration

- **Antigravity**: Used as the primary AI coding assistant for system design, backend development, security engine implementation, unit testing, and UI creation.
