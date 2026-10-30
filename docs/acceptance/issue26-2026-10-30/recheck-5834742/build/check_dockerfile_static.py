#!/usr/bin/env python3
"""Bounded Dockerfile consistency checks; never executes Dockerfile commands."""
from __future__ import annotations

import json
import re
import shlex
import subprocess
import sys
from pathlib import Path

DOCKERFILE = Path("codex/Dockerfile")
CONTEXT = DOCKERFILE.parent
lines = DOCKERFILE.read_text(encoding="utf-8").splitlines()
instructions: list[tuple[str, str, int]] = []
i = 0
while i < len(lines):
    raw = lines[i]
    line_no = i + 1
    stripped = raw.lstrip()
    if not stripped or stripped.startswith("#"):
        i += 1
        continue

    # A heredoc COPY consumes source lines through its delimiter; those lines
    # must not be parsed as Dockerfile instructions.
    if re.match(r"COPY\s+<<", stripped, re.IGNORECASE):
        header = stripped
        match = re.search(r"<<-?\s*(['\"]?)([A-Za-z_][A-Za-z0-9_]*)\1", header)
        if not match:
            raise SystemExit(f"FAIL line {line_no}: unsupported COPY heredoc delimiter")
        delimiter = match.group(2)
        i += 1
        while i < len(lines) and lines[i].strip() != delimiter:
            i += 1
        if i == len(lines):
            raise SystemExit(f"FAIL line {line_no}: unterminated COPY heredoc {delimiter}")
        i += 1
        continue

    logical = raw
    while logical.rstrip().endswith("\\"):
        logical = logical.rstrip()[:-1] + " "
        i += 1
        if i >= len(lines):
            raise SystemExit(f"FAIL line {line_no}: dangling continuation")
        logical += lines[i].lstrip()
    match = re.match(r"\s*([A-Za-z]+)\s+(.*)", logical, re.DOTALL)
    if not match:
        raise SystemExit(f"FAIL line {line_no}: could not parse instruction")
    instructions.append((match.group(1).upper(), match.group(2).strip(), line_no))
    i += 1

print(f"Dockerfile: {DOCKERFILE}; bounded logical instruction scan: PASS ({len(instructions)} instructions)")

run_count = 0
for keyword, body, line_no in instructions:
    if keyword == "RUN":
        # bash -n parses the exact shell-form RUN payload; it does not execute it.
        check = subprocess.run(["bash", "-n", "-c", body], text=True, capture_output=True)
        run_count += 1
        if check.returncode:
            print(f"FAIL RUN line {line_no}: {check.stderr.strip()}")
            sys.exit(check.returncode)
        print(f"PASS bash -n: RUN at Dockerfile line {line_no}")
    elif keyword == "COPY":
        try:
            tokens = shlex.split(body)
        except ValueError as exc:
            raise SystemExit(f"FAIL COPY line {line_no}: {exc}")
        # Docker COPY flags precede sources; --from sources are external and
        # are not checked as local context paths.
        local = True
        while tokens and tokens[0].startswith("--"):
            if tokens[0].startswith("--from=") or tokens[0] == "--from":
                local = False
            tokens.pop(0)
        if not local:
            print(f"INFO COPY line {line_no}: external --from source skipped")
            continue
        if len(tokens) < 2:
            raise SystemExit(f"FAIL COPY line {line_no}: expected source and destination")
        for source in tokens[:-1]:
            if any(c in source for c in "*?["):
                # Docker supports wildcard source expansion; this Dockerfile
                # currently has none. Keep this checker intentionally bounded.
                raise SystemExit(f"FAIL COPY line {line_no}: wildcard source not supported by bounded check: {source}")
            path = (CONTEXT / source).resolve()
            if not path.exists() or not path.is_relative_to(CONTEXT.resolve()):
                raise SystemExit(f"FAIL COPY line {line_no}: missing/out-of-context source {source}")
            print(f"PASS COPY source exists in codex context: line {line_no}: {source}")
    elif keyword in {"ENTRYPOINT", "CMD"} and body.startswith("["):
        try:
            value = json.loads(body)
        except json.JSONDecodeError as exc:
            raise SystemExit(f"FAIL {keyword} JSON at line {line_no}: {exc}")
        if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
            raise SystemExit(f"FAIL {keyword} JSON at line {line_no}: expected array of strings")
        print(f"PASS JSON {keyword} at Dockerfile line {line_no}: {value!r}")

print(f"RUN shell payloads syntax-checked, not executed: {run_count}")
print("Scope limitation: this is not full Dockerfile frontend/parser validation; no build, image pull, package resolution, architecture compilation, or runtime test was performed.")
