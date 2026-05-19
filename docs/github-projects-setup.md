# GitHub Projects 设置指南

本指南说明如何将 **Self_Learning-System** 仓库关联到 GitHub Projects 看板，以便统一追踪 Issue、PR 和里程碑进度。

---

## 一、创建 GitHub Project

1. 打开仓库主页 `https://github.com/ICEY4040727/Self_Learning-System`
2. 点击顶部导航栏 **Projects** → **New project**
3. 选择模板（推荐 **Board** 看板视图，也可选 Table 或 Roadmap）
4. 填写项目名称，例如 `Self_Learning-System v1.0.0`，点击 **Create project**

---

## 二、将仓库关联到 Project

1. 在项目页面点击右上角 **⚙ Settings**
2. 左侧菜单选择 **Manage access** → **Add repository**
3. 搜索并选择 `ICEY4040727/Self_Learning-System`，点击 **Add**

关联后可在看板中手动添加 Issue / PR，也可通过自动化工作流（见第四节）自动添加。

---

## 三、配置看板列（Status 字段）

推荐与现有 Issue 状态对齐：

| 列名 | 说明 |
|------|------|
| `Backlog` | 已创建但未开工的 Issue |
| `In Progress` | Creator 正在开发的任务 |
| `In Review` | PR 已提交，等待 Reviewer 审查 |
| `Done` | PR 已合并，Issue 已关闭 |

在 **Settings → Fields** 中新增或修改 `Status` 选项，使其与上表对应。

---

## 四、自动化：新 Issue / PR 自动入项目

仓库内已内置工作流 `.github/workflows/project-automation.yml`，可自动将新建的 Issue 和 PR 加入项目看板。

### 4.1 配置步骤

#### 步骤一：获取项目 URL

打开刚创建的 Project 页面，URL 格式为：

```
https://github.com/users/ICEY4040727/projects/<PROJECT_NUMBER>
```

记下 `PROJECT_NUMBER`（如 `1`）。

#### 步骤二：创建 Personal Access Token (PAT)

1. 点击右上角头像 → **Settings**（用户设置，非仓库设置）→ **Developer settings → Personal access tokens → Fine-grained tokens**
2. 点击 **Generate new token**
3. 设置 Token 名称（如 `project-automation`），有效期按需选择
4. **Repository permissions**：`Issues (Read)`、`Pull requests (Read)`（工作流通过 GITHUB_TOKEN 读取 Issue/PR，PAT 仅需读权限）
5. **Organization permissions** 或 **User permissions**：`Projects (Read and write)`（PAT 需要写入 Project 的权限）
6. 生成后复制 token 值（仅显示一次）

#### 步骤三：添加 Repository Secret

1. 进入仓库 **Settings → Secrets and variables → Actions**
2. 点击 **New repository secret**
3. Name: `PROJECT_TOKEN`，Value: 粘贴上一步的 token
4. 点击 **Add secret**

#### 步骤四：修改工作流配置

编辑 `.github/workflows/project-automation.yml`，将以下占位符替换为实际值：

```yaml
project-url: https://github.com/users/ICEY4040727/projects/<PROJECT_NUMBER>
```

将 `<PROJECT_NUMBER>` 替换为步骤一中记下的编号。

---

## 五、手动将现有 Issue 批量加入 Project

对于已有的 Open Issue，可通过 GitHub CLI 批量添加：

```bash
# 安装 GitHub CLI（已安装可跳过）
brew install gh   # macOS
# 或 https://cli.github.com/

# 登录
gh auth login

# 批量将 Open Issue 加入 Project（替换 <PROJECT_NUMBER> 为实际编号）
gh issue list --repo ICEY4040727/Self_Learning-System --state open --limit 100 \
  --json number,url --jq '.[].url' | \
  xargs -I{} gh project item-add <PROJECT_NUMBER> \
    --owner ICEY4040727 --url {}

# 注意：<PROJECT_NUMBER> 必须替换为第一节步骤一中记下的编号（如 1）。
```

---

## 六、视图推荐

| 视图 | 用途 |
|------|------|
| **Board（看板）** | 日常任务流转，直观查看 In Progress / Review / Done |
| **Table（表格）** | 批量编辑优先级、Assignee、里程碑 |
| **Roadmap（路线图）** | 按时间轴查看 Milestone v1.0.0 进度 |

---

## 七、与现有工作流的关系

本仓库采用 **Owner / Creator / Reviewer 三角色协作**（详见 `CONTRIBUTING.md`）。GitHub Projects 作为任务看板，补充了原有的 Issue + Label 机制：

- Issue 由 Owner 创建并标记 `approved` → Creator 在看板中将卡片移至 `In Progress`
- Creator 提 PR 并标记 `needs-review` → 看板卡片移至 `In Review`
- Reviewer 审查通过、Owner 合并 → 看板自动关闭为 `Done`（依赖自动化工作流）
