#!/usr/bin/env python3
"""Fail when User LLM columns are assigned outside the write gateway.

Uses AST (not line regex) so multi-line splits, parenthesized bases, and
local aliases (u = user; u.field = ...) are detected.

See CONTRIBUTING.md § User LLM 设置写入规范.
"""
from __future__ import annotations

import ast
import sys
from dataclasses import dataclass, field
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]

WRITE_GATEWAY = REPO_ROOT / "backend" / "services" / "user_llm_settings.py"

ALLOWLIST_PREFIXES = (
    REPO_ROOT / "backend" / "tests",
    WRITE_GATEWAY,
)

SCAN_ROOTS = (
    REPO_ROOT / "backend",
    REPO_ROOT / "scripts",
)

SKIP_DIR_NAMES = frozenset({
    ".venv",
    "venv",
    "__pycache__",
    "node_modules",
    ".git",
})

KNOWN_USER_ROOT_NAMES = frozenset({
    "user",
    "current_user",
    "db_user",
    "existing_user",
})

FORBIDDEN_FIELDS = frozenset({
    "default_provider",
    "encrypted_api_key",
    "llm_provider_settings",
    "llm_base_url",
    "temperature",
    "max_tokens",
    "model",
})


@dataclass
class Violation:
    lineno: int
    message: str


@dataclass
class Scope:
    aliases: dict[str, str] = field(default_factory=dict)

    def clone(self) -> Scope:
        return Scope(aliases=dict(self.aliases))


class UserLLMWriteVisitor(ast.NodeVisitor):
    def __init__(self) -> None:
        self.scope_stack: list[Scope] = [Scope()]
        self.violations: list[Violation] = []

    @property
    def scope(self) -> Scope:
        return self.scope_stack[-1]

    def _push_scope(self, extra_roots: frozenset[str] | None = None) -> None:
        scope = self.scope.clone()
        for name in extra_roots or ():
            scope.aliases[name] = name
        self.scope_stack.append(scope)

    def _pop_scope(self) -> None:
        self.scope_stack.pop()

    def _canonical_user_root(self, name: str) -> str | None:
        if name in KNOWN_USER_ROOT_NAMES:
            return name
        return self.scope.aliases.get(name)

    def _resolve_user_root(self, node: ast.expr) -> str | None:
        if isinstance(node, ast.Name):
            return self._canonical_user_root(node.id)

        if isinstance(node, ast.Attribute):
            if node.attr in KNOWN_USER_ROOT_NAMES:
                return node.attr
            if node.attr == "user":
                inner = self._resolve_user_root(node.value)
                if inner:
                    return inner
            return self._resolve_user_root(node.value)

        if isinstance(node, ast.Subscript):
            return self._resolve_user_root(node.value)

        if isinstance(node, ast.Call):
            return self._resolve_user_root(node.func)

        return None

    def _field_name_from_target(self, node: ast.expr) -> str | None:
        if isinstance(node, ast.Attribute):
            return node.attr
        return None

    def _record_field_write(self, target: ast.expr, lineno: int) -> None:
        field_name = self._field_name_from_target(target)
        if field_name not in FORBIDDEN_FIELDS:
            return
        if not isinstance(target, ast.Attribute):
            return

        root = self._resolve_user_root(target.value)
        if root is None:
            return

        self.violations.append(
            Violation(
                lineno=lineno,
                message=f"forbidden write to User.{field_name} via `{root}`",
            )
        )

    def _record_setattr_write(self, node: ast.Call, lineno: int) -> None:
        func = node.func
        is_setattr = (
            (isinstance(func, ast.Name) and func.id == "setattr")
            or (isinstance(func, ast.Attribute) and func.attr == "setattr")
        )
        if not is_setattr or len(node.args) < 2:
            return

        root = self._resolve_user_root(node.args[0])
        if root is None:
            return

        attr_node = node.args[1]
        if isinstance(attr_node, ast.Constant) and isinstance(attr_node.value, str):
            field_name = attr_node.value
        else:
            return

        if field_name not in FORBIDDEN_FIELDS:
            return

        self.violations.append(
            Violation(
                lineno=lineno,
                message=f"forbidden setattr on User.{field_name} via `{root}`",
            )
        )

    def _track_simple_alias(self, target: ast.expr, value: ast.expr) -> None:
        if not isinstance(target, ast.Name):
            return

        alias = target.id
        root = self._resolve_user_root(value)
        if root is not None:
            self.scope.aliases[alias] = root
            return

        # Reassignment to a non-user value breaks the alias chain.
        if alias in self.scope.aliases:
            del self.scope.aliases[alias]

    def visit_FunctionDef(self, node: ast.FunctionDef | ast.AsyncFunctionDef) -> None:
        param_roots = frozenset(
            arg.arg
            for arg in node.args.args
            if arg.arg in KNOWN_USER_ROOT_NAMES
        )
        self._push_scope(param_roots)
        self.generic_visit(node)
        self._pop_scope()

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        self._push_scope()
        self.generic_visit(node)
        self._pop_scope()

    def visit_Assign(self, node: ast.Assign) -> None:
        for target in node.targets:
            self._record_field_write(target, node.lineno)

        if len(node.targets) == 1:
            self._track_simple_alias(node.targets[0], node.value)

        self.generic_visit(node)

    def visit_AnnAssign(self, node: ast.AnnAssign) -> None:
        if node.value is not None and node.target is not None:
            self._record_field_write(node.target, node.lineno)
            self._track_simple_alias(node.target, node.value)
        self.generic_visit(node)

    def visit_AugAssign(self, node: ast.AugAssign) -> None:
        self._record_field_write(node.target, node.lineno)
        self.generic_visit(node)

    def visit_For(self, node: ast.For) -> None:
        if isinstance(node.target, ast.Name) and node.target.id in KNOWN_USER_ROOT_NAMES:
            self._push_scope(frozenset({node.target.id}))
            self.generic_visit(node)
            self._pop_scope()
            return
        self.generic_visit(node)

    def visit_Call(self, node: ast.Call) -> None:
        self._record_setattr_write(node, node.lineno)
        self.generic_visit(node)


