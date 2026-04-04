#!/usr/bin/env bash
# agent-orchestrator.sh
#
# Orchestrates Creator/Reviewer Copilot agents end-to-end:
# - Dispatch approved issues to Creator session
# - Dispatch needs-review PRs to Reviewer session
# - Auto-dispatch PRs with requested changes back to Creator
# - Auto-merge approved PRs when checks pass
#
# Usage:
#   tmux new-session -d -s agent-orchestrator "bash scripts/agent-orchestrator.sh"
#
# Requires: gh, tmux, jq

set -euo pipefail

POLL_INTERVAL="${POLL_INTERVAL:-60}"
REPO="${REPO:-ICEY4040727/Self_Learning-System}"
CREATOR_SESSION="${CREATOR_SESSION:-SelfLearning-creator}"
REVIEWER_SESSION="${REVIEWER_SESSION:-SelfLearn-reviewer}"
STATE_DIR="${STATE_DIR:-/tmp/agent-orchestrator}"

APPROVED_LABEL="${APPROVED_LABEL:-approved}"
CREATOR_LABEL="${CREATOR_LABEL:-creator}"
NEEDS_REVIEW_LABEL="${NEEDS_REVIEW_LABEL:-needs-review}"
AUTO_MERGE_LABEL="${AUTO_MERGE_LABEL:-auto-merge}"

mkdir -p "$STATE_DIR"
mkdir -p "$STATE_DIR/dispatched"

for cmd in gh tmux jq; do
  if ! command -v "$cmd" >/dev/null 2>&1; then
    echo "[agent-orchestrator] ERROR: missing command: $cmd" >&2
    exit 1
  fi
done

if ! gh auth status >/dev/null 2>&1; then
  echo "[agent-orchestrator] ERROR: gh is not authenticated." >&2
  exit 1
fi

has_session() {
  tmux has-session -t "$1" 2>/dev/null
}

is_idle() {
  local session="$1"
  has_session "$session" || return 1
  local tail_lines
  tail_lines=$(tmux capture-pane -t "$session" -p 2>/dev/null | grep -v '^$' | tail -5 || true)

  if echo "$tail_lines" | grep -q "weekly\|current.*⟳\|accept edits"; then
    return 0
  fi

  if echo "$tail_lines" | tail -1 | grep -qE '[❯$%] *$'; then
    return 0
  fi

  return 1
}

queue_file_for() {
  echo "$STATE_DIR/queue_$(echo "$1" | tr '-' '_').txt"
}

notify_or_queue() {
  local session="$1"
  local msg="$2"
  local qf
  qf=$(queue_file_for "$session")

  has_session "$session" || return 0

  if is_idle "$session"; then
    tmux send-keys -t "$session" "$msg" Enter || true
    echo "[agent-orchestrator] sent -> $session :: $msg"
  else
    echo "$msg" >> "$qf"
    echo "[agent-orchestrator] queued -> $session :: $msg"
  fi
}

flush_queue() {
  local session="$1"
  local qf
  qf=$(queue_file_for "$session")

  [[ -s "$qf" ]] || return 0
  has_session "$session" || return 0
  is_idle "$session" || return 0

  local count
  count=$(wc -l < "$qf" | tr -d ' ')
  if [[ "$count" -gt 4 ]]; then
    tmux send-keys -t "$session" "[AutoFlow] You have $count queued tasks. Please sync with GitHub now." Enter || true
  else
    while IFS= read -r line; do
      tmux send-keys -t "$session" "$line" Enter || true
    done < "$qf"
  fi
  rm -f "$qf"
}

mark_done() {
  local key="$1"
  touch "$STATE_DIR/dispatched/$key"
}

is_done() {
  local key="$1"
  [[ -f "$STATE_DIR/dispatched/$key" ]]
}

dispatch_approved_issues_to_creator() {
  local issues
  issues=$(gh issue list --repo "$REPO" --state open --label "$APPROVED_LABEL" --label "$CREATOR_LABEL" --json number,title,url 2>/dev/null || echo "[]")

  jq -r '.[] | "\(.number)|\(.title)|\(.url)"' <<< "$issues" | while IFS='|' read -r num title url; do
    local key="issue_${num}_creator"
    is_done "$key" && continue

    local msg="[AutoFlow][Creator] Handle Issue #${num}: ${title}. Read full issue/comments from GitHub, implement on feature branch, push PR with label ${NEEDS_REVIEW_LABEL}, then post fix summary comment. URL: ${url}"
    notify_or_queue "$CREATOR_SESSION" "$msg"
    mark_done "$key"
  done
}

