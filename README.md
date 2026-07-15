# VC Job Fetcher

A dependency-free Python agent that searches 15 venture-capital portfolio job
boards for software engineering roles, filters them by location, and
deduplicates results using normalized `company name + job title`.

The default location is the United Kingdom. UK matching understands common
aliases and cities such as `UK`, `United Kingdom`, `England`, `Scotland`,
`London`, `Manchester`, and `Edinburgh`.

## Supported firms

- Accel
- Lightspeed Venture Partners
- General Catalyst
- Andreessen Horowitz (a16z)
- Sequoia Capital
- Bessemer Venture Partners
- Insight Partners
- 8VC
- Menlo Ventures
- Khosla Ventures
- Kleiner Perkins
- Greylock Partners
- New Enterprise Associates (NEA)
- Battery Ventures
- Sapphire Ventures

The fetcher uses the structured data exposed by the firms' Getro and Consider
portfolio boards. It does not need browser automation, an LLM, or an API key.

## Setup

Python 3.11 or newer is required.

```bash
python3 -m venv .venv
. .venv/bin/activate
python3 -m pip install -e .
```

## Usage

Fetch UK jobs from all firms:

```bash
job-fetcher --location "United Kingdom" --output jobs.json --csv jobs.csv
```

Run without installing:

```bash
PYTHONPATH=src python3 -m job_fetcher --location "United Kingdom"
```

Fetch selected firms:

```bash
job-fetcher \
  --firm "Accel" \
  --firm "Andreessen Horowitz (a16z)" \
  --location "United Kingdom"
```

Show all accepted firm names:

```bash
job-fetcher --list-firms
```

Useful tuning options:

```text
--workers 6       number of boards fetched concurrently
--timeout 30      timeout for each HTTP request
--output PATH     JSON destination
--csv PATH        optional CSV destination
```

Each record includes the company, title, locations, application URL, posting
date when supplied, remote status, fetch time, and every VC board where the
role appeared. If one third-party board is unavailable, the other boards still
produce output and the failed board is reported as a warning.

## Deploy on Render

The included `render.yaml` deploys the fetcher as a Python web service in
Render's Frankfurt region. It starts refreshing immediately and then refreshes
every 12 hours.

1. Merge this repository's deployment changes into the default branch.
2. Open the [Render Blueprint deployment page][render-deploy].
3. Connect the GitHub repository and approve the `vc-job-fetcher` service.
4. Wait for `/health` to pass, then open the generated `onrender.com` URL.

[render-deploy]: https://render.com/deploy?repo=https://github.com/siddha1305-lab/Job-Fetcher

API endpoints:

```text
GET /          responsive job-search web interface
GET /health    deployment and refresh health
GET /jobs      metadata, board errors, and deduplicated jobs
```

The web interface provides free-text search, portfolio and remote-work filters,
responsive job cards, and direct application links. It is served by the same
Python process as the API, so no separate frontend service is required.

To use the JSON API directly:

```bash
curl https://YOUR-SERVICE.onrender.com/jobs
```

The Blueprint defaults to Render's free plan. Free web services sleep when
idle, so a request after an idle period can have a cold start. The process
refreshes stale data when it wakes, and `/jobs` can briefly return an empty
snapshot with `"refreshing": true` during the first fetch. Use a paid,
always-on instance if the 12-hour refresh schedule must run at exact times.

The service keeps its current snapshot in memory because Render's service
filesystem is ephemeral. A restarted instance rebuilds that snapshot from the
portfolio boards; no generated jobs file needs to be deployed.

To change deployment behavior in the Render dashboard, set:

```text
JOB_LOCATION=United Kingdom
REFRESH_INTERVAL_SECONDS=43200
FETCH_WORKERS=6
FETCH_TIMEOUT_SECONDS=30
```

## Deduplication

Company names and titles are lowercased, Unicode-normalized, stripped of
punctuation, and whitespace-normalized. Common company suffixes such as `Ltd`,
`Inc`, and `LLC` are ignored. Exact normalized `(company, title)` matches are
merged; source firms and locations are preserved.

This intentionally does not fuzzy-match titles. For example, `Software
Engineer` and `Senior Software Engineer` remain separate roles.

## Tests

```bash
PYTHONPATH=src python3 -m unittest discover -s tests -v
```

The tests are offline. A real run is the integration check because portfolio
boards are third-party services whose schemas and availability can change.

## Responsible use

Requests are bounded, retried with backoff, and identify this project with a
user agent. Run the fetcher on a reasonable schedule (for example once or
twice daily), and review each board's terms before operating it at larger
scale.
