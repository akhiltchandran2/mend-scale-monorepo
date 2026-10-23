#!/usr/bin/env python3
"""Create package-lock.json for every generated npm project.

Mend needs a lockfile (or node_modules) to resolve npm dependencies. npm runs
once per profile with --package-lock-only (no install, no scripts); the result
is copied into each project with that profile and renamed to match it.

Profiles that resolve to more than --max-packages are trimmed one direct
dependency at a time. Small projects keep each `mend dep` policy-compliance
check short enough to finish before the CLI's deadline.
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


def resolved(lock):
    return len(lock.get("packages", {})) - 1


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", type=Path, default=ROOT / "projects")
    ap.add_argument("--max-packages", type=int, default=200,
                    help="upper bound on resolved packages per project")
    args = ap.parse_args()

    index_path = args.out / "index.json"
    index = json.loads(index_path.read_text())
    npm = index["ecosystems"]["npm"]
    locks = []
    for i, deps in enumerate(npm["profiles"]):
        deps = list(deps)
        lock = lock_profile(deps)
        # Drop the dependency that contributes the most packages until it fits.
        while resolved(lock) > args.max_packages and len(deps) > 1:
            trials = [(resolved(lock_profile([d for d in deps if d != x])), x) for x in deps]
            deps.remove(min(trials)[1])
            lock = lock_profile(deps)
        npm["profiles"][i] = deps
        locks.append(lock)
        print(f"profile {i:2}: {len(deps):2} direct deps, {resolved(lock)} resolved packages")

    for proj in npm["projects"]:
        deps = npm["profiles"][proj["profile"]]
        pdir = args.out / "npm" / proj["name"]
        manifest = json.loads((pdir / "package.json").read_text())
        manifest["dependencies"] = dict(d.rsplit("@", 1) for d in deps)
        (pdir / "package.json").write_text(json.dumps(manifest, indent=2) + "\n")

        lock = copy.deepcopy(locks[proj["profile"]])
        lock["name"] = proj["name"]
        lock["packages"][""]["name"] = proj["name"]
        (pdir / "package-lock.json").write_text(json.dumps(lock, indent=2) + "\n")

    index_path.write_text(json.dumps(index, indent=1) + "\n")
    print(f"wrote {len(npm['projects'])} lockfiles")


if __name__ == "__main__":
    main()
