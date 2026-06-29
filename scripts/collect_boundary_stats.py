#!/usr/bin/env python3
"""Collect boundary inventory stats for docs/v1.0.5/boundary_diff_inventory.md

Output: docs/v1.0.5/boundary_stats.json
Must be re-run before merging doc/structural PRs; CI can diff line counts vs live files.
"""
from __future__ import annotations

import hashlib
import json
import re
import subprocess
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ROUTES_DIR = ROOT / "backend" / "api" / "routes"
MAIN_PY = ROOT / "backend" / "main.py"
FE_ROUTER = ROOT / "frontend" / "src" / "app" / "router" / "index.ts"
FE_SRC = ROOT / "frontend" / "src"
SERVICES_DIR = ROOT / "backend" / "services"
OUT_JSON = ROOT / "docs" / "v1.0.5" / "boundary_stats.json"

ROUTER_DECOR = re.compile(
    r'@router\.(get|post|put|patch|delete)\(\s*(?:\n\s*)?(?:f)?["\']([^"\']+)["\']',
    re.IGNORECASE,
)
INCLUDE_ROUTER = re.compile(
    r'include_router\((\w+)\.router,\s*prefix="([^"]+)"(?:,\s*tags=\[([^\]]+)\])?',
)
FE_PATH = re.compile(r"""path:\s*['"]([^'"]+)['"]""")


def git_head() -> str | None:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "HEAD"],
            cwd=ROOT,
            text=True,
            stderr=subprocess.DEVNULL,
        ).strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None


def file_fingerprint(path: Path) -> dict:
    raw = path.read_bytes()
    text = raw.decode("utf-8")
    return {
        "path": str(path.relative_to(ROOT)).replace("\\", "/"),
        "lines": len(text.splitlines()),
        "bytes": len(raw),
        "sha256_prefix": hashlib.sha256(raw).hexdigest()[:16],
    }


def extract_endpoints(path: Path) -> list[dict[str, str]]:
    text = path.read_text(encoding="utf-8")
    seen: set[tuple[str, str]] = set()
    out: list[dict[str, str]] = []
    for m in ROUTER_DECOR.finditer(text):
        key = (m.group(1).upper(), m.group(2))
        if key not in seen:
            seen.add(key)
            out.append({"method": key[0], "path": key[1]})
    return out


def main() -> None:
    route_files = sorted(p for p in ROUTES_DIR.glob("*.py") if p.name != "__init__.py")
    fingerprints = {f.name: file_fingerprint(f) for f in route_files}
    endpoints_by_file = {f.name: extract_endpoints(f) for f in route_files}

    main_text = MAIN_PY.read_text(encoding="utf-8")
    mounts = [
        {
            "module": m.group(1),
            "prefix": m.group(2),
            "tags": (m.group(3) or "").strip('"'),
        }
        for m in INCLUDE_ROUTER.finditer(main_text)
    ]

    fe_dirs = sorted(p.name for p in FE_SRC.iterdir() if p.is_dir())
    fe_routes = FE_PATH.findall(FE_ROUTER.read_text(encoding="utf-8"))

    svc_files = list(SERVICES_DIR.rglob("*.py"))

    learning_store = ROOT / "frontend" / "src" / "app" / "stores" / "learning.ts"
    ls_fp = file_fingerprint(learning_store) if learning_store.exists() else None

    payload = {
        "meta": {
            "generated_at": datetime.now(UTC).isoformat(),
            "generator": "scripts/collect_boundary_stats.py",
            "git_head": git_head(),
            "verify_note": "Compare fingerprints.lines/sha256_prefix against live files before citing counts as hard evidence.",
        },
        "backend": {
            "route_files": len(route_files),
            "route_fingerprints": fingerprints,
            "route_total_lines": sum(fp["lines"] for fp in fingerprints.values()),
            "endpoint_counts_by_file": {k: len(v) for k, v in endpoints_by_file.items()},
            "endpoint_total": sum(len(v) for v in endpoints_by_file.values()),
            "main_py_mounts": mounts,
            "main_py_mount_count": len(mounts),
            "archive_progress_endpoints": [
                e for e in endpoints_by_file.get("archive.py", []) if "progress" in e["path"]
            ],
        },
        "frontend": {
            "src_top_level_dirs": fe_dirs,
            "src_top_level_dir_count": len(fe_dirs),
            "router_paths": fe_routes,
            "router_path_count": len(fe_routes),
            "home_report_registered": any("report" in p for p in fe_routes),
            "learning_store_fingerprint": ls_fp,
        },
        "services": {
            "py_file_count": len(svc_files),
        },
        "endpoints_by_file": endpoints_by_file,
    }

    OUT_JSON.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(OUT_JSON)
    print(f"endpoint_total={payload['backend']['endpoint_total']} archive_lines={fingerprints['archive.py']['lines']}")


if __name__ == "__main__":
    main()
