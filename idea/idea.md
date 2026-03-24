实践一个想法“基于苏格拉底教学法的个性化学习系统”
这个系统的核心是：用户自己设定ai人设，通过维护一套“角色系统+学习档案”来增进对某一知识领域的掌握
我准备了一套对这个系统的设定，发送给claudecode后，它向我提出了三个问题，“老师的设定（动漫人物，历史人物，自己设定，随机）”“学习的科目和希望达到的效果”“学习的科目和希望达到的效果”然后可以稳定的自动生成一系列后期需要维护的档案.除了角色档案之外，再维护“群聊”“教案”“学习日记”“学习进度追踪”这几个文件.准备开始学习的时候，发送system。md作为system prompt，给出开始信号.然后可以进行互动式的学习.我做一个ui(can kao WebGAL)，让整个过程独立于vscode外进行，应该会更易用.我还想把这个信息传递的过程从文字拓展到语音，像豆包的界面可以语音交流.用llm模拟两个人之间长期的关系演变，我在想能不能用类似状态机的动态分析，＋动态的prompt注入，来实现.实现更高级别的模拟和仿真比如Mirofish. 更好的是网页,尤其考虑多租户.方便,想搞客户端就加一个Electron的壳就行.保障跨平台一致性和效果.网页你可以直接Chrome MCP一把梭.idea

![进行互动式的学习](image-1.png)
![然后可以稳定的自动生成一系列后期需要维护的档案](image.png)

# 基于苏格拉底教学法的个性化学习系统 - 实施计划

## 一、项目概述

### 1.1 背景与目标

构建一个基于苏格拉底教学法的个性化学习系统，用户通过设定AI人设维护"角色系统+学习档案"来增进对知识领域的掌握。系统提供类Galgame的沉浸式交互体验，支持多租户部署和多种LLM后端。

**核心特性**：

- 动态提示词构建（结合教师人格、关系阶段、记忆检索）
- 情感分析与关系阶段演进
- 类Galgame沉浸式UI

### 1.2 技术栈

- **前端**: Vue 3 + Vite + TypeScript
- **后端**: Python FastAPI
- **数据库**: PostgreSQL (主数据) + ChromaDB (向量知识库)
- **LLM**: 多种后端可配置 (Claude/OpenAI/本地模型)
- **部署**: Docker 多租户Web服务

### 1.3 多租户说明

- **初期**：单租户模式（个人使用）
- **扩展性**：数据库设计兼容多租户，为企业版/学校版预留

---

## 二、系统架构

### 2.1 整体架构

```
┌─────────────────────────────────────────────────────────────────┐
│                        Vue 3 Frontend                          │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────────────┐  │
│  │ 学习页面  │ │ 档案管理  │ │ 角色设定  │ │   进度追踪      │  │
│  │(Galgame) │ │          │ │          │ │                  │  │
│  └────┬─────┘ └────┬─────┘ └────┬─────┘ └────────┬─────────┘  │
└───────┼────────────┼────────────┼────────────────┼────────────┘
        │            │            │                │
        └────────────┴─────┬──────┴────────────────┘
                           │ REST API / WebSocket
        ┌──────────────────┼──────────────────┐
        │                  │                  │
┌───────┴───────┐  ┌───────┴───────┐  ┌───────┴───────┐
│  用户认证模块  │  │  学习引擎模块  │  │  档案管理模块  │
│  (多租户)     │  │  (Learning)   │  │  (CRUD)       │
│               │  │  动态分析模块  │  │               │
└───────┬───────┘  └───────┬───────┘  └───────┬───────┘
        │                  │                  │
┌───────┴──────────────────┴──────────────────┴───────┐
│                   PostgreSQL                          │
└───────────────────────────────────────────────────────┘
┌───────────────────────────────────────────────────────┐
│                   ChromaDB                             │
│           (知识向量库/对话历史嵌入)                      │
└───────────────────────────────────────────────────────┘
```

### 2.2 核心模块划分

