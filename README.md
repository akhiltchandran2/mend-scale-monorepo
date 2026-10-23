# mend-scale-monorepo

A polyglot monorepo of **intentionally vulnerable** projects for load-testing
Mend SCA. Each npm project produces a ~5–7 MB `mend dep` report, so scanning
about 100 of them gives a combined report **over 500 MB**.

> Nothing here is meant to run. Projects only declare old dependencies with
> published CVEs. Do not deploy them or install them outside a sandbox.

## Layout

| Path | What it is |
|---|---|
| `catalog/{npm,pypi,maven}.txt` | Vulnerable package versions the projects draw from |
| `catalog/npm-heavy.txt` | Old toolchains with large dependency trees, added to npm profiles to reach 1,000 packages |
| `projects/npm/npm-svc-NNNNN/` | 400 npm projects, each with `package.json` and a real `package-lock.json` (1,000–1,400 resolved packages) |
| `projects/pypi/pypi-svc-NNNNN/` | 300 Python projects (`requirements.txt`) |
| `projects/maven/maven-svc-NNNNN/` | 200 Maven projects (`pom.xml`) |
| `projects/index.json` | Which dependency profile each project uses |
| `mend/wss-unified-agent.config` | Unified Agent config, `projectPerFolder=true` |
| `tools/generate.py` | Builds `projects/` (scale is set with flags) |
| `tools/lock.py` | Creates npm lockfiles once per profile, fitting each to 1,000–1,400 packages |
| `tools/estimate.py` | Estimates report size, optionally calibrated from a real report |
| `tools/scan.sh` | Scans every folder as its own Mend project |

## How the size is reached

Mend report size grows with **projects × resolved libraries × findings**.
Each npm project starts with 45 vulnerable packages, and `tools/lock.py`
adds old toolchains (gulp, Angular CLI, karma, webpack, jest, ...) until it
resolves **1,000–1,400 packages**. At ~5 KB of `mend dep --format json` output
per package, that is **~5–7 MB per project**:

| npm projects scanned | Combined report |
|---|---|
| 1 | ~5–7 MB |
| 100 | ~565 MB |
| 400 (all) | ~2.2 GB |

Python (300) and Maven (200) projects are unchanged and much smaller.
Every project has a unique name and folder, so Mend does not merge them.
Run `python3 tools/estimate.py` for the current totals.

## Policy-compliance timeout

`failed to check policy compliance - timed out waiting for
asyncCheckPolicyCompliance run to complete: context deadline exceeded`
means the server-side policy check for one scan did not finish in time.
The most common cause is running `mend dep` at the repo root, which makes
the whole repo one huge project. Scan one project folder at a time instead.

Mend's CLI docs list no flag to skip that check or raise its timeout. If it
still happens on single folders:

- run one scan at a time: `tools/scan.sh cli 1`
- failed scans retry up to 3 times with back-off (`MEND_RETRIES=3`)
- make projects smaller: `python3 tools/lock.py --min-packages 600 --max-packages 900`
  (~3–4.5 MB per project), then scan more of them

The Unified Agent path (`tools/scan.sh ua`) runs with `checkPolicies=false`.

## Usage

```bash
python3 tools/generate.py --clean      # regenerate (defaults: 400 npm, 300 pypi, 200 maven)
python3 tools/lock.py                  # needs network access to the npm registry
python3 tools/estimate.py
```

Scan (each folder becomes a separate project under product `mend-scale-monorepo`):

```bash
tools/scan.sh cli 2                    # Mend CLI, 2 scans in parallel, results in scan-results.log
tools/scan.sh ua ./wss-unified-agent.jar
```

### Calibrate before the full scan

Bytes per component depend on which report you export. To get a real number,
scan the first 20 npm projects, export the report, then:

```bash
python3 tools/estimate.py --sample-report ./sample-report.json --sample-projects 20
```

If projects come out under 5 MB, raise the floor, for example
`python3 tools/lock.py --min-packages 1300 --max-packages 1800`.

## Ecosystem requirements

- **npm**: works as is; Mend reads `package-lock.json`.
- **Python**: Mend runs `pip install`. Many old pins (numpy 1.16, scipy 1.0)
  won't build on current Python, so the UA config sets
  `python.ignorePipInstallErrors=true`. Python 3.7 resolves the most packages.
- **Maven**: needs `mvn` on the scanning machine to resolve the POMs.

The 500 MB target relies only on npm, so it still holds if Python or Maven
resolution only partly works.
