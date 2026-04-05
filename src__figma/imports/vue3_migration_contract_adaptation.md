# vue3-migration 契约适配清单（含后端代码段）

## 结论

`/vue3-migration` 可复用的是页面与交互表现层；`router / api client / stores` 不能直接替换现网，需先完成以下契约适配。

## 适配清单总览

| # | 适配项 | 迁移代码现状 | 需要改造 |
|---|---|---|---|
| 1 | 鉴权 token 键名与登录态恢复 | 使用 `access_token` 流程 | 对齐现网鉴权存储与恢复流程 |
| 2 | Settings 后端字段边界 | 混入大量本地偏好字段 | 仅 `default_provider/api_key` 走后端 |
| 3 | Provider 枚举值 | 使用 `ollama` | 对齐后端 `local`（或后端扩展） |
| 4 | Learning Chat 请求/响应契约 | 请求 `{content}`，响应按 `choices`/字符串 `emotion` | 对齐 `{message}` 与后端 `ChatResponse` 结构 |
| 5 | Learning 启动/历史恢复链路 | 路由参数组织不一致 | 对齐 `/courses/{id}/start` 与 `/sessions/{id}/history` |
| 6 | Checkpoint 分叉返回值链路 | 已有分叉逻辑但字段接线不稳 | 对齐 `session_id/course_id/world_id` 返回 |
| 7 | 日记创建 payload | 缺 `course_id` | 补齐 `course_id` 且遵守课程归属校验 |
| 8 | 课程/角色/人格/世界绑定接口 | 基本可对齐但需逐项回归 | 严格按后端字段与错误语义对接 |
| 9 | 立绘上传约束 | 需确保上传命名/类型/大小一致 | 对齐后端表达名、MIME 与 2MB 限制 |

---

## 1) 鉴权 token 键名与登录态恢复

**后端代码段落：** `backend/api/routes/auth.py:62-112`

```python
@router.post("/login", response_model=Token)
@_rate_limit
def login(request: Request, form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == form_data.username).first()
    if not user or not verify_password(form_data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token = create_access_token(
        data={"user_id": user.id, "username": user.username}
    )
    return {"access_token": access_token, "token_type": "bearer"}


@router.get("/me", response_model=UserResponse)
def read_users_me(current_user: User = Depends(get_current_user)):
    return current_user
```

**适配要点：**
- 前端登录态读取/写入流程必须与现网一致（避免 token key 不一致导致刷新后掉线）。

---

## 2) Settings 字段边界 + Provider 枚举

**后端代码段落 A：** `backend/api/routes/archive.py:1039-1072`

```python
class SettingsUpdate(BaseModel):
    default_provider: str | None = None
    api_key: str | None = None


class SettingsResponse(BaseModel):
    default_provider: str | None = None


@router.get("/settings", response_model=SettingsResponse)
def get_settings(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return SettingsResponse(
        default_provider=current_user.default_provider
    )


@router.put("/settings")
def update_settings(
    settings: SettingsUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if settings.default_provider:
        current_user.default_provider = settings.default_provider

    if settings.api_key:
        from backend.core.security import encrypt_api_key
        current_user.encrypted_api_key = encrypt_api_key(settings.api_key)

    db.commit()
    return {"message": "Settings updated"}
```

**后端代码段落 B：** `backend/services/llm/adapter.py:222-237`

```python
def get_llm_adapter(provider: str = "claude") -> LLMAdapter:
    if provider == "claude":
        ...
    elif provider == "openai":
        ...
    elif provider == "local":
        return LocalAdapter()
    else:
        return ClaudeAdapter()
```

**适配要点：**
- `/api/settings` 仅同步 `default_provider/api_key`；本地 UI 偏好保留在 localStorage。
- Provider 值必须和后端适配器保持一致（当前后端使用 `local`）。

---

## 3) Learning Chat 请求/响应契约

**后端代码段落：** `backend/api/routes/learning.py:28-40,189-195,257-265`

```python
class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=5000)


class ChatResponse(BaseModel):
    type: str  # text, tool_request, choice
    reply: str
    choices: list[str] | None = None
    emotion: dict | None = None
    relationship_stage: str | None = None
    relationship: dict | None = None
    relationship_events: list[dict] | None = None
    expression_hint: str | None = None


@router.post("/courses/{course_id}/chat", response_model=ChatResponse)
async def send_message(
    course_id: int,
    chat_request: ChatRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    ...
    return ChatResponse(
        type=result.get("type", "text"),
        reply=result.get("reply", ""),
        emotion=result.get("emotion"),
        relationship_stage=result.get("relationship_stage"),
        relationship=result.get("relationship"),
        relationship_events=result.get("relationship_events"),
        expression_hint=expression,
    )
```

**适配要点：**
- 请求体改为 `{ message }`，不要发 `{ content }`。
- `type` 兼容 `choice`，`emotion` 按对象解析，`choices` 字段按可选处理。

---

## 4) Learning 启动/历史恢复链路

**后端代码段落 A：** `backend/api/routes/learning.py:76-123`

