# AI Procurement Request Copilot

A small internal product that gathers procurement evidence, applies deterministic controls, and recommends the next human action. It never approves spend or purchases software.

## Customer problem and outcome

Procurement reviewers currently need to join request details with employee ownership, department budget, approved software, prior purchases, vendor records, an external risk service, and policy. Missing or conflicting evidence can lead to slow reviews or unsafe assumptions.

The copilot produces one review package containing:

- a recommendation and next step;
- source-referenced evidence;
- required human approvals;
- missing information and risk flags;
- real tool and model-call telemetry.

The measurable MVP outcome is whether the system reaches the correct next action with grounded evidence and correct escalation. Both implementations passed all 6 public quality cases in the included evaluation.

## One-command start

Python 3.11 or 3.12 is recommended.

```bash
python -m venv .venv
source .venv/bin/activate       # Windows: .venv\Scripts\activate
python -m pip install -r requirements.txt
python run_local.py
```

Open `http://127.0.0.1:8501`. The command starts both the vendor risk API on port 8001 and the Streamlit product UI on port 8501. No external API key is required for the deterministic safety path.

For the model-backed path used in the recorded evaluation, install [Ollama](https://ollama.com), then run `ollama pull llama3.2:1b`. The app calls that local model by default. Set `OLLAMA_MODEL=` to disable it, or copy `.env.example` to `.env` to change the local model or endpoint. If Ollama is unavailable, the request still completes through the deterministic safety path and reports zero successful LLM calls.

Run preflight and tests:

```bash
python verify_setup.py
python -m unittest discover -s tests -v
```

## Product workflow

1. Select a request and either the single or staged architecture.
2. Run analysis to gather requester, budget, catalog, vendor, risk API, and purchase history evidence.
3. Apply required-field, financial, security, privacy, legal, overlap, date, and injection rules.
4. Review the recommendation, evidence, approvals, missing information, and risks in separate UI panels.
5. Send the evidence package to the named human control owners.

The stable assessment adapter is:

```python
from src.solution import handle_request

decision = handle_request("REQ-1005", architecture="single")
```

It returns the supplied `ProcurementDecision` contract.

## Architecture and tools

Detailed data flow, agent boundaries, stop conditions, and assumptions are in [Architecture and workflow](docs/architecture.md).

The implementation uses nine visible evidence, AI, and control tools:

| Tool | Purpose | Type |
|---|---|---|
| `request_context_tool` | Resolve requester and department | Data retrieval |
| `budget_tool` | Compare annual cost with available budget | Deterministic |
| `catalog_tool` | Find product, vendor, and category overlap | Deterministic retrieval |
| `vendor_registry_tool` | Read procurement, security, and legal state | Data retrieval |
| `vendor_risk_api_tool` | Call the mock external service | API integration |
| `purchase_history_tool` | Find previous related purchases | Data retrieval |
| `llm_need_interpreter` | Summarize the submitted business need | Local model, advisory |
| `llm_risk_reviewer` | Explain deterministic risks in the staged path | Local model, advisory |
| `deterministic_policy_tool` | Apply policy thresholds and controls | Deterministic |

Architecture A uses one orchestrator to gather evidence and run policy. Architecture B passes a copied evidence packet from an analyst stage to an independent policy reviewer. Both share the same rules so orchestration cannot change approval thresholds.

## Safety and failure behavior

- The reference date is fixed at `2026-09-30`; the computer clock is not used for review expiry.
- Request and vendor text are treated as untrusted data. Injection-like instructions are ignored and flagged.
- Missing request fields lead to clarification, never invented values.
- API failure, stale assessment, or material conflict fails closed to Security or manual review.
- Budget, approval thresholds, and review requirements stay in deterministic code.
- All decisions set `human_review_required=true`; no code path writes purchases, budgets, or approvals.
- Unknown request IDs and architecture names fail explicitly.

## Reproducible evaluation

Run the public minimum checks while `run_local.py` is active:

```bash
python evals/run_public_evals.py --architecture single
python evals/run_public_evals.py --architecture staged
```

Run the full comparison independently; it starts and stops its own mock API:

```bash
python evals/run_comparison.py
```

The comparison uses the same six public cases for both architectures and warms both paths before measurement. It writes [detailed results](evals/evaluation_results.csv) and a [machine-readable summary](evals/comparison_summary.json).

| Metric | Single agent | Staged reviewer |
|---|---:|---:|
| Cases passing all quality checks | 6/6 | 6/6 |
| Average latency | 524.60 ms | 1,143.85 ms |
| Average LLM calls | 1.0 | 2.0 |
| Average tool calls | 8.0 | 10.0 |
| Observed policy/grounding failures | 0 | 0 |

These are local synthetic-data measurements from `llama3.2:1b` through Ollama, not production performance claims. The model only explains submitted context and deterministic controls; it cannot add approvals or change the policy result.

## Ship decision

Ship the single-agent architecture for this MVP. It matched the staged design on all evaluated quality criteria and latency while using one fewer tool call and a smaller failure surface. See the [architecture decision memo](docs/architecture_decision.md) for the evidence and production gates.

## Assumptions and limitations

- The provided datasets are a consistent snapshot and all records are synthetic.
- Currency is USD and annual cost is already annualized.
- Empty integrations means none declared; an `unknown` data class is missing information.
- Catalog overlap is intentionally conservative and needs a human to judge functional fit.
- The current product accepts seeded request IDs; it does not include identity, persistence, approval workflow, audit storage, or live enterprise connectors.
- Tool calls are synchronous and local except for the mock HTTP API.
- The local model path requires Ollama and the configured model. The deterministic fallback keeps the demo usable without that optional service.
- Before production, evaluate a governed model on stakeholder-labeled ambiguous requests; keep policy enforcement and approval authority outside the model.
- Public cases are small and visible. Hidden, adversarial, load, accessibility, and user acceptance testing remain production gates.

## Repository map

```text
app.py                       Streamlit stakeholder UI
run_local.py                 one-command local launcher
src/architectures.py         single and staged orchestration
src/procurement_tools.py     evidence tools and injection/date checks
src/llm_advisor.py           bounded local-model interpretation
src/policy_engine.py         deterministic procurement controls
src/solution.py              evaluation adapter
evals/run_comparison.py      reproducible architecture comparison
evals/evaluation_results.csv recorded per-case results
docs/architecture.md         diagram, data flow, assumptions
docs/architecture_decision.md evidence-backed decision (under 500 words)
tests/test_solution.py       solution behavior and failure tests
```

## Secret handling

`.env` and common key files are ignored. `.env.example` contains only non-secret configuration. Never commit provider credentials.
