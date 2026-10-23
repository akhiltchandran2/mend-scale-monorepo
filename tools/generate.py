#!/usr/bin/env python3
"""Generate a large polyglot monorepo of intentionally vulnerable projects.

Each project becomes its own Mend project (one folder each), so the size of
the resulting inventory / findings / SBOM reports grows linearly with
--npm + --pypi + --maven.

Projects are assigned to a small number of dependency "profiles". The lock
step (tools/lock.sh) only runs npm once per profile and copies the lockfile
to every project that uses it, so 5,000 npm projects need only --profiles
network resolutions.
"""
import argparse
import json
import random
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CATALOG = ROOT / "catalog"


def load(name):
    lines = (CATALOG / name).read_text().splitlines()
    return [l.strip() for l in lines if l.strip() and not l.startswith("#")]


def make_profiles(catalog, count, size, rng):
    size = min(size, len(catalog))
    return [sorted(rng.sample(catalog, size)) for _ in range(count)]


def write_npm(path, name, deps):
    path.mkdir(parents=True, exist_ok=True)
    dependencies = {}
    for d in deps:
        pkg, ver = d.rsplit("@", 1)
        dependencies[pkg] = ver
    manifest = {
        "name": name,
        "version": "1.0.0",
        "private": True,
        "license": "UNLICENSED",
        "dependencies": dependencies,
    }
    (path / "package.json").write_text(json.dumps(manifest, indent=2) + "\n")
    (path / "index.js").write_text("module.exports = {};\n")


def write_pypi(path, name, deps):
    path.mkdir(parents=True, exist_ok=True)
    (path / "requirements.txt").write_text("\n".join(deps) + "\n")
    (path / "setup.py").write_text(
        "from setuptools import setup\n"
        f"setup(name={name!r}, version='1.0.0', py_modules=['app'])\n"
    )
    (path / "app.py").write_text("")


def write_maven(path, name, deps):
    path.mkdir(parents=True, exist_ok=True)
    dep_xml = []
    for d in deps:
        g, a, v = d.split(":")
        dep_xml.append(
            "    <dependency>\n"
            f"      <groupId>{g}</groupId>\n"
            f"      <artifactId>{a}</artifactId>\n"
            f"      <version>{v}</version>\n"
            "    </dependency>"
        )
    pom = f"""<?xml version="1.0" encoding="UTF-8"?>
<project xmlns="http://maven.apache.org/POM/4.0.0"
         xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
         xsi:schemaLocation="http://maven.apache.org/POM/4.0.0 http://maven.apache.org/xsd/maven-4.0.0.xsd">
  <modelVersion>4.0.0</modelVersion>
  <groupId>com.example.mendscale</groupId>
  <artifactId>{name}</artifactId>
  <version>1.0.0</version>
  <packaging>jar</packaging>
  <properties>
    <maven.compiler.source>8</maven.compiler.source>
    <maven.compiler.target>8</maven.compiler.target>
  </properties>
  <dependencies>
{chr(10).join(dep_xml)}
  </dependencies>
</project>
"""
    (path / "pom.xml").write_text(pom)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--npm", type=int, default=400, help="number of npm projects")
    ap.add_argument("--pypi", type=int, default=300, help="number of Python projects")
    ap.add_argument("--maven", type=int, default=200, help="number of Maven projects")
    ap.add_argument("--deps", type=int, default=35, help="direct dependencies per Python/Maven project")
    ap.add_argument("--npm-deps", type=int, default=45,
                    help="direct dependencies per npm project (lock.py then fits each profile to --min/--max-packages)")
    ap.add_argument("--profiles", type=int, default=12, help="distinct dependency sets per ecosystem")
    ap.add_argument("--seed", type=int, default=1337)
    ap.add_argument("--out", type=Path, default=ROOT / "projects")
    ap.add_argument("--clean", action="store_true", help="delete --out before generating")
    args = ap.parse_args()

    rng = random.Random(args.seed)
    if args.clean and args.out.exists():
        shutil.rmtree(args.out)

    plan = [
        ("npm", args.npm, load("npm.txt"), write_npm),
        ("pypi", args.pypi, load("pypi.txt"), write_pypi),
        ("maven", args.maven, load("maven.txt"), write_maven),
    ]
    index = {"seed": args.seed, "ecosystems": {}}
    for eco, count, catalog, writer in plan:
        deps = args.npm_deps if eco == "npm" else args.deps
        profiles = make_profiles(catalog, args.profiles, deps, rng)
        projects = []
        for i in range(count):
            name = f"{eco}-svc-{i:05d}"
            p = i % len(profiles)
            writer(args.out / eco / name, name, profiles[p])
            projects.append({"name": name, "profile": p})
        index["ecosystems"][eco] = {"profiles": profiles, "projects": projects}
        print(f"{eco:6} {count:6} projects  {len(profiles)} profiles  {deps} direct deps each")

    (args.out / "index.json").write_text(json.dumps(index, indent=1) + "\n")
    print(f"wrote {args.out}")


if __name__ == "__main__":
    main()
