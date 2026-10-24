#!/usr/bin/env python3
"""把「夜秣万能DIY装机顾问」技能打成可上传 SkillHub 的 ZIP。

默认排除：密钥与 .env、__pycache__ / .pyc、备份 .bak、状态文件、node_modules、
测试产物、dist 自身。打包前会再做一次密钥扫描，命中即拒绝打包。

用法：
  python scripts/package_skill.py                  # 输出到 dist/夜秣万能DIY装机顾问-<version>.zip
  python scripts/package_skill.py --dry-run        # 只列出会打进去的文件
"""

from __future__ import annotations

import argparse
import re
import zipfile
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parent.parent
DIST_DIR = SKILL_DIR / "dist"

EXCLUDE_DIRS = {
    "__pycache__", "node_modules", ".git", ".venv", "venv", "dist", ".idea", ".vscode",
    "assets",  # SkillHub 服务端只接受代码/文档，图片封面在网页端单独上传
    "tests", ".user-data", ".cache", "outputs", "_private",
}
EXCLUDE_SUFFIXES = {".pyc", ".pyo", ".bak", ".tmp", ".log", ".db", ".sqlite3"}
EXCLUDE_FILES = {
    ".env", ".env.local", ".env.production", ".pay-state.json",
    ".DS_Store", "config.json", "secret.json",
}
EXCLUDE_NAME_PATTERNS = [
    re.compile(r"^\.pay-state"),
    re.compile(r"_state\.json$"),
    re.compile(r"^\.alipay-"),      # 支付宝配置（含私钥）
    re.compile(r"\.key$"),          # 私钥文件
    re.compile(r"\.pem$"),
    re.compile(r"_last_result\.txt$"),
]
SECRET_PATTERNS = [
    re.compile(r"sk-[A-Za-z0-9]{16,}"),
    re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
    re.compile(r"MIIE[A-Za-z0-9+/]{20,}"),   # PKCS#8/PKCS#1 私钥常见前缀
]


def version_from_skill() -> str:
    text = (SKILL_DIR / "SKILL.md").read_text(encoding="utf-8")
    match = re.search(r"^version:\s*([0-9][0-9A-Za-z.\-]*)\s*$", text, re.M)
    return match.group(1) if match else "0.0.0"


def is_excluded(path: Path, root: Path) -> tuple[bool, str]:
    rel = path.relative_to(root)
    parts = set(rel.parts)
    if parts & EXCLUDE_DIRS:
        return True, "目录黑名单"
    if path.is_file():
        if path.name in EXCLUDE_FILES:
            return True, "文件黑名单"
        if path.suffix.lower() in EXCLUDE_SUFFIXES:
            return True, "后缀黑名单"
        for pattern in EXCLUDE_NAME_PATTERNS:
            if pattern.search(path.name):
                return True, "命名模式黑名单"
    return False, ""


def scan_secrets(files: list[Path]) -> list[str]:
    hits = []
    for path in files:
        if path.suffix.lower() in {".png", ".jpg", ".jpeg", ".pptx", ".zip"}:
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        for pattern in SECRET_PATTERNS:
            if pattern.search(text):
                hits.append(f"{path.relative_to(SKILL_DIR)} 命中 {pattern.pattern}")
                break
    return hits


def collect() -> tuple[list[Path], list[tuple[Path, str]]]:
    keep, skipped = [], []
    for path in sorted(SKILL_DIR.rglob("*")):
        if path.is_dir():
            continue
        excluded, reason = is_excluded(path, SKILL_DIR)
        (skipped if excluded else keep).append((path, reason) if excluded else path)
    return keep, skipped  # type: ignore[return-value]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--out", help="输出 zip 路径")
    args = parser.parse_args()

    keep, skipped = collect()
    print(f"技能目录：{SKILL_DIR}")
    print(f"将打包 {len(keep)} 个文件，排除 {len(skipped)} 个\n")
    for path, reason in skipped[:30]:
        print(f"  - 排除 {path.relative_to(SKILL_DIR)}（{reason}）")
    if len(skipped) > 30:
        print(f"  ... 另有 {len(skipped) - 30} 个")

    hits = scan_secrets(keep)
    if hits:
        print("\n[FAIL] 密钥扫描未通过，拒绝打包：")
        for hit in hits:
            print(f"  ! {hit}")
        print("\n请先把密钥移出技能目录（写入环境变量或 ~/.workbuddy/config/*.json）。")
        return 1
    print("\n[OK] 密钥扫描通过：包内无 sk- 密钥、无私钥 PEM。")

    if args.dry_run:
        print("\n（--dry-run，未生成 zip）")
        return 0

    version = version_from_skill()
    out_path = Path(args.out) if args.out else DIST_DIR / f"夜秣万能DIY装机顾问-{version}.zip"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    if out_path.exists():
        out_path.unlink()

    with zipfile.ZipFile(out_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for path in keep:
            zf.write(path, str(path.relative_to(SKILL_DIR)).replace("\\", "/"))

    size_mb = out_path.stat().st_size / 1024 / 1024
    print(f"\n[DONE] 已生成：{out_path}（{size_mb:.2f} MB）")
    if size_mb > 3:
        print("警告：超过 SkillHub 的 3MB 限制，需要瘦身后再上传。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
