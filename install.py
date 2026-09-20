#!/usr/bin/env python3
"""
Hermes Skills Vault - One-Click Deployment Script
Easily install, link, and sync curated skills onto a new machine.
Supports Windows, macOS, and Linux.
"""

import os
import sys
import shutil
import platform

REPO_DIR = os.path.dirname(os.path.abspath(__file__))

def get_hermes_skills_dir():
    if platform.system() == "Windows":
        base = os.environ.get("LOCALAPPDATA", os.path.expanduser(r"~\AppData\Local"))
        return os.path.join(base, "hermes", "skills")
    else:
        return os.path.expanduser("~/.hermes/skills")

def get_hermes_scripts_dir():
    if platform.system() == "Windows":
        base = os.environ.get("LOCALAPPDATA", os.path.expanduser(r"~\AppData\Local"))
        return os.path.join(base, "hermes", "scripts")
    else:
        return os.path.expanduser("~/.hermes/scripts")

def main():
    dest_skills = get_hermes_skills_dir()
    dest_scripts = get_hermes_scripts_dir()
    
    print("==================================================")
    print("       Hermes Curated Skills Vault Installer      ")
    print("==================================================")
    print(f"[*] Target skills directory:  {dest_skills}")
    print(f"[*] Target scripts directory: {dest_scripts}")
    print()

    os.makedirs(dest_skills, exist_ok=True)
    os.makedirs(dest_scripts, exist_ok=True)

    categories = [
        "autonomous-ai-agents",
        "study-and-engineering",
        "creative-and-design",
        "workflow-and-tools"
    ]

    installed_count = 0
    for cat in categories:
        cat_src = os.path.join(REPO_DIR, cat)
        if not os.path.exists(cat_src):
            continue
        cat_dest = os.path.join(dest_skills, cat)
        os.makedirs(cat_dest, exist_ok=True)

        for item in os.listdir(cat_src):
            src_item = os.path.join(cat_src, item)
            dest_item = os.path.join(cat_dest, item)
            if not os.path.isdir(src_item) and not item.endswith('.md'):
                continue
            
            # Copy or sync
            if os.path.isdir(src_item):
                shutil.copytree(src_item, dest_item, dirs_exist_ok=True)
            else:
                shutil.copy2(src_item, dest_item)
            installed_count += 1
            print(f"  ✓ [{cat}] {item}")

    # Copy utility scripts
    scripts_src = os.path.join(REPO_DIR, "scripts")
    script_count = 0
    if os.path.exists(scripts_src):
        for s in os.listdir(scripts_src):
            sp = os.path.join(scripts_src, s)
            dp = os.path.join(dest_scripts, s)
            if os.path.isfile(sp):
                shutil.copy2(sp, dp)
                script_count += 1
                print(f"  ✓ [scripts] {s}")

    print()
    print(f"🎉 Success! Installed {installed_count} skills and {script_count} scripts.")
    print("Hermes will automatically pick up the new skills on your next session.")

if __name__ == "__main__":
    main()