| 模块                       | 职责                        |
| -------------------------- | --------------------------- |
| `backend/api`              | RESTful API + WebSocket端点 |
| `backend/auth`             | JWT多租户认证               |
| `backend/learning`         | 学习引擎（含动态提示词）    |
| `backend.dynamic_analyzer` | 情感分析、关系阶段演进      |
| `backend/memory`           | ChromaDB记忆检索            |
| `backend/llm`              | 多后端LLM适配器             |
| `backend/archive`          | 档案管理系统                |
| `frontend/src/views`       | 各业务页面                  |
| `frontend/src/components`  | Galgame UI组件              |

---

## 三、数据库设计

### 3.1 核心表结构

```sql
-- 租户/用户表（多租户兼容设计）
tenants (id, name, created_at)
users (id, tenant_id, username, password_hash, role,
      encrypted_api_key VARCHAR(255),  -- 用户自己的API Key（加密存储）
      default_provider VARCHAR(50),    -- 用户默认的LLM提供商
      created_at)

-- 角色系统
characters (id, tenant_id, user_id, name, avatar, personality, background, speech_style, created_at)

-- 【新增】教师人格配置（从 teacher_config.md 解析）
teacher_personas (
    id, tenant_id, character_id, name, version,
    traits JSON,          -- 性格特质
    system_prompt_template TEXT,  -- 系统提示词模板
    is_active BOOLEAN, created_at, updated_at
)

-- 【新增】学习者画像（从 learner_config.md 解析）
learner_profiles (
    id, tenant_id, user_id, subject_id,
    learning_style JSON,    -- 学习风格
    cognitive_traits JSON, -- 认知特质
    emotional_traits JSON, -- 情感特质
    knowledge_graph JSON,  -- 知识图谱
    created_at, updated_at
)

-- 学习档案
-- 【注】初期为简单的一对多关系(角色->科目)，后续可优化为多对多
subjects (id, tenant_id, character_id, name, description, target_level)
lesson_plans (id, subject_id, content, created_at)
learning_diaries (id, subject_id, user_id, date, content, reflection)
progress_tracking (id, subject_id, user_id, topic, mastery_level, last_review, next_review)

-- 对话消息（直接关联session，省略chats表简化结构）
chat_messages (
    id, session_id, sender_type, sender_id, content, timestamp,
    emotion_analysis JSON,   -- 情感分析结果
    used_memory_ids JSON     -- 引用的记忆IDs
)

-- 学习会话（增加关系阶段字段）
sessions (
    id, tenant_id, subject_id, user_id, started_at, ended_at,
    system_prompt, relationship_stage VARCHAR(20),  -- 【新增】关系阶段
    teacher_persona_id, learner_profile_id
)

-- 【新增】会话中的关系阶段快照
relationship_stages (
    id, session_id, stage VARCHAR(20), reason TEXT, updated_at
)

-- 存档表（对象存储 + 数据库索引）
saves (
    id, user_id, subject_id, session_id,
    save_name VARCHAR(100), created_at,
    file_path VARCHAR(255),  -- 指向存储的JSON文件路径
    memory_ids JSON          -- 记忆ID列表，避免重建
)

-- 存档JSON文件内容结构：
-- {
--   "session_meta": {"relationship_stage": "...", "teacher_persona_id": "..."},
--   "chat_history": [...],  -- 最近N条消息
--   "progress": {...},
--   "learner_profile_snapshot": {...},
--   "memory_ids": [...]     -- ChromaDB中的记忆ID列表
-- }

-- 读档时：
-- 1. 读取存档JSON文件恢复状态
-- 2. 根据memory_ids从ChromaDB直接检索已有记忆，避免重建
```

---

## 四、学习引擎设计

### 4.1 LearningEngine 核心逻辑

