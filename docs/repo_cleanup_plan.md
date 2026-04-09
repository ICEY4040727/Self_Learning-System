# 仓库清理与分支管理计划

> 制定日期：2026-04-08
> 当前分支：`feat/login-page-text-update`
> 主分支：`main`（本地落后 origin/main **53 commits**）

---

## 一、当前仓库状况快照

### 1.1 工作区状态（150 处变更，10 个未跟踪文件）

变更可以拆为 **5 个互相独立的逻辑组**：

| 组别 | 内容 | 文件示例 | 性质 |
|---|---|---|---|
| **A. 报表/画像新功能** | 新增图表组件 + ReportPage / UserProfile + 路由 + 引入 vue3-apexcharts | `frontend/src/components/{LearningStatsCards,MasteryTrendsChart,MetacognitionRadar,MilestoneList,PreferenceBars,RelationshipTimeline,WorldComparisonGrid}.vue`、`frontend/src/views/{ReportPage,UserProfile}.vue`、`main.ts`、`router/index.ts`、`package.json`、`package-lock.json` | feat |
| **B. WorldDetail API 修复** | checkpoints 接口由 `/courses/{id}/checkpoints` 改为 `/save?subject_id=...` | `frontend/src/views/WorldDetail.vue` | fix |
| **C. 角色/情绪组件微调** | CharacterSprite 与 EmotionTrajectory 修改 | `frontend/src/components/{CharacterSprite,EmotionTrajectory}.vue` | refactor/fix（需 diff 二次确认） |
| **D. 文档更新** | 删 `docs/persona_generate_design.md`、改 `docs/v1.0.0前后端联调修复/.../character_optimization_plan.md`、新增 `docs/archive_improvement_plan.md` | `docs/**` | docs |
| **E. 历史脚手架清理** | `paper2galgame/`（15 文件，~2k 行）+ `src__figma/`（~110 文件，~23k 行） | 全部 deleted | chore |
| **F. 子模块** | `skill-cowork` 子模块内部有未提交内容 | `skill-cowork` | 待二次确认 |

> A/B/C 已经在新建文件 + 修改文件层面无重叠，可独立提交。

### 1.2 分支状态

- **当前分支命名错位**：`feat/login-page-text-update` 实际包含 20+ commits，涵盖 角色管理优化、axios → client.ts 替换、Character 修复、LLM Phase 3 全套优化、记忆检索、模块化提示词注入器、Home 联调 等内容 —— **完全不是登录页文案改动**。
- **本地 main 落后 origin/main 53 个 commit**：极其危险，所有 rebase 前必须先同步。
- **大量"幽灵"本地分支**（远端已删除，标记为 `[gone]`）：
  - `feat/#125-delta-api-knowledge`、`feat/#127-cleanup-deploy-validation`、`feat/#129-world-knowledge-invariant`
  - `feat/141-ui-foundation`、`feat/142~146`、`feat/world-system-wip`
  - `fix/#124-delta-migration-gap`、`fix/#132-131-133-legacy-compat`
- **未合入的活跃分支**：
  - `feat/147-character-migration`、`feat/148-settings-migration`、`feat/149-regression-matrix`、`feat/163-shared-style-base`（均挂在 `.worktrees/`）
  - `fix/#130-world-character-api`（无远端，本地 `chore: remove .pyc and node_modules from git tracking`，含 stash）
- **PR 镜像分支**：`pr-136 ~ pr-170`、`pr-156-review` 等 review 用临时分支。
- **Stash**：`stash@{0}: On fix/#130-world-character-api: local edits on fix/#130 branch`。

---

## 二、目标

1. 工作区清空，所有变更进入语义清晰的 commit。
2. 本地 `main` 与 `origin/main` 同步。
3. 当前分支重命名为能反映其内容的名字，并基于最新 main rebase。
4. 删除全部远端已合并的本地"幽灵"分支与一次性 PR 镜像分支。
5. 子模块与 stash 妥善处理，无悬空状态。

---

## 三、执行步骤

> 每一步执行前先 `git status` 复核；任何 destructive 操作（`reset --hard`、`branch -D`、`push --force`）执行前 **必须** 由 Owner 二次确认。

### Step 0 — 安全网（最先做）

