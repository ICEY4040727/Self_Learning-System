"""Risk 1 — static AST scan for forbidden direct User LLM writes."""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
CHECKER_PATH = REPO_ROOT / "scripts" / "check_user_llm_direct_writes.py"


def _load_checker():
    spec = importlib.util.spec_from_file_location("check_user_llm_direct_writes", CHECKER_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


checker = _load_checker()


def _violations(source: str) -> list[checker.Violation]:
    import ast

    tree = ast.parse(source)
    visitor = checker.UserLLMWriteVisitor()
    visitor.visit(tree)
    return visitor.violations


class TestStaticScanViolations:
    def test_flags_direct_model_assignment(self):
        hits = _violations('user.model = "gpt-4o"')
        assert len(hits) == 1
        assert "model" in hits[0].message

    def test_flags_multiline_split_assignment(self):
        source = 'user.model \\\n    = "gpt-4o"'
        hits = _violations(source)
        assert len(hits) == 1
        assert "model" in hits[0].message

    def test_flags_parenthesized_base_assignment(self):
        hits = _violations('(current_user).encrypted_api_key = "x"')
        assert len(hits) == 1
        assert "encrypted_api_key" in hits[0].message

    def test_flags_alias_chain_assignment(self):
        hits = _violations("u = user\nv = u\nv.temperature = 0.5")
        assert len(hits) == 1
        assert "temperature" in hits[0].message

    def test_flags_setattr_on_alias(self):
        hits = _violations('u = current_user\nsetattr(u, "max_tokens", 1024)')
        assert len(hits) == 1
        assert "max_tokens" in hits[0].message

    def test_ignores_non_user_targets(self):
        assert _violations('config.model = "gpt-4o"') == []


class TestStaticScanAllowlist:
    def test_write_gateway_file_is_allowlisted(self):
        assert checker._scan_file(checker.WRITE_GATEWAY) == []

    def test_backend_tests_tree_is_allowlisted(self):
        sample = REPO_ROOT / "backend" / "tests" / "conftest.py"
        assert checker._is_allowlisted(sample) is True


class TestStaticScanCliExitCodes:
    @staticmethod
    def _scratch_dir(name: str) -> Path:
        # Must live outside backend/tests — that tree is allowlisted.
        root = REPO_ROOT / ".pytest_scan_tmp" / name
        if root.exists():
            for child in root.glob("**/*"):
                if child.is_file():
                    child.unlink()
        root.mkdir(parents=True, exist_ok=True)
        return root

    def test_main_returns_zero_on_clean_scan_roots(self, monkeypatch):
        clean = self._scratch_dir("clean_pkg")
        (clean / "ok.py").write_text("config = {}\n", encoding="utf-8")
        monkeypatch.setattr(checker, "SCAN_ROOTS", (clean,))
        assert checker.main() == 0

    def test_main_returns_one_when_violation_present(self, monkeypatch):
        bad_root = self._scratch_dir("bad_pkg")
        (bad_root / "bad.py").write_text('user.default_provider = "openai"\n', encoding="utf-8")
        monkeypatch.setattr(checker, "SCAN_ROOTS", (bad_root,))
        assert checker.main() == 1
