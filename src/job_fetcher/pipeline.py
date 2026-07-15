from __future__ import annotations

import csv
import json
from pathlib import Path

from .filtering import dedup_key
from .models import Job


def deduplicate(jobs: list[Job]) -> list[Job]:
    unique: dict[tuple[str, str], Job] = {}
    for job in jobs:
        key = dedup_key(job.company, job.title)
        if key not in unique:
            unique[key] = job
            continue
        current = unique[key]
        current.source_firms = sorted(
            set(current.source_firms).union(job.source_firms),
            key=str.casefold,
        )
        current.locations = sorted(
            set(current.locations).union(job.locations),
            key=str.casefold,
        )
        current.remote = current.remote or job.remote
        if not current.posted_at and job.posted_at:
            current.posted_at = job.posted_at
    return sorted(
        unique.values(),
        key=lambda job: (job.company.casefold(), job.title.casefold()),
    )


def write_json(jobs: list[Job], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps([job.to_dict() for job in jobs], indent=2, ensure_ascii=False)
        + "\n",
        encoding="utf-8",
    )


def write_csv(jobs: list[Job], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=(
                "company",
                "title",
                "locations",
                "remote",
                "url",
                "source_firms",
                "posted_at",
                "fetched_at",
            ),
        )
        writer.writeheader()
        for job in jobs:
            row = job.to_dict()
            row["locations"] = " | ".join(job.locations)
            row["source_firms"] = " | ".join(job.source_firms)
            writer.writerow(row)
