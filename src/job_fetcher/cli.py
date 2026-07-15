from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .boards import BOARDS, select_boards
from .fetchers import fetch_all
from .pipeline import deduplicate, write_csv, write_json


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="job-fetcher",
        description=(
            "Fetch software engineering jobs from 15 VC portfolio boards, "
            "filter by location, and deduplicate by company + title."
        ),
    )
    parser.add_argument(
        "--location",
        default="United Kingdom",
        help="Location to match (default: United Kingdom)",
    )
    parser.add_argument(
        "--firm",
        action="append",
        help="Fetch one firm by its exact name; repeat for multiple firms",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("jobs.json"),
        help="JSON output path (default: jobs.json)",
    )
    parser.add_argument("--csv", type=Path, help="Optional CSV output path")
    parser.add_argument(
        "--workers", type=int, default=6, help="Concurrent boards (default: 6)"
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=30,
        help="Per-request timeout in seconds (default: 30)",
    )
    parser.add_argument(
        "--list-firms", action="store_true", help="Print configured firms and exit"
    )
    return parser


def run(args: argparse.Namespace) -> int:
    if args.list_firms:
        for board in BOARDS:
            print(board.name)
        return 0
    if args.workers < 1:
        raise ValueError("--workers must be at least 1")
    boards = select_boards(args.firm)
    jobs, errors = fetch_all(
        boards,
        args.location,
        workers=args.workers,
        timeout=args.timeout,
    )
    unique_jobs = deduplicate(jobs)
    write_json(unique_jobs, args.output)
    if args.csv:
        write_csv(unique_jobs, args.csv)

    print(
        f"Saved {len(unique_jobs)} unique jobs from "
        f"{len(boards) - len(errors)}/{len(boards)} boards to {args.output}"
    )
    for firm, error in sorted(errors.items()):
        print(f"warning: {firm}: {error}", file=sys.stderr)
    return 1 if errors and len(errors) == len(boards) else 0


def main() -> None:
    parser = build_parser()
    try:
        code = run(parser.parse_args())
    except (OSError, ValueError) as exc:
        parser.error(str(exc))
    raise SystemExit(code)


if __name__ == "__main__":
    main()
