# mend-scale-monorepo

A polyglot monorepo of **intentionally vulnerable** projects for load-testing
Mend SCA. It is sized so that a full scan produces a report **over 500 MB**.

> Nothing here is meant to run. Projects only declare old dependencies with
> published CVEs. Do not deploy them or install them outside a sandbox.

## Layout

| Path | What it is |
|---|---|
| `catalog/{npm,pypi,maven}.txt` | Vulnerable package versions the projects draw from |
| `projects/npm/npm-svc-NNNNN/` | 1,500 npm projects, each with `package.json` and a real `package-lock.json` |
| `projects/pypi/pypi-svc-NNNNN/` | 300 Python projects (`requirements.txt`) |
| `projects/maven/maven-svc-NNNNN/` | 200 Maven projects (`pom.xml`) |
| `projects/index.json` | Which dependency profile each project uses |
| `mend/wss-unified-agent.config` | Unified Agent config, `projectPerFolder=true` |
| `tools/generate.py` | Builds `projects/` (scale is set with flags) |
| `tools/lock.py` | Creates npm lockfiles, running npm once per profile |
| `tools/estimate.py` | Estimates report size, optionally calibrated from a real report |
| `tools/scan.sh` | Scans every folder as its own Mend project |

## How the size is reached

Mend report size grows with **projects × resolved libraries × findings**.
Each project gets 35 direct vulnerable dependencies. The npm lockfiles expand
these to about 230–830 transitive packages, which gives about 930k component
instances across 2,000 projects:

- at ~700 bytes per component (a lean inventory row): **~620 MB**
- at ~4 KB per component (findings/SBOM with vulnerability detail): **~3.6 GB**

Every project has a unique name and folder, so Mend does not merge them.

## Usage

```bash
python3 tools/generate.py --clean      # regenerate (defaults: 1500 npm, 300 pypi, 200 maven)
python3 tools/lock.py                  # needs network access to the npm registry
python3 tools/estimate.py
```

Scan (each folder becomes a separate project under product `mend-scale-monorepo`):

```bash
tools/scan.sh cli 8                    # Mend CLI, 8 scans in parallel
tools/scan.sh ua ./wss-unified-agent.jar
```

### Calibrate before the full scan

Bytes per component depend on which report you export. To get a real number,
scan the first 20 npm projects, export the report, then:

```bash
python3 tools/estimate.py --sample-report ./sample-report.json --sample-projects 20
```

If it prints `TOO SMALL`, raise the scale, for example
`python3 tools/generate.py --clean --npm 3000 --deps 45`, then run `lock.py` again.

## Ecosystem requirements

- **npm**: works as is; Mend reads `package-lock.json`.
- **Python**: Mend runs `pip install`. Many old pins (numpy 1.16, scipy 1.0)
  won't build on current Python, so the UA config sets
  `python.ignorePipInstallErrors=true`. Python 3.7 resolves the most packages.
- **Maven**: needs `mvn` on the scanning machine to resolve the POMs.

The default size estimate counts npm on its own as ~96% of components, so the
500 MB target still holds if Python or Maven resolution only partly works.
