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
