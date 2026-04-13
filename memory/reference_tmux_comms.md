---
name: tmux Communication Protocol
description: How to notify via tmux send-keys, session groups, idle detection
type: reference
---

## Tmux Session 结构

**Session 组名** (优先使用，更稳定):
- Reviewer 组: `reviewer`
- Creator 组: `creator`

**当前活跃 Session**:
- `reviewer-0` → 组 `reviewer`
- `creator-1` → 组 `creator`

> **重要**: Session 名称可能动态变化 (如 reviewer-0, reviewer-1)，但组名固定。**优先使用组名**。

---

## 通知方式

### Reviewer → Creator

```bash
# 推荐：使用组名（稳定）
tmux send-keys -t creator "[Reviewer 通知] message" Enter

# 或指定具体 session
tmux send-keys -t creator-1 "[Reviewer 通知] message" Enter
```

### Creator → Reviewer

```bash
# 推荐：使用组名（稳定）
tmux send-keys -t reviewer "[Creator 通知] message" Enter

# 或指定具体 session
tmux send-keys -t reviewer-0 "[Creator 通知] message" Enter
```

---

## 检查对方是否空闲

发送前检查目标 session 最后一行是否包含 `❯`：

```bash
# 检查 Creator
tmux capture-pane -t creator -p | grep -v '^$' | tail -1

# 检查 Reviewer
tmux capture-pane -t reviewer -p | grep -v '^$' | tail -1
```

---

## 队列机制（如果对方忙碌）

```bash
# Creator 通知队列
echo "[通知内容]" >> /tmp/gh-notify/queue_reviewer.txt

# Reviewer 通知队列
echo "[通知内容]" >> /tmp/gh-notify/queue_creator.txt
```

---

## 完整示例

```bash
# 1. 检查 Reviewer 是否空闲
IDLE_CHECK=$(tmux capture-pane -t reviewer -p | grep -v '^$' | tail -1)

# 2. 如果空闲（包含 ❯），直接发送
if echo "$IDLE_CHECK" | grep -q "❯"; then
  tmux send-keys -t reviewer "[Creator 通知] PR #203 修复完成" Enter
else
  # 3. 如果忙碌，写入队列
  echo "[Creator 通知] PR #203 修复完成" >> /tmp/gh-notify/queue_reviewer.txt
fi
```

---

## Notification Daemon

自动守护脚本监听队列文件：
- 运行 session: `gh-notify`
- 脚本路径: `scripts/gh-notify-daemon.sh`
- 启动命令: `tmux new-session -d -s gh-notify "bash scripts/gh-notify-daemon.sh"`
