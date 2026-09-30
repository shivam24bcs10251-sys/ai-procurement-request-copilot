# Architecture Decision Memo

**Decision:** Ship the single-agent architecture for the MVP.

## Evidence

Both architectures were evaluated on the same six public cases after both paths were warmed. Quality checks covered correct next action, evidence-to-tool grounding, supplied policy expectations, and correct human escalation. The run used the local `llama3.2:1b` model through Ollama.

| Metric | Single agent | Staged / 2-agent |
|---|---:|---:|
| Cases passing all quality checks | 6/6 | 6/6 |
| Average latency | 524.60 ms | 1,143.85 ms |
| Average LLM calls | 1.0 | 2.0 |
| Average tool calls | 8.0 | 10.0 |
| Observed policy/grounding failures | 0 | 0 |

The staged reviewer produced no quality improvement on this test set, added a second model call and policy pass, and was about 2.2 times slower. The decision rests on equivalent outcomes with less orchestration and a smaller failure surface.

## Trade-offs

The single path is easier to trace, operate, and explain to Procurement. Shared deterministic rules keep thresholds and sensitive approvals consistent. The staged path adds an explicit review boundary and a separate AI explanation, but it currently reruns the same policy logic over the same evidence. That is extra work without demonstrated benefit.

## Risks and limitations

The dataset is synthetic, small, and visible, and each architecture/case pair had one measured run. The local 1B model is not a production-approved service, and these cases do not establish model quality. The overlap matcher is conservative, and there is no identity layer, persistence, approval workflow, or production audit store.

Before production, I would test hidden and adversarial cases, add stakeholder-labeled examples, run load and connector-failure tests, and measure clarification rate, incorrect escalation, human override rate, evidence freshness, and time to decision. If a governed model is added for ambiguous need interpretation, policy decisions remain deterministic and model output receives its own grounding and injection evaluations.

## Why this is the right MVP

The single architecture solves the client’s immediate problem: it gathers evidence, fails closed, applies policy consistently, and hands decisions to humans. The staged option should be reconsidered only when evaluation shows that an independent reviewer catches material errors often enough to justify its added cost and complexity.
