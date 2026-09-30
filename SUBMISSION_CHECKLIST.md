# Final submission checklist

Reviewed against the assignment brief, starter instructions, public rubric categories, and starter checklist on 30 September 2026.

| Requirement | Implemented or evidenced in | Status | Remaining limitation |
|---|---|---|---|
| Working end-to-end product | `app.py`, `run_local.py`, `src/solution.py` | Complete | Uses seeded requests rather than a create-request form |
| One-command local start | `python run_local.py` | Complete | Dependencies must be installed first |
| Request details and evidence UI | `app.py` | Complete | No authentication or accessibility study |
| Recommendation, approvals, missing info, risks, next step | `app.py`, `src/contracts.py` | Complete | Recommendations remain advisory by design |
| Single-agent baseline | `src/architectures.py::run_single_agent` | Complete | Deterministic fallback used in recorded run |
| Staged / 2-agent variant | `src/architectures.py::run_staged_agents` | Complete | Both stages currently share the same policy code |
| At least three tools | `src/procurement_tools.py`, `src/policy_engine.py` | Complete | Local CSV connectors are demonstration adapters |
| At least one deterministic tool | Budget, catalog, and policy tools | Complete | None |
| Structured output contract | `ProcurementDecision` returned by `handle_request` | Complete | None |
| Human handoff and authority | Output contract, UI, recommendation logic | Complete | No external approval-system connector |
| Fixed policy reference date | `src/procurement_tools.py::REFERENCE_DATE` | Complete | Date is tied to supplied snapshot |
| Incomplete and ambiguous request | Policy engine and `REQ-1006` tests/eval | Complete | Free-form ambiguity beyond supplied fields needs model/user research |
| Existing-tool overlap | Catalog tool and `REQ-1002`/`REQ-1003` | Complete | String/category matching is conservative |
| Stale or conflicting vendor evidence | Policy engine | Complete | No source confidence weighting |
| Sensitive data and approval thresholds | Policy engine and tests | Complete | Policy changes require a code/config update |
| Prompt injection in business data | Injection detector and `REQ-1006` test | Complete | Pattern detection is not a complete content-security system |
| Tool/API unavailable | Fail-closed vendor tool and `REQ-1009` test | Complete | No retry or circuit breaker in MVP |
| Reproducible same-set evaluation | `evals/run_comparison.py` | Complete | Six visible synthetic cases only |
| Evaluation results | `evals/evaluation_results.csv`, `comparison_summary.json` | Complete | Local latency is not production performance |
| Latency and call counts | Evaluation files and README | Complete | Zero LLM calls because no model credential was supplied |
| Architecture/workflow diagram and assumptions | `docs/architecture.md` | Complete | Mermaid requires a compatible renderer on GitHub |
| Decision memo <=500 words | `docs/architecture_decision.md` (380 words) | Complete | Decision should be revisited with model-backed evals |
| README setup, flow, tools, comparison, ship decision, limitations | `README.md` | Complete | None |
| Error and edge-case tests | `tests/test_solution.py` plus starter tests | Complete | No load, browser accessibility, or live enterprise integration tests |
| No secrets and `.env.example` | `.gitignore`, `.env.example` | Complete | Repository still needs publishing under the student's GitHub account |
| Public GitHub repository URL | Prepared local Git repository | Pending | Requires the student's GitHub destination and public push |
| Google Form submission | Assignment form | Pending | Must be submitted by the student with the public repository URL |

## Verified commands

```text
python verify_setup.py                              PASS
python -m unittest discover -s tests -v            PASS (17 tests)
python evals/run_public_evals.py --architecture single  PASS (6/6)
python evals/run_public_evals.py --architecture staged  PASS (6/6)
python evals/run_comparison.py                      PASS (6/6 each)
python run_local.py                                 PASS (API and UI reachable)
Streamlit render and analysis interaction           PASS
```
