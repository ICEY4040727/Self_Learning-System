#!/usr/bin/env bash
#
# gh-notify-daemon.sh — Poll GitHub for events and notify Creator/Reviewer via tmux
#
# Usage:
#   tmux new-session -d -s gh-notify "bash scripts/gh-notify-daemon.sh"
#
# Requires: gh (authenticated), tmux, jq

set -euo pipefail

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
POLL_INTERVAL="${POLL_INTERVAL:-60}"                                # 1 minute
REPO="${REPO:-ICEY4040727/Self_Learning-System}"
CREATOR_SESSION="${CREATOR_SESSION:-SelfLearning-creator}"
REVIEWER_SESSION="${REVIEWER_SESSION:-SelfLearn-reviewer}"
STATE_DIR="/tmp/gh-notify"

# ---------------------------------------------------------------------------
# Preflight checks
# ---------------------------------------------------------------------------
for cmd in gh tmux jq; do
    if ! command -v "$cmd" &>/dev/null; then
        echo "[gh-notify] ERROR: '$cmd' not found. Aborting." >&2
        exit 1
    fi
done

if ! gh auth status &>/dev/null; then
    echo "[gh-notify] ERROR: gh CLI not authenticated. Run 'gh auth login' first." >&2
    exit 1
fi

mkdir -p "$STATE_DIR"

echo "[gh-notify] Daemon started — repo=$REPO interval=${POLL_INTERVAL}s"
echo "[gh-notify] Creator session: $CREATOR_SESSION"
echo "[gh-notify] Reviewer session: $REVIEWER_SESSION"

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

# Check if a tmux session's active pane is idle
# Claude Code shows status bar (Opus/context/weekly) when idle at prompt
is_idle() {
    local session="$1"
    if ! tmux has-session -t "$session" 2>/dev/null; then
        return 1  # session doesn't exist
    fi
    local tail_lines
    tail_lines=$(tmux capture-pane -t "$session" -p 2>/dev/null | grep -v '^$' | tail -5)

    # Claude Code idle: status bar contains usage info
    if echo "$tail_lines" | grep -q "weekly\|current.*⟳\|accept edits"; then
        return 0
    fi
    # Traditional shell prompt
    if echo "$tail_lines" | tail -1 | grep -qE '[❯$%] *$'; then
        return 0
    fi
    return 1
}

# Send a message to a tmux session, or queue it
notify_session() {
    local session="$1"
    local message="$2"
    local queue_file="$STATE_DIR/queue_$(echo "$session" | tr '-' '_').txt"

    if ! tmux has-session -t "$session" 2>/dev/null; then
        return 0  # session doesn't exist, skip silently
    fi

    if is_idle "$session"; then
        tmux send-keys -t "$session" "$message" Enter || true
        echo "[gh-notify] Sent to $session: $message"
    else
        echo "$message" >> "$queue_file"
        echo "[gh-notify] Queued for $session: $message"
    fi
}

# Flush queued messages for a session
flush_queue() {
    local session="$1"
    local queue_file="$STATE_DIR/queue_$(echo "$session" | tr '-' '_').txt"

    [[ ! -f "$queue_file" ]] && return 0
    [[ ! -s "$queue_file" ]] && return 0

    if ! tmux has-session -t "$session" 2>/dev/null; then
        return 0
    fi

    if ! is_idle "$session"; then
        return 0  # still busy
    fi

    # Merge similar notifications to avoid spam
    local count
    count=$(wc -l < "$queue_file" | tr -d ' ') || { echo "[gh-notify] WARN: flush_queue count failed"; return 0; }
    if [[ "$count" -gt 3 ]]; then
        local merged="[通知] 你有 ${count} 条积压通知，请查看 GitHub Issues/PRs"
        tmux send-keys -t "$session" "$merged" Enter || { echo "[gh-notify] WARN: flush send failed"; return 0; }
        echo "[gh-notify] Flushed $count queued messages to $session (merged)"
    else
        while IFS= read -r line; do
            tmux send-keys -t "$session" "$line" Enter || true
        done < "$queue_file"
        echo "[gh-notify] Flushed $count queued messages to $session"
    fi

    rm -f "$queue_file"
}

# ---------------------------------------------------------------------------
# Polling functions
# ---------------------------------------------------------------------------

