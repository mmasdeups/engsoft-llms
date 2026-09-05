#!/usr/bin/env python3
"""Summarise meter logs written by token_meter.py.

    python meter_report.py part1-baseline.jsonl part1-used.jsonl
    python meter_report.py cli-road.jsonl browser-road.jsonl

For Part 1 you want `first_call_prompt_tokens`.
For Part 2 you want `TOTAL`.
"""

import json
import sys

GAP_SECONDS = 30  # a pause longer than this probably means a new run


def load(path):
    rows = []
    with open(path) as handle:
        for line in handle:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def totals(row):
    prompt = row.get("prompt_tokens") or 0
    completion = row.get("completion_tokens") or 0
    total = row.get("total_tokens")
    if total is None:
        total = prompt + completion
    return prompt, completion, total


def report(path):
    try:
        rows = load(path)
    except FileNotFoundError:
        print(f"\n=== {path} ===\n  (no such file)")
        return

    failures = [r for r in rows if not r.get("ok")]
    rows = [r for r in rows if r.get("ok")]

    print(f"\n=== {path} ===")
    if not rows:
        print("  no successful calls")
        if failures:
            print(f"  {len(failures)} failed call(s); first error: {failures[0].get('error')}")
        return

    print(f"{'#':>3}  {'gap(s)':>7}  {'prompt':>8}  {'compl':>7}  {'total':>8}")
    previous = None
    for index, row in enumerate(rows, 1):
        prompt, completion, total = totals(row)
        gap = "" if previous is None else f"{row['ts'] - previous:.1f}"
        marker = ""
        if previous is not None and row["ts"] - previous > GAP_SECONDS:
            marker = "   <- new run?"
        print(f"{index:>3}  {gap:>7}  {prompt:>8}  {completion:>7}  {total:>8}{marker}")
        previous = row["ts"]

    sum_prompt = sum(totals(r)[0] for r in rows)
    sum_completion = sum(totals(r)[1] for r in rows)
    sum_total = sum(totals(r)[2] for r in rows)

    print()
    print(f"  calls                     : {len(rows)}")
    print(f"  first_call_prompt_tokens  : {rows[0].get('prompt_tokens')}   <- Part 1 number")
    print(f"  prompt / completion       : {sum_prompt} / {sum_completion}")
    print(f"  TOTAL                     : {sum_total}   <- Part 2 number")
    if failures:
        print(f"  failed calls              : {len(failures)}")


if __name__ == "__main__":
    for path in sys.argv[1:] or ["meter.jsonl"]:
        report(path)
