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
CREATOR_SESSION="${CREATOR_SESSION:-creator}"
REVIEWER_SESSION="${REVIEWER_SESSION:-reviewer}"
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

    # Claude Code idle markers across UI variants
    if echo "$tail_lines" | grep -q "weekly\|current.*⟳\|accept edits\|Type @ to mention files\|autopilot\|shift+tab switch mode\|ctrl+q enqueue"; then
        return 0
    fi
    # Traditional shell prompt
    if echo "$tail_lines" | tail -1 | grep -qE '[❯$%] *$'; then
        return 0
    fi
    return 1
}

# Build queue file path for a session name
queue_file_path() {
    local session="$1"
    echo "$STATE_DIR/queue_$(echo "$session" | tr '-' '_').txt"
}

# Discover fallback session by role when configured session name is absent
discover_session_by_role() {
    local role="$1"
    local sessions
    sessions=$(tmux list-sessions -F '#S' 2>/dev/null || true)
    [[ -z "$sessions" ]] && return 1

    if [[ "$role" == "creator" ]]; then
        for candidate in creator SelfLearning-creator creator-try; do
            if echo "$sessions" | grep -Fxq "$candidate"; then
                echo "$candidate"
                return 0
            fi
        done
        while IFS= read -r session; do
            [[ -z "$session" ]] && continue
            if [[ "$session" == *creator* && "$session" != *reviewer* ]]; then
                echo "$session"
                return 0
            fi
        done <<< "$sessions"
        return 1
    fi

    if [[ "$role" == "reviewer" ]]; then
        for candidate in reviewer SelfLearn-reviewer reviewer-try; do
            if echo "$sessions" | grep -Fxq "$candidate"; then
                echo "$candidate"
                return 0
            fi
        done
        while IFS= read -r session; do
            [[ -z "$session" ]] && continue
            if [[ "$session" == *reviewer* ]]; then
                echo "$session"
                return 0
            fi
        done <<< "$sessions"
        return 1
    fi

    return 1
}

# Resolve configured session to an existing tmux session (with role-based fallback)
resolve_target_session() {
    local desired="$1"
    if tmux has-session -t "$desired" 2>/dev/null; then
        echo "$desired"
        return 0
    fi

    local role=""
    if [[ "$desired" == "$CREATOR_SESSION" ]]; then
        role="creator"
    elif [[ "$desired" == "$REVIEWER_SESSION" ]]; then
        role="reviewer"
    fi

    [[ -z "$role" ]] && return 1

    local fallback
    fallback=$(discover_session_by_role "$role" 2>/dev/null || true)
    if [[ -n "$fallback" ]]; then
        echo "[gh-notify] WARN: session '$desired' not found, fallback to '$fallback'" >&2
        echo "$fallback"
        return 0
    fi

    return 1
}

# Send a message to a tmux session, or queue it
notify_session() {
    local session="$1"
    local message="$2"
    local resolved
    resolved=$(resolve_target_session "$session" || true)

    if [[ -z "$resolved" ]]; then
        local unresolved_queue
        unresolved_queue=$(queue_file_path "$session")
        echo "$message" >> "$unresolved_queue"
        echo "[gh-notify] WARN: target '$session' missing; queued to $unresolved_queue"
        return 0
    fi

    local queue_file
    queue_file=$(queue_file_path "$resolved")

    if is_idle "$resolved"; then
        tmux send-keys -t "$resolved" "$message" Enter || true
        echo "[gh-notify] Sent to $resolved: $message"
    else
        echo "$message" >> "$queue_file"
        echo "[gh-notify] Queued for $resolved: $message"
    fi
}

# Flush queued messages for a session
flush_queue() {
    local session="$1"
    local resolved
    resolved=$(resolve_target_session "$session" || true)
    [[ -z "$resolved" ]] && return 0

    if ! is_idle "$resolved"; then
        return 0  # still busy
    fi

    local primary_queue resolved_queue role_pattern
    primary_queue=$(queue_file_path "$session")
    resolved_queue=$(queue_file_path "$resolved")
    role_pattern=""
    if [[ "$session" == "$CREATOR_SESSION" ]]; then
        role_pattern="queue_*creator*.txt"
    elif [[ "$session" == "$REVIEWER_SESSION" ]]; then
        role_pattern="queue_*reviewer*.txt"
    fi

    local queue_files=("$primary_queue" "$resolved_queue")
    if [[ -n "$role_pattern" ]]; then
        while IFS= read -r extra_queue; do
            queue_files+=("$extra_queue")
        done < <(find "$STATE_DIR" -maxdepth 1 -type f -name "$role_pattern" -print 2>/dev/null || true)
    fi

    for queue_file in "${queue_files[@]}"; do
        [[ ! -f "$queue_file" ]] && continue
        [[ ! -s "$queue_file" ]] && continue

        # Merge similar notifications to avoid spam
        local count
        count=$(wc -l < "$queue_file" | tr -d ' ') || { echo "[gh-notify] WARN: flush_queue count failed"; continue; }
        if [[ "$count" -gt 3 ]]; then
            local merged="[通知] 你有 ${count} 条积压通知，请查看 GitHub Issues/PRs"
            tmux send-keys -t "$resolved" "$merged" Enter || { echo "[gh-notify] WARN: flush send failed"; continue; }
            echo "[gh-notify] Flushed $count queued messages to $resolved (merged)"
        else
            while IFS= read -r line; do
                tmux send-keys -t "$resolved" "$line" Enter || true
            done < "$queue_file"
            echo "[gh-notify] Flushed $count queued messages to $resolved"
        fi

        rm -f "$queue_file"
    done
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
    if [[ "$current" != "[]" ]]; then
        echo "$current" > "$state_file"
    fi
    return 0
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
    if [[ "$current" != "[]" ]]; then
        echo "$current" > "$state_file"
    fi
    return 0
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
    if [[ "$current" != "[]" ]]; then
        echo "$current" > "$state_file"
    fi
    return 0
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
    if [[ "$current" != "[]" ]]; then
        echo "$current" > "$state_file"
    fi
    return 0
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
