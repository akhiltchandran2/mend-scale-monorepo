#!/usr/bin/env python3
"""Create package-lock.json for every generated npm project.

Mend needs a lockfile (or node_modules) to resolve npm dependencies. npm runs
once per profile with --package-lock-only (no install, no scripts); the result
is copied into each project with that profile and renamed to match it.

Each profile is fitted to --min-packages..--max-packages resolved packages:
toolchains from catalog/npm-heavy.txt are added until it reaches the minimum,
and direct dependencies are trimmed if it goes over the maximum. At ~5 KB of
`mend dep --format json` output per package, 1,000 packages is ~5 MB per project.
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
    ap.add_argument("--min-packages", type=int, default=1000,
                    help="lower bound on resolved packages per project")
    ap.add_argument("--max-packages", type=int, default=1400,
                    help="upper bound on resolved packages per project")
    args = ap.parse_args()

    index_path = args.out / "index.json"
    index = json.loads(index_path.read_text())
    npm = index["ecosystems"]["npm"]
    heavy = [l.strip() for l in (ROOT / "catalog" / "npm-heavy.txt").read_text().splitlines()
             if l.strip() and not l.startswith("#")]
    locks = []
    for i, deps in enumerate(npm["profiles"]):
        deps = list(deps)
        lock = lock_profile(deps)
        # Drop the dependency that contributes the most packages until it fits.
        while resolved(lock) > args.max_packages and len(deps) > 1:
            trials = [(resolved(lock_profile([d for d in deps if d != x])), x) for x in deps]
            deps.remove(min(trials)[1])
            lock = lock_profile(deps)
        for tool in heavy:
            if resolved(lock) >= args.min_packages:
                break
            bigger = lock_profile(deps + [tool])
            if resolved(bigger) <= args.max_packages:
                deps, lock = deps + [tool], bigger
        if resolved(lock) < args.min_packages:
            print(f"warning: profile {i} only reaches {resolved(lock)} packages")
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