```python
class LearningEngine:
    """学习引擎 - 整合动态提示词、记忆检索、情感分析"""

    def __init__(self, session_id: str, llm_adapter, memory_store, dynamic_analyzer):
        self.session_id = session_id
        self.llm = llm_adapter
        self.memory = memory_store
        self.analyzer = dynamic_analyzer

    async def process_input(self, user_input: str) -> Response:
        """处理用户输入，返回响应"""

        # 1. 情感分析（调用动态分析模块）
        emotion = await self.analyzer.analyze_emotion(user_input)

        # 2. 检索相关记忆（ChromaDB向量检索）
        memories = await self.memory.retrieve(user_input, top_k=3)

        # 3. 构建动态Prompt
        system_prompt = await self.build_prompt(emotion, memories)

        # 4. 调用LLM
        reply = await self.llm.chat(system_prompt, user_input)

        # 5. 检查工具调用请求
        if self.has_tool_request(reply):
            return ToolRequestResponse(reply)

        # 6. 更新会话状态（关系阶段、学习者画像）
        await self.update_state(emotion, reply, memories)

        return TextResponse(reply)

    async def build_prompt(self, emotion: dict, memories: list) -> str:
        """动态组装系统提示词"""
        # 结合：教师人格模板 + 关系阶段 + 当前情感 + 检索记忆

    async def update_state(self, emotion: dict, reply: str, memories: list):
        """更新关系阶段和学习者画像"""
```

### 4.2 工具调用格式约定

在系统提示词中约定LLM返回工具调用的格式：

**方式一：JSON格式（推荐）**

```json
{
  "type": "tool_request",
  "tool": "search",
  "query": "导数定义",
  "reason": "学生不理解导数，需要补充资料"
}
```

**方式二：特殊标签**

```
<tool>search:导数定义</tool>
```

后端解析后返回 `ToolRequestResponse`，前端显示工具确认弹窗，用户确认后执行工具并将结果再次送给LLM生成最终回复。

### 4.3 API响应格式

```json
{
  "type": "text",
  "reply": "老师的回复内容...",
  "choices": ["选项A", "选项B"], // 可选，如果有选择题
  "emotion": { "valence": 0.8, "arousal": 0.5 },
  "relationship_stage": "friend"
}
```

### 4.2 动态分析模块

```python
class DynamicAnalyzer:
    """动态分析模块"""

    async def analyze_emotion(self, text: str) -> dict:
        """情感分析（使用snownlp或云端API）"""
        # 返回: {valence, arousal, emotion_type, confidence}

    async def update_relationship_stage(self, session_id: str, emotion: dict) -> str:
        """根据情感和互动深度更新关系阶段"""
        # 阶段: stranger -> acquaintance -> friend -> mentor -> partner

    async def update_learner_profile(self, user_id: str, interaction: dict):
        """更新学习者画像（薄弱点、兴趣等）"""
```

### 4.3 状态机流程

```
用户输入 ──┬──> 意图识别
          │
          ├──> 概念提取 ──> 问题生成 ──> LLM调用 ──> 输出响应
          │         │
          │         └──── 反馈分析 <─── 响应评估
          │                  │
          ▼                  ▼
          └──── 情感分析 ──> 关系阶段更新
                              │
                              ▼
                    更新学习者画像 + 存储记忆
```

---

## 五、前端设计 (Galgame风格)

### 5.1 核心页面

1. **登录/注册页** - 用户认证
2. **学习主页** - 角色选择、科目列表、进度概览
3. **学习交互页** - 核心Galgame式对话界面
4. **档案管理页** - 角色、教案、日记、进度管理
5. **角色设定页** - 创建/编辑AI人设

### 5.2 Galgame UI组件

| 组件                    | 功能                         |
| ----------------------- | ---------------------------- |
| `CharacterDisplay`      | 立绘显示、表情切换、位置控制 |
| `DialogBox`             | 对话框、姓名框、选项按钮     |
| `Background`            | 背景图切换、过渡动画         |
| `ChoicePanel`           | 多选项交互                   |
| `SaveLoad`              | 存档/读档界面                |
| `EmotionIndicator`      | 情感状态指示器               |
| **`ToolConfirmDialog`** | **工具确认弹窗（新增）**     |

