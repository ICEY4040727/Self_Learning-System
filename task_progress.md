# P1 #183 存储结构重设计 - 任务清单

**状态**: 进行中
**依赖**: P0 #175 Alembic 双 head 合并 ✅ 已完成

## 任务清单

### 阶段一：数据库模型更新
- [ ] 1. 更新 `models/models.py`:
  - 添加 `MemoryFact` 模型
  - 添加 `SaveSnapshot` 模型
  - 删除 `Knowledge` 模型
  - 更新 `World` 移除 knowledge relationship

### 阶段二：创建新服务
- [ ] 2. 创建 `services/memory_facts.py` - MemoryFact 表操作
- [ ] 3. 创建 `services/memory_extractor.py` - 记忆提取拦截逻辑
- [ ] 4. 创建 `services/prompt_builder/modules/memory_facts.py` - 从 memory_facts 读取

### 阶段三：删除旧文件
- [ ] 5. 删除 `services/knowledge.py`
- [ ] 6. 删除 `services/prompt_builder/modules/knowledge.py`
- [ ] 7. 删除 `services/prompt_builder/modules/memory_retrieval.py`

### 阶段四：Alembic 迁移
- [ ] 8. 创建迁移：添加 memory_facts 和 save_snapshots 表
- [ ] 9. 运行迁移验证

### 阶段五：learning_engine 更新
- [ ] 10. 更新 `services/learning_engine.py`:
  - 移除 knowledge_service 引用
  - 集成 memory_extractor
  - 更新 prompt_builder 调用

### 阶段六：前端调用点排查
- [ ] 11. 搜索前端 `/api/save`、`SaveLoad` 等引用
- [ ] 12. 清理不需要的 save 相关前端代码

### 阶段七：测试验证
- [ ] 13. 运行 pytest 验证改动
- [ ] 14. 手动测试学习会话
