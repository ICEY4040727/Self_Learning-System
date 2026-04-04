---
mode: ask
model: GPT-5
description: "Create implementation from a GitHub issue and open/update PR for reviewer."
---

You are implementing a GitHub issue in this repository.

Input:

- Issue number: ${input:issueNumber}

Required execution:

1. Pull latest remote issue context and all comments.
2. Implement changes locally on a feature/fix branch.
3. Run relevant tests/checks.
4. Commit with conventional commit style.
5. Push and open/update PR with label needs-review and auto-merge.
6. Post a PR comment with:
   - changed files
   - behavior impact
   - test evidence
   - open risks
7. Notify reviewer session via tmux only after PR comment is posted.

Constraints:

- Never push to main directly.
- If architecture/schema decision is needed, stop and write Option A vs B in issue comment.
- If blocked by auth/permissions, report exact blocker and failed command.