```python
@router.post("/courses/{course_id}/start")
async def start_learning(course_id: int, ...):
    ...
    return {
        "session_id": existing.id,
        "teacher_persona": teacher_persona.name if teacher_persona else None,
        "course": course.name,
        "relationship_stage": stage,
        "relationship": relationship,
        "greeting": _get_greeting(stage, teacher_persona.name if teacher_persona else None),
        "scenes": course.world.scenes if course.world and course.world.scenes else {},
        "sage_sprites": sage_character.sprites if sage_character else None,
        "traveler_sprites": traveler_character.sprites if traveler_character else None,
        "character_sprites": sage_character.sprites if sage_character else None,
    }
```

**后端代码段落 B：** `backend/api/routes/learning.py:305-330`

```python
@router.get("/sessions/{session_id}/history")
async def get_history(session_id: int, ...):
    ...
    return [
        {
            "id": m.id,
            "sender_type": m.sender_type,
            "content": m.content,
            "timestamp": m.timestamp
        }
        for m in messages
    ]
```

**适配要点：**
- 前端学习页入口、会话恢复、消息映射都应以上述路径和字段为准。

---

## 5) Checkpoint 分叉返回值链路

**后端代码段落：** `backend/api/routes/save.py:157-266`

```python
@router.post("/checkpoints/{checkpoint_id}/branch")
async def branch_from_checkpoint(...):
    ...
    return {
        "session_id": new_session.id,
        "course_id": new_session.course_id,
        "world_id": new_session.world_id,
        "parent_checkpoint_id": new_session.parent_checkpoint_id,
        "branch_name": new_session.branch_name,
    }
```

**适配要点：**
- 前端分叉后跳转必须消费 `session_id/course_id/world_id`，避免状态不完整导致恢复失败。

---

## 6) 日记创建 payload（必须含 course_id）

**后端代码段落 A：** `backend/api/routes/archive.py:139-143`

```python
class LearningDiaryCreate(BaseModel):
    course_id: int
    date: datetime
    content: str
    reflection: str | None = None
```

**后端代码段落 B：** `backend/api/routes/archive.py:831-851`

```python
@router.post("/learning_diary", response_model=LearningDiaryResponse)
def create_learning_diary(diary: LearningDiaryCreate, ...):
    course = db.query(Course).join(World, Course.world_id == World.id).filter(
        Course.id == diary.course_id,
        World.user_id == current_user.id,
    ).first()
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")

    db_diary = LearningDiary(**diary.model_dump(), user_id=current_user.id)
    ...
```

**适配要点：**
- Archive 提交日记时必须携带 `course_id`，否则无法通过后端归属校验。

---

## 7) 课程/角色/人格/世界绑定接口（逐项回归）

**后端代码段落 A：** `backend/api/routes/archive.py:359-404`（世界-角色绑定）

```python
@router.post("/worlds/{world_id}/characters", response_model=WorldCharacterResponse)
def create_world_character(world_id: int, wc: WorldCharacterCreate, ...):
    ...
    existing = db.query(WorldCharacter).filter(
        WorldCharacter.world_id == world_id,
        WorldCharacter.character_id == wc.character_id,
    ).first()
    if existing:
        raise HTTPException(status_code=409, detail="Character already bound to this world")
    ...
```

**后端代码段落 B：** `backend/api/routes/archive.py:704-827`（世界-课程与课程 CRUD）

```python
@router.post("/worlds/{world_id}/courses", response_model=CourseResponse)
def create_world_course(world_id: int, course: CourseInWorldCreate, ...):
    return create_course(
        CourseCreate(
            world_id=world_id,
            name=course.name,
            description=course.description,
            target_level=course.target_level,
        ),
        db,
        current_user,
    )


@router.get("/courses/{course_id}", response_model=CourseResponse)
def get_course(course_id: int, ...):
    ...
```

**后端代码段落 C：** `backend/api/routes/archive.py:1103-1133`（人格生成入口依赖 settings）

```python
@router.post("/persona/generate", response_model=PersonaGenerateResponse)
async def generate_persona(req: PersonaGenerateRequest, current_user: User = Depends(get_current_user)):
    ...
    provider = current_user.default_provider or "claude"
    ...
    if not user_api_key:
        raise HTTPException(status_code=400, detail="请先在设置页配置 API Key")

    adapter = get_llm_adapter(provider)
    ...
```

**适配要点：**
- 创建/编辑流程要完整匹配后端字段与错误语义（404/409/400）。
- 人格生成链路依赖 settings 中 provider/api_key。

---

## 8) 立绘上传约束

**后端代码段落：** `backend/api/routes/archive.py:471-533`

```python
@router.post("/characters/{character_id}/sprites")
async def upload_sprites(character_id: int, files: list[UploadFile], ...):
    """Upload character expression sprites. Filenames must be default/happy/thinking/concerned."""
    ...
    for file in files:
        name_stem = Path(file.filename or "").stem
        if name_stem not in ALLOWED_EXPRESSIONS:
            raise HTTPException(status_code=422, detail=f"文件名 '{file.filename}' 无效...")

        if file.content_type not in ALLOWED_MIME_TYPES:
            raise HTTPException(status_code=422, detail=f"文件类型 '{file.content_type}' 不支持...")

        content = await file.read()
        if len(content) > MAX_FILE_SIZE:
            raise HTTPException(status_code=413, detail=f"文件 '{file.filename}' 超过 2MB 限制")
    ...
```

**适配要点：**
- 前端上传组件需要在提交前做同等校验（表达名、MIME、大小），避免后端拒绝。

