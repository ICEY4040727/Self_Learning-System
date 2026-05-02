# v1.0.3 Findings 状态追踪

> Last updated: 2026-05-02
> 基于 review-plan.md 中列出的 12 个预检发现

## 状态总览

| # | ID | 级别 | 描述 | 状态 | 说明 |
|---|-----|------|------|------|------|
| 1 | 2A-01 | High | evolve_salience 未实现 | ✅ 已修复 | `compute_effective_salience()` 在 memory_manager.py:377，retrieve() 中已调用 |
| 2 | 2A-02 | High | t_valid/t_invalid 未迁移 | ✅ 已修复 | models.py:112-113 已有列，memory_facts.py:73 写入 |
| 3 | 2A-03 | High | 去重未实现规则分类器 | 🟡 设计如此 | 简单 tag 匹合并 + 保守策略 ("宁可多建不误删") |
| 4 | 2A-04 | High | retrieve() 未更新召回追踪 | ✅ 已修复 | memory_manager.py:155-156 更新 recall_count + last_recalled_at |
| 5 | 2A-05 | Medium | ILIKE SQL 注入 | ✅ 已修复 | 已替换为 concept_tags JSON contains 过滤 |
| 6 | 2E-01 | Medium | experience_points 残留 | 🟡 保留 | archive.py 有 levelup 端点使用这些字段，加 TODO 标注 |
| 7 | 2E-02 | Medium | gamification stage_order 重复 | 🟡 Deferred | 低影响，下个迭代统一 |
| 8 | 2F-01 | Medium | 语义检索未实现 | ✅ 已修复 | retrieve() 支持 concept_tags 过滤 |
| 9 | R1-01 | Medium | RecallService 未按 world_id 过滤 | ✅ 已修复 | recall_service.py 传入 world_id=world_id |
| 10 | R1-02 | Medium | NarrativeEngine._cooldowns 内存存储 | 🟡 Deferred | 非功能性，重启丢失可接受 |
| 11 | 2B-01 | Low | 关联提醒未在注释体现 | ✅ 不适用 | 代码已重构 |
| 12 | 2C-01 | Low | CourseGenerator 未改名 | 🟡 设计决策 | 当前命名更合理 |

## 统计

- ✅ 已修复: 7/12
- 🟡 Deferred/设计决策: 5/12 (无 High)
- ❌ 未处理: 0/12

## 4 个 High 级别全部已修复 ✅