```bash
# 0.1 备份当前分支当前状态（含未提交变更也无影响，备份的是 HEAD）
git branch backup/login-page-text-update-2026-04-08 feat/login-page-text-update

# 0.2 看看 stash 内容是否还需要
git stash show -p stash@{0} | less
# 决策：保留 / 应用到 fix/#130 / 丢弃 → 记录在 PR 描述中
```

### Step 1 — 同步 main

```bash
git fetch origin --prune
git switch main
git merge --ff-only origin/main          # 必须 fast-forward；非 ff 说明本地 main 有脏 commit，需要排查
```

如果 `--ff-only` 失败：
```bash
git log --oneline origin/main..main      # 看本地 main 上多出来什么
# 若是误提交 → 用 git reset --hard origin/main（需 Owner 确认）
```

### Step 2 — 切回特性分支并 stash 全部工作区

```bash
git switch feat/login-page-text-update
git stash push -u -m "wip: A+B+C+D+E pending split 2026-04-08"
```

### Step 3 — 重命名当前分支（因为内容与名字严重不符）

实际内容主要是 **Character + LLM Phase3 + Home 联调**，建议拆为多分支后再处理。先重命名以避免 PR 时被 reviewer 误解：

```bash
git branch -m feat/login-page-text-update feat/character-llm-phase3-home
git push origin :feat/login-page-text-update                            # 删除远端旧名
git push -u origin feat/character-llm-phase3-home                        # 推送新名
```

> 若该分支已经有开放的 PR，先在 PR 页面更新分支再删除旧远端引用，避免 PR 自动 close。

### Step 4 — 拆 commit（按 1.1 的逻辑组）

恢复 stash 后逐组 `add` + `commit`：

```bash
git stash pop

# --- 组 E：历史脚手架清理（先做，体量最大、最独立） ---
git add -u paper2galgame/ src__figma/
git commit -m "chore: remove legacy paper2galgame and src__figma scaffolding"

# --- 组 D：文档 ---
git add -u docs/persona_generate_design.md \
           "docs/v1.0.0前后端联调修复/implementation/character_optimization_plan.md"
git add docs/archive_improvement_plan.md
git commit -m "docs: refresh character optimization plan and add archive improvement plan"

# --- 组 B：WorldDetail checkpoints 接口修复 ---
git add frontend/src/views/WorldDetail.vue
git commit -m "fix(world-detail): use /save endpoint for checkpoints listing"

# --- 组 C：角色/情绪组件微调（先 diff 确认是否真的独立） ---
git diff --staged frontend/src/components/CharacterSprite.vue \
                  frontend/src/components/EmotionTrajectory.vue
git add frontend/src/components/CharacterSprite.vue \
        frontend/src/components/EmotionTrajectory.vue
git commit -m "refactor(galgame): tweak CharacterSprite and EmotionTrajectory rendering"

# --- 组 A：报表/画像新功能（最大的 feat） ---
git add frontend/src/components/{LearningStatsCards,MasteryTrendsChart,MetacognitionRadar,MilestoneList,PreferenceBars,RelationshipTimeline,WorldComparisonGrid}.vue
git add frontend/src/views/{ReportPage,UserProfile}.vue
git add frontend/src/main.ts frontend/src/router/index.ts
git add frontend/package.json frontend/package-lock.json
git commit -m "feat(report): add learning report and user profile pages with chart components"
```

### Step 5 — 处理 skill-cowork 子模块

```bash
git submodule status
git -C skill-cowork status
# 若是无意修改 → 在子模块内 git restore .
# 若是有意修改 → 在子模块内单独提交并推送，再回主仓库 git add skill-cowork && git commit -m "chore: bump skill-cowork submodule"
```

### Step 6 — Interactive Rebase 整理 commit 历史

当前分支累计了 20+ commit，可在 rebase 时合并/重排：

```bash
git fetch origin
git rebase -i origin/main
```

在编辑器中：
- 把 LLM Phase 3 系列（041b5eb、4046365、50b8243、b1d87b8、7a3706c、20be3a6、31f6a2f、91aed99）`squash` 成 1~2 个总 commit。
- 把 axios → client.ts 替换、Character 修复、Home 联调 commit 按主题归类。
- 登录页历史细节 commit（多个 fix transition、绝对定位等）`fixup` 进对应主 commit。

> ⚠️ 该分支已有远端，rebase 后必须 `git push --force-with-lease`（**不要** `--force`），且只能在 Owner 确认无人 fork 后执行。

### Step 7 — 合并到 main

