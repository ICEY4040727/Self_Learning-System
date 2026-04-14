#!/usr/bin/env python3
"""
Phase 1.5 DD1: TeacherPersona 数据迁移脚本

此脚本将 TeacherPersona 表中的数据迁移到 Character 表。
迁移完成后，TeacherPersona 表可以被删除。

迁移逻辑:
1. 对于每个 TeacherPersona 记录，找到对应的 Character
2. 将 TeacherPersona 的 traits, system_prompt_template 复制到 Character
3. 如果 TeacherPersona.is_active=True，设置 Character.is_active=True

向后兼容:
- Session.teacher_persona_id 字段保留，但不再用于查询
- 新代码直接使用 sage_character_id + Character 的字段

执行方式:
    python scripts/migrate_teacher_persona_to_character.py

危险操作: 否 (此脚本不修改数据库，仅生成迁移 SQL)
"""

import argparse
import sys


def generate_migration_sql():
    """生成数据库迁移 SQL"""
    sql = """
-- =====================================================
-- Phase 1.5 DD1: TeacherPersona → Character 数据迁移
-- 
-- 此迁移将 TeacherPersona 表中的数据合并到 Character 表
-- 执行前请备份数据库！
-- =====================================================

-- 1. 迁移 traits 和 system_prompt_template 到 Character
UPDATE characters c
SET 
    traits = tp.traits,
    system_prompt_template = tp.system_prompt_template,
    template_name = tp.name,
    is_active = tp.is_active
FROM teacher_personas tp
WHERE tp.character_id = c.id;

-- 2. 对于没有对应 TeacherPersona 但有 sage 角色的 Character，设置默认 is_active=True
UPDATE characters c
SET is_active = TRUE
WHERE type = 'sage'
  AND is_active IS NULL
  AND NOT EXISTS (
      SELECT 1 FROM teacher_personas tp WHERE tp.character_id = c.id
  );

-- 3. (可选) 删除 teacher_personas 表 - 在确认迁移成功后执行
-- DROP TABLE IF EXISTS teacher_personas;

-- =====================================================
-- 回滚操作 (如需回滚)
-- =====================================================
-- 注意: traits/system_prompt_template 数据无法回滚，因为已覆盖
-- 回滚仅恢复 is_active 字段:
-- UPDATE characters SET is_active = TRUE WHERE type = 'sage';
"""
    return sql


def dry_run():
    """模拟运行 (不修改数据库)"""
    print("=" * 60)
    print("Phase 1.5 DD1: TeacherPersona → Character 数据迁移")
    print("=" * 60)
    print()
    print("⚠️  DRY RUN 模式 - 仅展示 SQL，不会修改数据库")
    print()
    print("迁移说明:")
    print("1. 将 TeacherPersona.traits → Character.traits")
    print("2. 将 TeacherPersona.system_prompt_template → Character.system_prompt_template")
    print("3. 将 TeacherPersona.name → Character.template_name")
    print("4. 将 TeacherPersona.is_active → Character.is_active")
    print("5. 为没有 TeacherPersona 的 sage 角色设置默认 is_active=True")
    print()
    print("生成的 SQL:")
    print("-" * 60)
    print(generate_migration_sql())
    print("-" * 60)
    print()
    print("✅ 预览完成。如需执行，请运行:")
    print("   python scripts/migrate_teacher_persona_to_character.py --execute")


def execute():
    """实际执行迁移"""
    print("=" * 60)
    print("Phase 1.5 DD1: TeacherPersona → Character 数据迁移")
    print("=" * 60)
    print()
    print("⚠️  即将执行数据库迁移!")
    print()
    print("请确保:")
    print("1. 已备份数据库")
    print("2. 已停止所有应用服务")
    print("3. 已运行 alembic upgrade head (确保新字段已添加)")
    print()
    print("生成的 SQL:")
    print("-" * 60)
    print(generate_migration_sql())
    print("-" * 60)
    print()
    print("请手动执行上述 SQL 或使用数据库客户端运行")
    print("迁移完成后，可以删除 teacher_personas 表:")
    print("   DROP TABLE IF EXISTS teacher_personas;")


def main():
    parser = argparse.ArgumentParser(
        description="Phase 1.5 DD1: TeacherPersona → Character 数据迁移脚本"
    )
    parser.add_argument(
        "--execute",
        action="store_true",
        help="执行迁移 (默认仅显示 SQL)"
    )
    args = parser.parse_args()

    if args.execute:
        execute()
    else:
        dry_run()


if __name__ == "__main__":
    main()
