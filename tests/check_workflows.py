"""Validate the GitHub Actions workflow files parse and reference real scripts."""
import glob
import os
import sys

import yaml

ROOT = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(ROOT)


def _steps(workflow):
    out = []
    for job in (workflow.get("jobs") or {}).values():
        for step in job.get("steps") or []:
            out.append(step)
    return out


def main():
    failures = []
    paths = sorted(glob.glob(os.path.join(REPO, ".github", "workflows", "*.yml")))
    paths += sorted(glob.glob(os.path.join(REPO, ".github", "workflows", "*.yaml")))

    if not paths:
        print("no workflow files found")
        return 1

    for path in paths:
        rel = os.path.relpath(path, REPO).replace("\\", "/")
        with open(path, encoding="utf-8") as fh:
            try:
                wf = yaml.safe_load(fh)
            except yaml.YAMLError as exc:
                failures.append(f"{rel}: YAML error: {exc}")
                continue

        if not isinstance(wf, dict):
            failures.append(f"{rel}: top level is not a mapping")
            continue

        # PyYAML 1.1 parses the bare key `on` as boolean True.
        if True not in wf and "on" not in wf:
            failures.append(f"{rel}: missing 'on:' trigger block")
        if "jobs" not in wf:
            failures.append(f"{rel}: missing 'jobs'")
            continue

        for job_name, job in wf["jobs"].items():
            if not job.get("runs-on"):
                failures.append(f"{rel}: job '{job_name}' has no runs-on")
            steps = job.get("steps") or []
            if not steps:
                failures.append(f"{rel}: job '{job_name}' has no steps")
            for step in steps:
                run = step.get("run")
                if not run:
                    continue
                for token in run.replace("|", " ").replace(">", " ").split():
                    token = token.strip("'\"")
                    if token.startswith(("_scripts/", "tests/")) and token.endswith(".py"):
                        target = os.path.join(REPO, token)
                        if not os.path.isfile(target):
                            failures.append(
                                f"{rel}: step '{step.get('name', '?')}' runs "
                                f"missing file {token}"
                            )

        print(f"  ok  {rel}  ({len(wf['jobs'])} job(s), {len(_steps(wf))} steps)")

    for f in failures:
        print(f"  FAIL {f}")
    print(f"\n{len(paths)} workflow(s), {len(failures)} problem(s)")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