视分支体量决定合并方式：
- 单一主题且 commit 历史干净 → **PR + Merge commit**（保留分支历史）
- 多个独立主题混杂 → 在 GitHub UI 用 **Squash merge**

```bash
gh pr create --base main --head feat/character-llm-phase3-home \
  --title "feat: character/LLM-phase3/home integration bundle" \
  --body-file <(cat <<'EOF'
## Summary
- 角色管理功能优化（含 axios → client.ts 全局替换）
- LLM Phase 3 完整优化（缓存、SDK 迁移、Token 预算、模块化提示词注入器）
- Home 页前后端联调（characters/stats、avatar、levelup）
- 报表/画像新页面 + 历史脚手架清理

## Test plan
- [ ] frontend `npm run build` 通过
- [ ] backend `pytest` 通过
- [ ] /home /character /report /profile 路由手动回归
EOF
)
```

### Step 8 — 分支大扫除

#### 8.1 删除远端已合并的"幽灵"本地分支

```bash
# 先确认 [gone] 列表
git fetch -p
git branch -vv | awk '/: gone]/ {print $1}'

# 逐一确认 commit 已进 main 后再删
for b in feat/#125-delta-api-knowledge feat/#127-cleanup-deploy-validation \
         feat/#129-world-knowledge-invariant feat/141-ui-foundation \
         feat/world-system-wip fix/#124-delta-migration-gap \
         fix/#132-131-133-legacy-compat; do
  git log main --oneline --grep="$(git log -1 --format=%s "$b")" | head -1
done

# 确认无误后批量删除（-D 因为它们没有上游）
git branch -D feat/#125-delta-api-knowledge feat/#127-cleanup-deploy-validation \
              feat/#129-world-knowledge-invariant feat/141-ui-foundation \
              feat/world-system-wip fix/#124-delta-migration-gap \
              fix/#132-131-133-legacy-compat
```

#### 8.2 处理 worktree 中的 feat/142~149

```bash
git worktree list
# 已合入的：先 git worktree remove .worktrees/feat-14x，再 git branch -d feat/14x-...
# 未合入的（如 147/148/149/163）：保持现状或推动 PR
```

#### 8.3 清理 PR 镜像分支

`pr-136`、`pr-137`、`pr-138`、`pr-139`、`pr-140`、`pr-156-review`、`pr-170` 都是 reviewer 临时分支，确认对应 PR 状态后删除：

```bash
gh pr view 136 --json state,mergedAt
# merged → git branch -D pr-136
# closed/open → 保留或与 reviewer 沟通
```

#### 8.4 清理 stash

```bash
git stash list
git stash drop stash@{0}    # 已确认无价值后
```

---

## 四、风险与回滚

| 操作 | 风险 | 回滚手段 |
|---|---|---|
| `git reset --hard origin/main`（main 同步） | 丢失本地 main 上的私有 commit | 已在 Step 0 备份；reflog 可恢复 |
| `git rebase -i origin/main` | 解决冲突时误丢代码 | `backup/login-page-text-update-2026-04-08` 分支保底 |
| `git push --force-with-lease` | 覆盖远端他人 push | `--force-with-lease` 自带保护；先 `git fetch` |
| 删除幽灵分支 | 误删未合并工作 | 先 `git log main --grep` 验证，再删；reflog 30 天可恢复 |
| 删除 worktree | 丢失未提交修改 | `git worktree remove` 会拒绝有未提交修改的 worktree |

---

## 五、执行检查表

- [ ] Step 0 备份分支已建 + stash 内容已审阅
- [ ] Step 1 main 同步至 origin/main 53 个新 commit
- [ ] Step 2 工作区 stash 完成
- [ ] Step 3 分支重命名 + 远端同步
- [ ] Step 4 五个逻辑组分别成 commit
- [ ] Step 5 submodule 状态干净
- [ ] Step 6 rebase 后 commit 历史精简
- [ ] Step 7 PR 创建并合入 main
- [ ] Step 8 幽灵分支 / worktree / PR 镜像 / stash 全部清理
- [ ] 最终 `git status` 干净，`git branch -vv` 无 `[gone]`，`git worktree list` 仅保留活跃工作区

---

## 六、未决项决议（Owner 已确认 + 调研结果）

### Q1. `paper2galgame/` 与 `src__figma/` 删除？

**决议：可删除** —— 按 Step 4 的组 E 提交 `chore: remove legacy paper2galgame and src__figma scaffolding`。git 历史可追溯，无需额外备份。

