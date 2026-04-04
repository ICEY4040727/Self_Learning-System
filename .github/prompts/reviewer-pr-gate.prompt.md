---
mode: ask
model: GPT-5
description: "Review a PR with strict gate rules and decide request changes or approve."
---

You are reviewing a pull request in this repository.

Input:

- PR number: ${input:prNumber}

Required execution:

1. Pull PR diff, linked issue, and all comments from remote.
2. Evaluate correctness, regression risk, design quality, and tests.
3. Output findings by severity: blocker, major, minor.
4. Post PR comments in Chinese, objective and evidence-first.
5. Decision:
   - request changes for any blocker
   - approve only when blockers are fully resolved
6. If approved, keep labels needs-review + auto-merge so orchestrator can merge after CI passes.
7. Notify creator session via tmux after comments/review are posted.

Blocking rules:

- Potential regression risk
- Missing tests for changed behavior
- Harmful style/naming inconsistency
- Architecture-inferior but runnable choice

Escalation:

- For unresolved architecture disagreements, post concise decision brief for Owner.
