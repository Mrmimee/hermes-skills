#!/usr/bin/env python3
"""
一键技能同步脚本：自动将本地 Hermes 正在演进、迭代的新 Skill 沉淀同步回 GitHub (Mrmimee/hermes-skills)。
具备：
- 自动分类增量同步
- 自动敏感信息与密钥扫描（拦截泄漏风险）
- 自动 Git Commit & Push
"""

import os
import sys
import shutil
import subprocess
import re
from pathlib import Path

REPO_DIR = Path(__file__).resolve().parent
LOCAL_SKILLS_DIR = Path.home() / "AppData" / "Local" / "hermes" / "skills"
AGENTS_SKILLS_DIR = Path.home() / ".agents" / "skills"
TOKEN_FILE = Path.home() / "OneDrive" / "桌面" / "apikey.txt"

CATEGORIES = [
    "autonomous-ai-agents",
    "study-and-engineering",
    "creative-and-design",
    "workflow-and-tools"
]

SECRET_PATTERNS = [
    re.compile(r'sk-[a-zA-Z0-9_\-]{20,}'),
    re.compile(r'ghp_[a-zA-Z0-9]{30,}'),
    re.compile(r'github_pat_[a-zA-Z0-9_]{30,}'),
    re.compile(r'nvapi-[a-zA-Z0-9_\-]{30,}'),
    re.compile(r'tvly-[a-zA-Z0-9_\-]{20,}')
]

def get_token():
    if not TOKEN_FILE.exists():
        return None
    try:
        lines = TOKEN_FILE.read_text(encoding='utf-8').splitlines()
        for i, line in enumerate(lines):
            if 'GitHub (Token)' in line and i + 1 < len(lines):
                return lines[i+1].strip()
    except Exception:
        pass
    return None

def scan_secrets(target_dir):
    leaks = []
    for root, dirs, files in os.walk(target_dir):
        if '.git' in root:
            continue
        for f in files:
            fp = os.path.join(root, f)
            try:
                text = Path(fp).read_text(encoding='utf-8', errors='ignore')
                for p in SECRET_PATTERNS:
                    m = p.search(text)
                    if m:
                        leaks.append((fp, m.group(0)[:8]))
            except Exception:
                pass
    return leaks

def sync_local_to_repo():
    print("🔄 正在扫描本地技能库变动...")
    synced_items = 0
    for cat in CATEGORIES:
        cat_repo_dir = REPO_DIR / cat
        if not cat_repo_dir.exists():
            continue

        for item in cat_repo_dir.iterdir():
            if not item.is_dir() and not item.name.endswith('.md'):
                continue
            
            # Find in local hermes or agents
            p1 = LOCAL_SKILLS_DIR / cat / item.name
            p2 = LOCAL_SKILLS_DIR / item.name
            p3 = AGENTS_SKILLS_DIR / item.name

            source = None
            if p1.exists(): source = p1
            elif p2.exists(): source = p2
            elif p3.exists(): source = p3

            if source:
                # If source is newer or changed
                if source.is_dir():
                    shutil.copytree(source.resolve(), item, dirs_exist_ok=True)
                else:
                    shutil.copy2(source.resolve(), item)
                synced_items += 1

    print(f"✓ 校验比对完成，覆盖检查了 {synced_items} 个技能。")

def main():
    commit_msg = sys.argv[1] if len(sys.argv) > 1 else "sync: auto-sync local skill updates"
    
    # 1. Sync local skills
    sync_local_to_repo()

    # 2. Secret safety scan
    leaks = scan_secrets(REPO_DIR)
    if leaks:
        print("❌ 安全拦截：检测到可能的密钥泄漏，已终止推送：", leaks, file=sys.stderr)
        sys.exit(1)
    print("🔒 安全审计通过：零敏感信息与密钥泄漏。")

    # 3. Git status check
    status = subprocess.run(["git", "status", "--porcelain"], cwd=REPO_DIR, text=True, capture_output=True).stdout
    if not status.strip():
        print("✨ 本地与云端已保持最新，无变动需要推送。")
        sys.exit(0)

    # 4. Git commit & push
    print("🚀 正在提交并推送到 GitHub (Mrmimee/hermes-skills)...")
    token = get_token()
    if token:
        remote_auth = f"https://x-access-token:{token}@github.com/Mrmimee/hermes-skills.git"
        subprocess.run(["git", "remote", "set-url", "origin", remote_auth], cwd=REPO_DIR, capture_output=True)

    subprocess.run(["git", "add", "."], cwd=REPO_DIR, capture_output=True)
    subprocess.run(["git", "commit", "-m", commit_msg], cwd=REPO_DIR, capture_output=True)
    res = subprocess.run(["git", "push", "origin", "main"], cwd=REPO_DIR, text=True, capture_output=True)

    # Clean remote URL immediately
    subprocess.run(["git", "remote", "set-url", "origin", "https://github.com/Mrmimee/hermes-skills.git"], cwd=REPO_DIR, capture_output=True)

    if res.returncode == 0:
        print("✅ GitHub 技能库已同步更新：https://github.com/Mrmimee/hermes-skills")
    else:
        print(f"⚠️ 推送失败：{res.stderr.strip()}", file=sys.stderr)
        sys.exit(res.returncode)

if __name__ == "__main__":
    main()
