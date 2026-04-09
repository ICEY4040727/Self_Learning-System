---
name: tmux Communication Protocol
description: How to notify Creator via tmux send-keys, session names, idle detection
type: reference
---

**My tmux session**: `SelfLearn-reviewer`
**Creator's tmux session**: `SelfLearning-creator`
**Notification daemon**: `gh-notify` session running `scripts/gh-notify-daemon.sh`

**To notify Creator**:
```bash
tmux send-keys -t SelfLearning-creator "[Reviewer 通知] message" Enter
```

**Before sending, check if Creator is idle** (last line contains `❯`):
```bash
tmux capture-pane -t SelfLearning-creator -p | grep -v '^$' | tail -1
```

**If Creator is busy**: write to queue file `/tmp/gh-notify/queue_SelfLearning-creator.txt`

**Message prefix**: Always use `[Reviewer 通知]` prefix.
