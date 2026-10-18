# Architecture Decision Records

Create numbered records (0001-short-title.md) for irreversible or material decisions called out in AGENTS.md. Each ADR should state Context, Decision, Alternatives, Consequences, and Evidence/References. Draft decisions must not be represented as approved. A routine implementation detail does not require an ADR.

## Diagram synchronization (required for every ADR PR)

The public architecture figure embedded in [README](../../README.md) is maintained in [docs/architecture.svg](../architecture.svg). The accepted [ADR 0001](0001-core-cli-boundaries.md) establishes the headless Core ↔ CLI/third-party-consumer boundary.

- If a new or revised ADR changes components, responsibilities, source/consumer extensibility, data flows, public contracts, OS/DE/WM setter interfaces or dependency directions, update **docs/architecture.svg in that very PR**. Keep the README's explanation and docs/architecture.md consistent. Mark `Architecture diagram: updated` in the PR.
- If an ADR genuinely does not affect the depicted architecture (for example, a documentation-only correction), put `Diagram impact: none - <specific technical rationale>` in the ADR and `Architecture diagram: unchanged - <specific technical rationale>` in the PR. Explain why the *existing figure remains accurate*. The CI validator requires both justifications and rejects empty/generic statements.
- Do not postpone diagram changes to a follow-up PR or draw speculative capabilities as current. Use a dashed visual treatment with 'planned' labeling for future functionality.
- Inspect rendered GitHub README diagram before merging. The automated check verifies references, parseability, key components and ADR/diagram synchronization; semantic accuracy still requires review.
