"""Tests for scripts/check_user_llm_direct_writes.py AST scanner."""
from __future__ import annotations

import ast
import importlib.util
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
CHECKER_PATH = REPO_ROOT / "scripts" / "check_user_llm_direct_writes.py"


def _load_checker_module():
    spec = importlib.util.spec_from_file_location("check_user_llm_direct_writes", CHECKER_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    import sys
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


checker = _load_checker_module()


def _violations(source: str) -> list[checker.Violation]:
    tree = ast.parse(source)
    visitor = checker.UserLLMWriteVisitor()
    visitor.visit(tree)
    return visitor.violations


def test_detects_multiline_split_assignment():
    source = """
user.default_provider \\
    = "claude"
"""
    hits = _violations(source)
    assert len(hits) == 1
    assert "default_provider" in hits[0].message


def test_detects_parenthesized_base_assignment():
    source = """
(current_user).model = "gpt-4o"
"""
    hits = _violations(source)
    assert len(hits) == 1
    assert "model" in hits[0].message


def test_detects_alias_assignment_chain():
    source = """
u = user
v = u
v.temperature = 0.5
"""
    hits = _violations(source)
    assert len(hits) == 1
    assert "temperature" in hits[0].message


def test_detects_setattr_on_alias():
    source = """
u = current_user
setattr(u, "max_tokens", 1024)
"""
    hits = _violations(source)
    assert len(hits) == 1
    assert "max_tokens" in hits[0].message


def test_ignores_non_user_attribute_writes():
    source = """
config.model = "gpt-4o"
"""
    hits = _violations(source)
    assert hits == []


def test_ignores_write_gateway_file():
    hits = checker._scan_file(checker.WRITE_GATEWAY)
    assert hits == []


def test_flags_direct_user_root_write():
    hits = _violations("user.default_provider = 'claude'")
    assert len(hits) == 1
    assert "default_provider" in hits[0].message