### Q2. `feat/login-page-text-update` 的 PR 处理？

**决议：新建 PR** —— 不复用旧 PR。Step 3 的分支重命名照旧执行（`feat/login-page-text-update` → `feat/character-llm-phase3-home`），并 `git push origin :feat/login-page-text-update` 删除远端旧分支。Step 7 用 `gh pr create` 开一个新 PR。

### Q3. `fix/#130-world-character-api` 与其 stash？

**调研结果**：

- 分支 tip = `2a0cdb3 chore: remove .pyc and node_modules from git tracking`，与本地 main 是同一个 commit，**0 unmerged commits** —— 分支本身已无价值，**直接删除**。
- Stash 内容：修改 `CLAUDE.md` / `CONTRIBUTING.md`（把 PostgreSQL + ChromaDB 改成 SQLite 描述、更新 tmux session 名），删除 `docs/DEPLOYMENT.md`、`docs/persona_generate_design.md`、`first_work_record.md`、`idea/idea.md`。语义是 **"Phase 0 文档同步到 SQLite + 删除旧设计稿"**。
- 关键发现：核对 `origin/main`，**这些清理上游都还没合入**（origin/main 的 CLAUDE.md 仍写 "PostgreSQL + ChromaDB"，4 个待删文件仍存在）→ stash 有真实价值。

**决议**：

1. 删除 `fix/#130-world-character-api` 分支本身（已与 main 同 commit，无丢失风险）。
2. Stash 单独抢救：在 Step 1 同步完 main 后，新建 `chore/docs-sqlite-sync` 分支，`git stash apply stash@{0}`，处理潜在冲突，**单独开 PR**，不混入当前 bundle。
3. PR 合入后再 `git stash drop stash@{0}`。

```bash
# 删除分支
git branch -D fix/#130-world-character-api

# 抢救 stash
git switch -c chore/docs-sqlite-sync main           # main 必须先同步完成
git stash apply stash@{0}
git status                                          # 处理冲突
git add -A
git commit -m "chore(docs): sync CLAUDE.md and CONTRIBUTING.md to SQLite + remove legacy design docs"
git push -u origin chore/docs-sqlite-sync
gh pr create --base main --title "chore: docs sync to SQLite stack"
# 合入后
git stash drop stash@{0}
```

### Q4. worktree 中的 feat/147~149、163？

**调研结果**：

- `.worktrees/` 下共 **9 个 worktree**（feat-142~149 + feat-163），全部创建于 2026-04-05，是 Phase A 多 PR 切片产物（路由 / 登录 / Home / 学习 / 存档 / 角色 / 设置 / 回归矩阵 / 共享样式）。Owner 不记得用过 worktree，可能是当时实验性流程，现在已不需要。
- **feat/142~149 全部 0 unmerged commits**，已通过 PR #152~#162 合入 origin/main：

  ```text
  #152 feat/142-routing-semantics
  #153 feat/143-login-auth
  #154 feat/144-home-world-chain
  #155 feat/145-learning-scene
  #156 feat/146-archive-migration
  #158 feat/147-character-migration
  #161 feat/148-settings-migration
  #162 feat/149-regression-matrix
  ```

- **feat/163-shared-style-base 有 2 个领先 commit**（推测是 evidence/截图刷新，与原 PR 已合入的内容相比），需要人工裁决。
- 所有 worktree 工作区干净，无未提交修改。

**决议**：

1. **feat/142~149**：8 个 worktree + 8 个分支全部清理。

   ```bash
   for n in 142 143 144 145 146 147 148 149; do
     git worktree remove .worktrees/feat-$n
   done
   git branch -D feat/142-routing-semantics feat/143-login-auth feat/144-home-world-chain \
                 feat/145-learning-scene feat/146-archive-migration feat/147-character-migration \
                 feat/148-settings-migration feat/149-regression-matrix
   ```

2. **feat/163-shared-style-base**：先看那 2 个领先 commit 是什么，再决定丢弃 / 推 PR。

   ```bash
   git log origin/main..feat/163-shared-style-base --stat
   # 若只是截图/evidence 刷新且无人需要 → git worktree remove .worktrees/feat-163 && git branch -D feat/163-shared-style-base
   # 若有价值 → 推到远端单独开 PR
   ```

3. 最后清理空目录：`rmdir .worktrees`（如果全部 worktree 都已 remove）。
