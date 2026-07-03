# -*- coding: utf-8 -*-
"""
Verify scheduler deployment via Railway startup logs.

Looks for:
  [SCHEDULER BUILD INFO]
  git_sha=<expected>
  [DASHBOARD SNAPSHOT ARCHIVE CONFIG]
  archive_enabled=...

Usage:
  python scripts/scheduler_deployment_verify_v1.py
  python scripts/scheduler_deployment_verify_v1.py --expected-sha 18d46ad
  python scripts/scheduler_deployment_verify_v1.py --log-file path/to/railway.log
"""
from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "scripts" / "_scheduler_deployment_verify_v1_out"
OUT_FILE = OUT_DIR / "verify_report.txt"


def _fetch_railway_logs(service: str, lines: int) -> str:
    out = subprocess.check_output(
        ["railway", "logs", "--service", service, "--lines", str(lines)],
        stderr=subprocess.STDOUT,
        timeout=120,
    )
    return out.decode("utf-8", errors="replace")


def _verify_log_text(text: str, expected_sha: str) -> tuple[bool, list[str]]:
    findings: list[str] = []
    ok = True

    if "[SCHEDULER BUILD INFO]" not in text:
        ok = False
        findings.append("MISSING [SCHEDULER BUILD INFO]")
    else:
        findings.append("FOUND [SCHEDULER BUILD INFO]")

    sha_match = re.search(r"git_sha=([0-9a-f]+)", text, re.IGNORECASE)
    if not sha_match:
        ok = False
        findings.append("MISSING git_sha=...")
    else:
        got = sha_match.group(1).lower()[: len(expected_sha)]
        exp = expected_sha.lower()
        if got != exp and not sha_match.group(1).lower().startswith(exp):
            ok = False
            findings.append(f"git_sha mismatch got={sha_match.group(1)} expected={exp}")
        else:
            findings.append(f"git_sha OK ({sha_match.group(1)})")

    if "process_role=scheduler" not in text:
        ok = False
        findings.append("MISSING process_role=scheduler")
    else:
        findings.append("FOUND process_role=scheduler")

    if "[DASHBOARD SNAPSHOT ARCHIVE CONFIG]" not in text:
        ok = False
        findings.append("MISSING [DASHBOARD SNAPSHOT ARCHIVE CONFIG]")
    else:
        findings.append("FOUND [DASHBOARD SNAPSHOT ARCHIVE CONFIG]")

    arch_match = re.search(r"archive_enabled=(true|false)", text, re.IGNORECASE)
    if arch_match:
        findings.append(f"archive_enabled={arch_match.group(1).lower()}")
    else:
        findings.append("archive_enabled not found in logs")

    return ok, findings


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--expected-sha", default="18d46ad")
    parser.add_argument("--service", default="smart-reply-ai-scheduler")
    parser.add_argument("--lines", type=int, default=800)
    parser.add_argument("--log-file", default="")
    args = parser.parse_args()

    if args.log_file:
        text = Path(args.log_file).read_text(encoding="utf-8", errors="replace")
        source = args.log_file
    else:
        try:
            text = _fetch_railway_logs(args.service, args.lines)
            source = f"railway logs --service {args.service}"
        except (OSError, subprocess.SubprocessError) as exc:
            print(f"Could not fetch Railway logs: {exc}")
            print(
                "Run manually: railway logs --service <scheduler> | "
                "findstr \"SCHEDULER BUILD INFO DASHBOARD SNAPSHOT ARCHIVE CONFIG\""
            )
            return 1

    ok, findings = _verify_log_text(text, args.expected_sha)
    report = "\n".join(
        [
            f"source={source}",
            f"expected_sha={args.expected_sha}",
            f"verified={'PASS' if ok else 'FAIL'}",
            *findings,
        ]
    )
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    OUT_FILE.write_text(report + "\n", encoding="utf-8")
    print(report)
    print(f"\nWrote {OUT_FILE}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
