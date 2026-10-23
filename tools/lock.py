#!/usr/bin/env python3
"""Create package-lock.json for every generated npm project.

Mend needs a lockfile (or node_modules) to resolve npm dependencies. npm runs
once per profile with --package-lock-only (no install, no scripts); the result
is copied into each project with that profile and renamed to match it.
"""
import argparse
import copy
import json
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def lock_profile(deps):
    manifest = {"name": "profile", "version": "1.0.0", "private": True,
                "dependencies": dict(d.rsplit("@", 1) for d in deps)}
    with tempfile.TemporaryDirectory() as tmp:
        (Path(tmp) / "package.json").write_text(json.dumps(manifest))
        subprocess.run(
            ["npm", "install", "--package-lock-only", "--ignore-scripts",
             "--no-audit", "--no-fund", "--legacy-peer-deps"],
            cwd=tmp, check=True, stdout=subprocess.DEVNULL,
        )
        return json.loads((Path(tmp) / "package-lock.json").read_text())


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, default=ROOT / "projects")
    args = ap.parse_args()

    index = json.loads((args.out / "index.json").read_text())
    npm = index["ecosystems"]["npm"]
    locks = []
    for i, deps in enumerate(npm["profiles"]):
        lock = lock_profile(deps)
        locks.append(lock)
        print(f"profile {i:2}: {len(lock.get('packages', {})) - 1} resolved packages")

    for proj in npm["projects"]:
        lock = copy.deepcopy(locks[proj["profile"]])
        lock["name"] = proj["name"]
        lock["packages"][""]["name"] = proj["name"]
        path = args.out / "npm" / proj["name"] / "package-lock.json"
        path.write_text(json.dumps(lock, indent=2) + "\n")
    print(f"wrote {len(npm['projects'])} lockfiles")


if __name__ == "__main__":
    main()
