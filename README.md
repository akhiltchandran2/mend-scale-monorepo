# mend-scale-monorepo

A polyglot monorepo of **intentionally vulnerable** projects for load-testing
Mend SCA. It is sized so that a full scan produces a report **over 500 MB**.

> Nothing here is meant to run. Projects only declare old dependencies with
> published CVEs. Do not deploy them or install them outside a sandbox.

## Layout

| Path | What it is |
|---|---|
| `catalog/{npm,pypi,maven}.txt` | Vulnerable package versions the projects draw from |
| `projects/npm/npm-svc-NNNNN/` | 5,500 npm projects, each with `package.json` and a real `package-lock.json` (≤200 resolved packages) |
| `projects/pypi/pypi-svc-NNNNN/` | 300 Python projects (`requirements.txt`) |
| `projects/maven/maven-svc-NNNNN/` | 200 Maven projects (`pom.xml`) |
| `projects/index.json` | Which dependency profile each project uses |
| `mend/wss-unified-agent.config` | Unified Agent config, `projectPerFolder=true` |
| `tools/generate.py` | Builds `projects/` (scale is set with flags) |
| `tools/lock.py` | Creates npm lockfiles once per profile, trimming any profile over 200 packages |
| `tools/estimate.py` | Estimates report size, optionally calibrated from a real report |
| `tools/scan.sh` | Scans every folder as its own Mend project |

## How the size is reached

Mend report size grows with **projects × resolved libraries × findings**.
Every project stays at **200 resolved packages or fewer**, so each
`mend dep` scan, and its policy-compliance check, stays small. The total
comes from the number of projects instead: 5,500 npm, 300 Python and
200 Maven. Run `python3 tools/estimate.py` for the current totals.

Every project has a unique name and folder, so Mend does not merge them.

## Policy-compliance timeout

`failed to check policy compliance - timed out waiting for
asyncCheckPolicyCompliance run to complete: context deadline exceeded`
means the server-side policy check for one scan did not finish in time.
Mend's CLI docs list no flag to skip that check or raise its timeout, so this
repo avoids it by:

- capping each project at 200 resolved packages (`tools/lock.py --max-packages`)
- running only 2 scans at once by default (`tools/scan.sh cli 2`)
- retrying a failed scan up to 3 times with back-off (`MEND_RETRIES=3`)

If it still happens, lower `--max-packages` (for example to 150), use
`tools/scan.sh cli 1`, and ask your Mend admin how long policy checks take on
your org. The Unified Agent path (`tools/scan.sh ua`) runs with
`checkPolicies=false`.

## Usage

```bash
python3 tools/generate.py --clean      # regenerate (defaults: 5500 npm, 300 pypi, 200 maven)
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

If it prints `TOO SMALL`, raise the scale, for example
`python3 tools/generate.py --clean --npm 6000`, then run `lock.py` again.
Raise the project count rather than `--max-packages`, so each scan stays small.

## Ecosystem requirements

- **npm**: works as is; Mend reads `package-lock.json`.
- **Python**: Mend runs `pip install`. Many old pins (numpy 1.16, scipy 1.0)
  won't build on current Python, so the UA config sets
  `python.ignorePipInstallErrors=true`. Python 3.7 resolves the most packages.
- **Maven**: needs `mvn` on the scanning machine to resolve the POMs.

The default size estimate counts npm on its own as ~96% of components, so the
500 MB target still holds if Python or Maven resolution only partly works.
