# Architecture Decision Memo

**Decision:** Ship the single-agent architecture for the MVP.

## Evidence

Both architectures were evaluated on the same six public cases. Each case was run five measured times after both paths were warmed. Quality checks covered correct next action, evidence-to-tool grounding, supplied policy expectations, and correct human escalation.

| Metric | Single agent | Staged / 2-agent |
|---|---:|---:|
| Cases passing all quality checks | 6/6 | 6/6 |
| Average latency | 3.6 ms | 3.6 ms |
| Average LLM calls | 0.0 | 0.0 |
| Average tool calls | 7.0 | 8.0 |
| Observed policy/grounding failures | 0 | 0 |

The staged reviewer produced no quality improvement on this test set and added one policy tool call per request. Local latency was effectively equal, so the decision rests on equivalent outcomes with less orchestration and a smaller failure surface.

## Trade-offs

The single path is easier to trace, operate, and explain to Procurement. Shared deterministic rules keep thresholds and sensitive approvals consistent. The staged path adds an explicit review boundary and could catch future nondeterministic reasoning errors, but it currently reruns the same policy logic over the same evidence. That is redundancy without demonstrated benefit.

## Risks and limitations

The dataset is synthetic, small, and visible. No model credential was available, so measured runs used the deterministic fallback and truthfully recorded zero LLM calls. The experiment therefore validates evidence integration, rule behavior, failure handling, and orchestration; it does not establish model quality. The overlap matcher is conservative, and there is no identity layer, persistence, approval workflow, or production audit store.

Before production, I would test hidden and adversarial cases, add stakeholder-labeled examples, run load and connector-failure tests, and measure clarification rate, incorrect escalation, human override rate, evidence freshness, and time to decision. If a governed model is added for ambiguous need interpretation, policy decisions remain deterministic and model output receives its own grounding and injection evaluations.

## Why this is the right MVP

The single architecture solves the client’s immediate problem: it gathers evidence, fails closed, applies policy consistently, and hands decisions to humans. The staged option should be reconsidered only when evaluation shows that an independent reviewer catches material errors often enough to justify its added cost and complexity.
