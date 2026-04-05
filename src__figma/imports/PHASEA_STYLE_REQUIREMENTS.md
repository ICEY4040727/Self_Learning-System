# Phase A 样式返工需求说明（Owner 手改版）

## 背景

当前 PR #170（Closes #163）已通过功能与证据门槛，但 **Owner 对视觉效果不满意**。  
本目录用于 Owner 手工调整样式后，交由 Creator 按结果重新提交 PR 与截图证据。

## 返工目标

以 `/vue3-migration` 的视觉体验为基线，提升以下内容的一致性与完成度：

1. 共享样式基座（色板、圆角、阴影、模糊、动效节奏）更统一。  
2. DialogBox / HudBar / BacklogPanel / CheckpointPanel 的视觉语言一致。  
3. Learning 页面对话层与 HUD 的层级关系、过渡质感更自然。  
4. 整体观感达到 Owner 预期（不是“仅能用”，而是“风格到位”）。

## 本包内容

- 本次 PR #170 的全部改动文件副本（见 `CHANGED_FILES_FROM_PR170.txt`）。
- 包含源码、e2e 用例与证据文件（日志/截图）。

## 约束（不得破坏）

1. 不改后端接口契约与业务语义（仅样式/表现层返工）。  
2. 不回退 world-first、checkpoint、relationship/emotion、knowledge-graph 主链路。  
3. 对话框过渡继续遵守 transform-only 原则，避免 backdrop-filter 闪烁问题。  
4. 若涉及交互细节调整，必须保证现有 e2e 关键流程仍可通过。

## Creator 二次提交要求（硬性）

重新提交 PR 时必须附以下证据（build+preview 口径）：

- `docs/evidence/issue-163/00-frontend-build.txt`
- `docs/evidence/issue-163/01-preview-startup.txt`
- `docs/evidence/issue-163/02-shared-components-dialog-hud.png`
- `docs/evidence/issue-163/02-shared-components-backlog-panel.png`
- `docs/evidence/issue-163/02-shared-components-checkpoint-panel.png`
- （如新增）补充对应截图与执行日志

并在 PR 描述中给出“截图 -> 改动点”映射；缺证据则按流程 Request changes。