# Check for newly approved issues → notify Creator
check_approved_issues() {
    local state_file="$STATE_DIR/last_approved.json"
    local current

    current=$(gh issue list --repo "$REPO" --label "approved" --state open --json number,title 2>/dev/null || echo "[]")

    if [[ ! -f "$state_file" ]]; then
        echo "$current" > "$state_file"
        return 0  # first run, just save state
    fi

    local prev
    prev=$(cat "$state_file")

    # Find new issues (in current but not in prev)
    local new_issues
    new_issues=$(jq -r --argjson prev "$prev" '
        [.[] | select(.number as $n | $prev | map(.number) | index($n) | not)]
        | .[] | "[通知] 新 approved 任务: #\(.number) \(.title)"
    ' <<< "$current" 2>/dev/null || true)

    if [[ -n "$new_issues" ]]; then
        while IFS= read -r msg; do
            notify_session "$CREATOR_SESSION" "$msg"
        done <<< "$new_issues"
    fi

    # Don't overwrite state with empty result (API failure fallback)
    [[ "$current" != "[]" ]] && echo "$current" > "$state_file"
}

# Check for PRs needing review → notify Reviewer
check_needs_review() {
    local state_file="$STATE_DIR/last_needs_review.json"
    local current

    current=$(gh pr list --repo "$REPO" --label "needs-review" --state open --json number,title 2>/dev/null || echo "[]")

    if [[ ! -f "$state_file" ]]; then
        echo "$current" > "$state_file"
        return 0
    fi

    local prev
    prev=$(cat "$state_file")

    local new_prs
    new_prs=$(jq -r --argjson prev "$prev" '
        [.[] | select(.number as $n | $prev | map(.number) | index($n) | not)]
        | .[] | "[通知] 新 PR 待审查: #\(.number) \(.title)"
    ' <<< "$current" 2>/dev/null || true)

    if [[ -n "$new_prs" ]]; then
        while IFS= read -r msg; do
            notify_session "$REVIEWER_SESSION" "$msg"
        done <<< "$new_prs"
    fi

    # Don't overwrite state with empty result (API failure fallback)
    [[ "$current" != "[]" ]] && echo "$current" > "$state_file"
}

# Check for PR updates (new commits pushed) → notify Reviewer to re-review
check_pr_updates() {
    local state_file="$STATE_DIR/last_pr_commits.json"
    local current

    # Get open PRs with their latest commit SHA
    current=$(gh pr list --repo "$REPO" --state open --json number,title,headRefOid 2>/dev/null || echo "[]")

    if [[ ! -f "$state_file" ]]; then
        echo "$current" > "$state_file"
        return 0
    fi

    local prev
    prev=$(cat "$state_file")

    # Find PRs where headRefOid changed (new commits pushed)
    local updated_prs
    updated_prs=$(jq -r --argjson prev "$prev" '
        [.[] | . as $cur |
         ($prev | map(select(.number == $cur.number)) | first // null) as $old |
         select($old != null and $old.headRefOid != $cur.headRefOid)]
        | .[] | "[通知] PR #\(.number) 有新提交，请 re-review: \(.title)"
    ' <<< "$current" 2>/dev/null || true)

    if [[ -n "$updated_prs" ]]; then
        while IFS= read -r msg; do
            notify_session "$REVIEWER_SESSION" "$msg"
        done <<< "$updated_prs"
    fi

    # Don't overwrite state with empty result (API failure fallback)
    [[ "$current" != "[]" ]] && echo "$current" > "$state_file"
}

# Check for new reviewer-assigned issues → notify Reviewer
check_reviewer_issues() {
    local state_file="$STATE_DIR/last_reviewer_issues.json"
    local current

    current=$(gh issue list --repo "$REPO" --label "reviewer" --state open --json number,title 2>/dev/null || echo "[]")

    if [[ ! -f "$state_file" ]]; then
        echo "$current" > "$state_file"
        return 0
    fi

    local prev
    prev=$(cat "$state_file")

    local new_issues
    new_issues=$(jq -r --argjson prev "$prev" '
        [.[] | select(.number as $n | $prev | map(.number) | index($n) | not)]
        | .[] | "[通知] 新任务指派: #\(.number) \(.title)"
    ' <<< "$current" 2>/dev/null || true)

    if [[ -n "$new_issues" ]]; then
        while IFS= read -r msg; do
            notify_session "$REVIEWER_SESSION" "$msg"
        done <<< "$new_issues"
    fi

    # Don't overwrite state with empty result (API failure fallback)
    [[ "$current" != "[]" ]] && echo "$current" > "$state_file"
}

# ---------------------------------------------------------------------------
# Main loop
# ---------------------------------------------------------------------------
while true; do
    echo "[gh-notify] Polling at $(date '+%H:%M:%S')..."

    # Flush any queued messages first
    flush_queue "$CREATOR_SESSION"
    flush_queue "$REVIEWER_SESSION"

    # Check for new events
    check_approved_issues || echo "[gh-notify] WARN: check_approved_issues failed"
    check_needs_review    || echo "[gh-notify] WARN: check_needs_review failed"
    check_pr_updates      || echo "[gh-notify] WARN: check_pr_updates failed"
    check_reviewer_issues || echo "[gh-notify] WARN: check_reviewer_issues failed"

    sleep "$POLL_INTERVAL"
done
