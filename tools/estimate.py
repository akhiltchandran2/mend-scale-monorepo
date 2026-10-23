#!/usr/bin/env python3
"""Estimate how big the Mend report for the generated repo will be.

Mend does not publish a size formula, so this counts component instances
(project x resolved library) and multiplies by bytes per instance.

Calibrate first: scan a handful of projects, export the report you care
about, then pass --sample-report <file> --sample-projects <n>. Without a
sample, --bytes-per-component (default 4 KB, a guess for a JSON findings or
SBOM report with vulnerability detail) is used.
"""
import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
# Rough transitive fan-out for ecosystems we cannot lock offline.
FANOUT = {"pypi": 1.6, "maven": 3.0}
TARGET_MB = 500


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, default=ROOT / "projects")
    ap.add_argument("--bytes-per-component", type=float, default=4096)
    ap.add_argument("--sample-report", type=Path)
    ap.add_argument("--sample-projects", type=int)
    args = ap.parse_args()

    index = json.loads((args.out / "index.json").read_text())
    total = 0
    per_project = {}
    for eco, data in index["ecosystems"].items():
        count = 0
        for proj in data["projects"]:
            if eco == "npm":
                lock = args.out / "npm" / proj["name"] / "package-lock.json"
                if lock.exists():
                    n = len(json.loads(lock.read_text())["packages"]) - 1
                else:
                    n = len(data["profiles"][proj["profile"]]) * 8
            else:
                n = len(data["profiles"][proj["profile"]]) * FANOUT[eco]
            per_project[proj["name"]] = n
            count += n
        print(f"{eco:6} {len(data['projects']):6} projects  ~{int(count):>9,} component instances")
        total += count

    bpc = args.bytes_per_component
    if args.sample_report:
        names = list(per_project)[: args.sample_projects]
        sample_components = sum(per_project[n] for n in names)
        bpc = args.sample_report.stat().st_size / sample_components
        print(f"calibrated from {args.sample_report.name}: {bpc:,.0f} bytes/component "
              f"(first {len(names)} projects in index order)")

    mb = total * bpc / 1024 / 1024
    verdict = "OK" if mb > TARGET_MB else "TOO SMALL - raise --npm/--pypi/--maven or --deps"
    print(f"total  ~{int(total):,} component instances -> ~{mb:,.0f} MB  [{verdict}]")


if __name__ == "__main__":
    main()
