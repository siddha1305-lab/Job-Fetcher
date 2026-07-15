from __future__ import annotations

import base64
import json
import random
import re
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urlsplit, urlunsplit
from urllib.request import Request, urlopen

from .filtering import is_software_engineering_title, matches_location
from .models import Board, Job

USER_AGENT = (
    "VCJobFetcher/0.1 (+https://github.com/siddha1305-lab/Job-Fetcher)"
)
SEARCH_TERMS = (
    "software",
    "developer",
    "frontend",
    "backend",
    "full stack",
    "devops",
    "site reliability",
    "mobile engineer",
)
NEXT_DATA = re.compile(
    r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>',
    re.DOTALL,
)


class FetchError(RuntimeError):
    pass


def _request_json_or_text(
    url: str,
    *,
    payload: dict[str, Any] | None = None,
    timeout: float = 30,
    retries: int = 2,
) -> bytes:
    body = json.dumps(payload).encode() if payload is not None else None
    headers = {"Accept": "application/json", "User-Agent": USER_AGENT}
    if body is not None:
        headers["Content-Type"] = "application/json"
    request = Request(url, data=body, headers=headers, method="POST" if body else "GET")
    for attempt in range(retries + 1):
        try:
            with urlopen(request, timeout=timeout) as response:
                return response.read()
        except HTTPError as exc:
            retryable = exc.code == 429 or 500 <= exc.code < 600
            if not retryable or attempt == retries:
                raise FetchError(f"{url}: HTTP {exc.code}") from exc
        except (TimeoutError, URLError) as exc:
            if attempt == retries:
                raise FetchError(f"{url}: {exc}") from exc
        time.sleep((2**attempt) + random.random())
    raise AssertionError("retry loop exhausted")


def _getro_url(board: Board, term: str, location: str) -> str:
    location_filter = base64.b64encode(
        json.dumps(
            {"searchable_locations": [location]}, separators=(",", ":")
        ).encode()
    ).decode()
    parts = urlsplit(board.url)
    query = urlencode({"q": term, "filter": location_filter})
    return urlunsplit((parts.scheme, parts.netloc, parts.path, query, ""))


def _timestamp(value: Any) -> str | None:
    if isinstance(value, (int, float)):
        return datetime.fromtimestamp(value, timezone.utc).isoformat()
    return value if isinstance(value, str) and value else None


def _logo_url(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    value = value.strip()
    return value if urlsplit(value).scheme in {"http", "https"} else None


def _consider_logo(raw: dict[str, Any]) -> str | None:
    direct = _logo_url(raw.get("companyLogo") or raw.get("logoUrl"))
    if direct:
        return direct
    logos = raw.get("companyLogos") or {}
    if not isinstance(logos, dict):
        return None
    for source in ("manual", "linkedin", "clearbit", "crunchbase"):
        candidate = logos.get(source)
        if isinstance(candidate, dict):
            candidate = candidate.get("src") or candidate.get("url")
        logo = _logo_url(candidate)
        if logo:
            return logo
    return None


def _parse_getro_job(raw: dict[str, Any], board: Board) -> Job:
    organization = raw.get("organization") or {}
    locations = [str(value) for value in raw.get("locations") or []]
    return Job(
        company=str(organization.get("name") or "Unknown company"),
        title=str(raw.get("title") or ""),
        locations=locations,
        url=str(raw.get("url") or ""),
        source_firms=[board.name],
        logo_url=_logo_url(organization.get("logoUrl")),
        posted_at=_timestamp(raw.get("createdAt")),
        remote=raw.get("workMode") == "remote"
        or any("remote" in value.casefold() for value in locations),
    )


def fetch_getro(board: Board, location: str, timeout: float) -> list[Job]:
    found: dict[Any, Job] = {}
    for term in SEARCH_TERMS:
        html = _request_json_or_text(
            _getro_url(board, term, location), timeout=timeout
        ).decode("utf-8", errors="replace")
        match = NEXT_DATA.search(html)
        if not match:
            raise FetchError(f"{board.name}: Getro data was not present in the page")
        state = json.loads(match.group(1))
        raw_jobs = state["props"]["pageProps"]["initialState"]["jobs"]["found"]
        for raw in raw_jobs:
            job = _parse_getro_job(raw, board)
            if (
                job.title
                and job.url
                and is_software_engineering_title(job.title)
                and matches_location(job.locations, location)
            ):
                found[raw.get("id") or job.url] = job
    return list(found.values())


def _parse_consider_job(raw: dict[str, Any], board: Board) -> Job:
    locations = [str(value) for value in raw.get("locations") or []]
    return Job(
        company=str(raw.get("companyName") or "Unknown company"),
        title=str(raw.get("title") or ""),
        locations=locations,
        url=str(raw.get("applyUrl") or raw.get("url") or ""),
        source_firms=[board.name],
        logo_url=_consider_logo(raw),
        posted_at=_timestamp(
            raw.get("postedAt") or raw.get("createdAt") or raw.get("publishedAt")
        ),
        remote=bool(raw.get("remote"))
        or any("remote" in value.casefold() for value in locations),
    )


def fetch_consider(board: Board, location: str, timeout: float) -> list[Job]:
    parts = urlsplit(board.url)
    endpoint = urlunsplit(
        (parts.scheme, parts.netloc, "/api-boards/search-jobs", "", "")
    )
    found: dict[Any, Job] = {}
    for term in SEARCH_TERMS:
        payload = {
            "meta": {"size": 50},
            "board": {"id": board.board_id, "isParent": True},
            "query": {"titlePrefix": term, "locations": [location]},
            "grouped": False,
        }
        response = json.loads(
            _request_json_or_text(
                endpoint, payload=payload, timeout=timeout
            ).decode()
        )
        if response.get("errors"):
            raise FetchError(f"{board.name}: {response['errors']}")
        for raw in response.get("jobs", []):
            job = _parse_consider_job(raw, board)
            if (
                job.title
                and job.url
                and is_software_engineering_title(job.title)
                and matches_location(job.locations, location)
            ):
                found[raw.get("jobId") or raw.get("id") or job.url] = job
    return list(found.values())


def fetch_board(board: Board, location: str, timeout: float = 30) -> list[Job]:
    if board.provider == "getro":
        return fetch_getro(board, location, timeout)
    if board.provider == "consider":
        return fetch_consider(board, location, timeout)
    raise FetchError(f"{board.name}: unsupported provider {board.provider!r}")


def fetch_all(
    boards: tuple[Board, ...],
    location: str,
    *,
    workers: int = 6,
    timeout: float = 30,
) -> tuple[list[Job], dict[str, str]]:
    jobs: list[Job] = []
    errors: dict[str, str] = {}
    with ThreadPoolExecutor(max_workers=min(workers, len(boards))) as executor:
        futures = {
            executor.submit(fetch_board, board, location, timeout): board
            for board in boards
        }
        for future in as_completed(futures):
            board = futures[future]
            try:
                jobs.extend(future.result())
            except Exception as exc:  # isolate one changing third-party board
                errors[board.name] = str(exc)
    return jobs, errors