### 5.3 存档/读档实现

```typescript
// 存档数据结构
interface SaveData {
  session_id: string;
  relationship_stage: string;
  teacher_persona_snapshot: TeacherPersona;
  learner_profile_snapshot: LearnerProfile;
  chat_history: ChatMessage[];
  current_topic: string;
  progress: ProgressTracking;
}

// 存档操作流程
// 1. 前端点击"存档"按钮
// 2. 后端将session相关状态打包为JSON
// 3. 存入saves表或文件存储
// 4. 读档时恢复状态 + 重建ChromaDB记忆
```

---

## 六、LLM适配层

### 6.1 多后端支持

```python
class LLMAdapter(ABC):
    @abstractmethod
    async def chat(self, messages: list, system_prompt: str) -> str:
        pass

    @abstractmethod
    async def chat_stream(self, messages: list, system_prompt: str) -> AsyncGenerator[str, None]:
        """流式返回token（后续优化）"""
        pass

class ClaudeAdapter(LLMAdapter):
    # Anthropic Claude API

class OpenAIAdapter(LLMAdapter):
    # OpenAI GPT API

class LocalAdapter(LLMAdapter):
    # 本地模型 (Ollama等)
```

### 6.2 配置结构

```yaml
llm:
  default_provider: "claude"
  providers:
    claude:
      enabled: true
      api_key: "${CLAUDE_API_KEY}"
      model: "claude-3-5-sonnet-20241022"
    openai:
      enabled: false
      api_key: "${OPENAI_API_KEY}"
      model: "gpt-4"

# 语音能力预留（暂不启用）
features:
  voice:
    enabled: false
    provider: "web_speech" # or "azure", "elevenlabs"
```

### 6.3 核心API端点

使用 FastAPI 的 APIRouter 组织路由，自动生成 OpenAPI 文档。

| 端点                        | 方法           | 说明                      |
| --------------------------- | -------------- | ------------------------- |
| `/api/auth/login`           | POST           | 登录，返回 JWT            |
| `/api/auth/register`        | POST           | 注册                      |
| `/api/character`            | GET/POST       | 角色列表/创建             |
| `/api/character/{id}`       | GET/PUT/DELETE | 角色详情/编辑/删除        |
| `/api/teacher_persona`      | GET/POST       | 教师人格配置              |
| `/api/teacher_persona/{id}` | GET/PUT/DELETE | 教师人格 CRUD             |
| `/api/learner_profile`      | GET/PUT        | 学习者画像获取/更新       |
| `/api/subjects`             | GET/POST       | 科目管理                  |
| `/api/subjects/{id}`        | GET/PUT/DELETE | 科目 CRUD                 |
| `/api/subjects/{id}/chat`   | POST           | 发送对话消息              |
| `/api/chat/tool_confirm`    | POST           | 确认工具调用              |
| `/api/save`                 | POST           | 创建存档                  |
| `/api/save`                 | GET            | 存档列表                  |
| `/api/save/{id}`            | GET            | 读取存档                  |
| `/api/voice`                | POST           | 语音输入（预留，返回501） |
| `/api/settings`             | GET/PUT        | 用户设置（API Key配置）   |

---

## 七、实施阶段

### 阶段一：基础框架 (1-2周)

- [ ] 项目初始化 (Vue 3 + FastAPI)
- [ ] 多租户认证系统 (JWT)
- [ ] 基础数据库模型（含动态分析表）
- [ ] RESTful API基础

### 阶段二：档案系统 (1周)

- [ ] 角色CRUD (人设设定)
- [ ] 教师人格配置 CRUD
- [ ] 学习者画像 CRUD
- [ ] 科目管理
- [ ] 学习日记
- [ ] 进度追踪

### 阶段三：学习引擎 + 动态分析 (2周)

- [ ] LLM适配层
- [ ] ChromaDB集成（记忆存储与检索）
- [ ] 动态分析模块（情感分析、关系阶段）
- [ ] LearningEngine核心逻辑
- [ ] 对话历史管理

