import tempfile
import unittest
from pathlib import Path

from job_fetcher.boards import BOARDS, select_boards
from job_fetcher.filtering import (
    dedup_key,
    is_software_engineering_title,
    matches_location,
)
from job_fetcher.models import Job
from job_fetcher.pipeline import deduplicate, write_csv, write_json


def job(
    company: str,
    title: str,
    source: str,
    locations: list[str] | None = None,
) -> Job:
    return Job(
        company=company,
        title=title,
        locations=locations or ["London, UK"],
        url=f"https://example.com/{source}",
        source_firms=[source],
    )


class FilteringTests(unittest.TestCase):
    def test_software_titles(self) -> None:
        accepted = [
            "Senior Software Engineer",
            "Backend Developer",
            "Site Reliability Engineer",
            "Engineering Manager, Platform",
        ]
        rejected = [
            "Solutions Engineer",
            "Mechanical Engineer",
            "Account Executive",
            "Principal Developer Advocate",
            "Mobile Product Manager",
        ]
        self.assertTrue(all(is_software_engineering_title(x) for x in accepted))
        self.assertFalse(any(is_software_engineering_title(x) for x in rejected))

    def test_uk_aliases_and_other_locations(self) -> None:
        self.assertTrue(matches_location(["London, England"], "United Kingdom"))
        self.assertTrue(matches_location(["Remote (UK)"], "United Kingdom"))
        self.assertFalse(matches_location(["Remote (US)"], "United Kingdom"))
        self.assertTrue(matches_location(["Paris, France"], "Paris"))

    def test_company_legal_suffix_is_ignored(self) -> None:
        self.assertEqual(
            dedup_key("Example Ltd.", "Software Engineer"),
            dedup_key("EXAMPLE", "Software-Engineer"),
        )


class PipelineTests(unittest.TestCase):
    def test_deduplicates_company_and_title_and_merges_sources(self) -> None:
        result = deduplicate(
            [
                job("Acme Ltd", "Senior Software Engineer", "Accel"),
                job(
                    "ACME",
                    "Senior Software Engineer",
                    "a16z",
                    ["Edinburgh, Scotland"],
                ),
                job("Acme", "Backend Developer", "Accel"),
            ]
        )
        self.assertEqual(len(result), 2)
        merged = next(x for x in result if x.title == "Senior Software Engineer")
        self.assertEqual(merged.source_firms, ["a16z", "Accel"])
        self.assertEqual(
            merged.locations, ["Edinburgh, Scotland", "London, UK"]
        )

    def test_writes_json_and_csv(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            json_path = Path(directory) / "jobs.json"
            csv_path = Path(directory) / "jobs.csv"
            jobs = [job("Acme", "Software Engineer", "Accel")]
            write_json(jobs, json_path)
            write_csv(jobs, csv_path)
            self.assertIn('"company": "Acme"', json_path.read_text())
            self.assertIn("Software Engineer", csv_path.read_text())


class BoardTests(unittest.TestCase):
    def test_exactly_fifteen_boards_are_configured(self) -> None:
        self.assertEqual(len(BOARDS), 15)
        self.assertIn("Accel", {board.name for board in BOARDS})
        self.assertIn(
            "Lightspeed Venture Partners", {board.name for board in BOARDS}
        )
        self.assertIn(
            "Andreessen Horowitz (a16z)", {board.name for board in BOARDS}
        )

    def test_select_boards_rejects_unknown_name(self) -> None:
        self.assertEqual(select_boards(["Accel"])[0].name, "Accel")
        with self.assertRaises(ValueError):
            select_boards(["Not a firm"])


if __name__ == "__main__":
    unittest.main()
