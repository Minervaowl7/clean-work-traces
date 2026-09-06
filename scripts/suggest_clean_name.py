#!/usr/bin/env python3
"""Preview a concise dated deliverable filename without changing files."""

from __future__ import annotations

import argparse
from datetime import date
from pathlib import Path


def suggest_name(source: Path, keep_through: str, date_text: str) -> Path:
    if not source.name:
        raise ValueError("source filename is empty")
    if not keep_through:
        raise ValueError("keep_through must not be empty")
    if len(date_text) != 8 or not date_text.isdigit():
        raise ValueError("date must use YYYYMMDD")
    stem = source.stem
    marker_index = stem.find(keep_through)
    if marker_index < 0:
        raise ValueError(f"marker not found in filename: {keep_through}")
    prefix = stem[: marker_index + len(keep_through)].rstrip(" -_—")
    return source.with_name(f"{prefix}-{date_text}{source.suffix}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("--keep-through", required=True, help="Keep the filename through this marker and drop later work suffixes.")
    parser.add_argument("--date", default=date.today().strftime("%Y%m%d"), help="Date suffix in YYYYMMDD format; defaults to today.")
    args = parser.parse_args()
    print(suggest_name(args.source, args.keep_through, args.date))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