def _is_allowlisted(path: Path) -> bool:
    resolved = path.resolve()
    for prefix in ALLOWLIST_PREFIXES:
        try:
            resolved.relative_to(prefix.resolve())
            return True
        except ValueError:
            continue
    return False


def _scan_file(path: Path) -> list[Violation]:
    if path.suffix != ".py" or _is_allowlisted(path):
        return []

    source = path.read_text(encoding="utf-8")
    try:
        tree = ast.parse(source, filename=str(path))
    except SyntaxError as exc:
        return [Violation(lineno=exc.lineno or 1, message=f"syntax error: {exc.msg}")]

    visitor = UserLLMWriteVisitor()
    visitor.visit(tree)
    return visitor.violations


def _iter_python_files(root: Path):
    for path in root.rglob("*.py"):
        if any(part in SKIP_DIR_NAMES for part in path.parts):
            continue
        yield path


def main() -> int:
    violations: list[tuple[Path, Violation]] = []

    for root in SCAN_ROOTS:
        if not root.exists():
            continue
        for path in _iter_python_files(root):
            if path.name == Path(__file__).name:
                continue
            for hit in _scan_file(path):
                violations.append((path.relative_to(REPO_ROOT), hit))

    if not violations:
        return 0

    print(
        "Forbidden direct assignment to User LLM columns detected.\n"
        "Use backend.services.user_llm_settings update_* helpers instead "
        "(see CONTRIBUTING.md).\n",
        file=sys.stderr,
    )
    for rel_path, hit in sorted(violations, key=lambda item: (str(item[0]), item[1].lineno)):
        print(f"  {rel_path}:{hit.lineno}: {hit.message}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