dispatch_needs_review_prs_to_reviewer() {
  local prs
  prs=$(gh pr list --repo "$REPO" --state open --label "$NEEDS_REVIEW_LABEL" --json number,title,url,isDraft 2>/dev/null || echo "[]")

  jq -r '.[] | select(.isDraft == false) | "\(.number)|\(.title)|\(.url)"' <<< "$prs" | while IFS='|' read -r num title url; do
    local key="pr_${num}_reviewer"
    is_done "$key" && continue

    local msg="[AutoFlow][Reviewer] Review PR #${num}: ${title}. Post concrete comments; choose request changes or approve. If approved and CI green, allow auto merge path. URL: ${url}"
    notify_or_queue "$REVIEWER_SESSION" "$msg"
    mark_done "$key"
  done
}

dispatch_requested_changes_to_creator() {
  local prs
  prs=$(gh pr list --repo "$REPO" --state open --json number,title,url,reviewDecision,isDraft 2>/dev/null || echo "[]")

  jq -r '.[] | select(.isDraft == false and .reviewDecision == "CHANGES_REQUESTED") | "\(.number)|\(.title)|\(.url)"' <<< "$prs" | while IFS='|' read -r num title url; do
    local key="pr_${num}_creator_rework"
    is_done "$key" && continue

    local msg="[AutoFlow][Creator] Rework PR #${num}: ${title}. Read all review comments, apply fixes, push updates, reply item-by-item in PR comments, then notify reviewer. URL: ${url}"
    notify_or_queue "$CREATOR_SESSION" "$msg"
    mark_done "$key"
  done
}

checks_success_for_pr() {
  local pr_number="$1"
  local sha
  sha=$(gh pr view "$pr_number" --repo "$REPO" --json headRefOid -q '.headRefOid' 2>/dev/null || true)
  [[ -n "$sha" ]] || return 1

  local combined
  combined=$(gh api "/repos/$REPO/commits/$sha/status" -q '.state' 2>/dev/null || echo "failure")
  [[ "$combined" == "success" ]]
}

auto_merge_approved_prs() {
  local prs
  prs=$(gh pr list --repo "$REPO" --state open --label "$NEEDS_REVIEW_LABEL" --label "$AUTO_MERGE_LABEL" --json number,title,reviewDecision,isDraft,url 2>/dev/null || echo "[]")

  jq -r '.[] | select(.isDraft == false and .reviewDecision == "APPROVED") | "\(.number)|\(.title)|\(.url)"' <<< "$prs" | while IFS='|' read -r num title url; do
    local key="pr_${num}_merged"
    is_done "$key" && continue

    if checks_success_for_pr "$num"; then
      echo "[agent-orchestrator] auto-merge PR #$num"
      if gh pr merge "$num" --repo "$REPO" --squash --delete-branch; then
        mark_done "$key"
        notify_or_queue "$CREATOR_SESSION" "[AutoFlow] PR #${num} merged: ${title}"
        notify_or_queue "$REVIEWER_SESSION" "[AutoFlow] PR #${num} merged: ${title}"
      fi
    fi
  done
}

dispatch_reviewer_backlog_when_idle() {
  local open_pr_count
  open_pr_count=$(gh pr list --repo "$REPO" --state open --json number | jq 'length')

  if [[ "$open_pr_count" -eq 0 ]]; then
    local today_key="reviewer_backlog_$(date +%Y%m%d)"
    if ! is_done "$today_key"; then
      notify_or_queue "$REVIEWER_SESSION" "[AutoFlow][Reviewer] No open PR now. Please run proactive audit on main and create bug/research issues if needed."
      mark_done "$today_key"
    fi
  fi
}

main_loop() {
  echo "[agent-orchestrator] started: repo=$REPO interval=${POLL_INTERVAL}s"

  while true; do
    flush_queue "$CREATOR_SESSION"
    flush_queue "$REVIEWER_SESSION"

    dispatch_approved_issues_to_creator || echo "[agent-orchestrator] warn: dispatch_approved_issues_to_creator"
    dispatch_needs_review_prs_to_reviewer || echo "[agent-orchestrator] warn: dispatch_needs_review_prs_to_reviewer"
    dispatch_requested_changes_to_creator || echo "[agent-orchestrator] warn: dispatch_requested_changes_to_creator"
    auto_merge_approved_prs || echo "[agent-orchestrator] warn: auto_merge_approved_prs"
    dispatch_reviewer_backlog_when_idle || echo "[agent-orchestrator] warn: dispatch_reviewer_backlog_when_idle"

    sleep "$POLL_INTERVAL"
  done
}

main_loop