### 阶段四：前端UI (2周)

- [ ] Galgame核心组件（含ToolConfirmDialog）
- [ ] 学习交互页
- [ ] 档案管理页
- [ ] 角色设定页

### 阶段五：完善与部署 (1周)

- [ ] 存档/读档功能（核心功能）
- [ ] 工具确认弹窗联调
- [ ] Docker部署配置
- [ ] 语音能力预留（端点+配置）
- [ ] 性能优化

---

## 八、关键文件清单

### 后端 (Python/FastAPI)

| 文件                                   | 说明                     |
| -------------------------------------- | ------------------------ |
| `backend/main.py`                      | 应用入口                 |
| `backend/api/routes/auth.py`           | 认证路由                 |
| `backend/api/routes/learning.py`       | 学习路由                 |
| `backend/api/routes/archive.py`        | 档案路由                 |
| `backend/api/routes/save.py`           | 存档/读档路由            |
| `backend/core/config.py`               | 配置管理                 |
| `backend/core/security.py`             | JWT安全                  |
| `backend/db/database.py`               | 数据库连接               |
| `backend/services/learning_engine.py`  | 学习引擎                 |
| `backend/services/dynamic_analyzer.py` | **动态分析模块（新增）** |
| `backend/services/memory.py`           | ChromaDB记忆服务         |
| `backend/services/llm/adapter.py`      | LLM适配器                |
| `backend/models/*.py`                  | SQLAlchemy模型           |

### 前端 (Vue 3)

| 文件                                                    | 说明                     |
| ------------------------------------------------------- | ------------------------ |
| `frontend/src/App.vue`                                  | 根组件                   |
| `frontend/src/router/index.ts`                          | 路由配置                 |
| `frontend/src/views/Login.vue`                          | 登录页                   |
| `frontend/src/views/Home.vue`                           | 主页                     |
| `frontend/src/views/Learning.vue`                       | 学习交互页               |
| `frontend/src/views/Archive.vue`                        | 档案管理                 |
| `frontend/src/views/Character.vue`                      | 角色设定                 |
| `frontend/src/views/Settings.vue`                       | 用户设置（API Key配置）  |
| `frontend/src/components/galgame/CharacterDisplay.vue`  | 立绘组件                 |
| `frontend/src/components/galgame/DialogBox.vue`         | 对话框组件               |
| `frontend/src/components/galgame/ChoicePanel.vue`       | 选项面板                 |
| `frontend/src/components/galgame/SaveLoad.vue`          | 存档/读档                |
| `frontend/src/components/galgame/ToolConfirmDialog.vue` | **工具确认弹窗（新增）** |
| `frontend/src/components/voice/VoiceInput.vue`          | 语音输入（预留，不激活） |

---

## 九、验证方案

### 9.1 功能测试

1. **用户认证**: 注册、登录、Token刷新
2. **角色系统**: 创建角色、编辑、删除、切换
3. **教师人格**: 创建、编辑、激活不同人格
4. **学习者画像**: 创建、更新、查看画像
5. **学习流程**: 开始学习 → 对话交互 → 情感分析 → 关系演进 → 记录进度
6. **档案管理**: CRUD各类型档案
7. **存档/读档**: 存档、读档、状态恢复

### 9.2 集成测试

1. 完整学习流程端到端测试
2. 动态提示词构建测试
3. ChromaDB记忆检索测试
4. LLM调用稳定性测试

### 9.3 部署验证

1. Docker容器构建成功
2. 数据库连接与迁移
3. WebSocket长连接稳定性

---

## 十、总结

本计划实现一个完整的基于苏格拉底教学法的个性化学习系统，具备：

- 类Galgame的沉浸式学习体验
- 动态提示词构建（教师人格 + 关系阶段 + 记忆检索）
- 情感分析与关系阶段演进
- 完整的档案管理系统（含教师人格、学习者画像）
- 存档/读档功能
- 工具确认弹窗
- 语音能力预留
- 多租户兼容架构
