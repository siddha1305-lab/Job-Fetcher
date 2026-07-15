from __future__ import annotations

import re
import unicodedata


SOFTWARE_TITLE = re.compile(
    r"\b("
    r"software|developer|programmer|full[\s-]?stack|front[\s-]?end|back[\s-]?end|"
    r"(?:mobile|ios|android)(?: software)? (?:engineer|developer)|"
    r"devops|site reliability|sre|platform engineer|"
    r"cloud engineer|infrastructure engineer|application engineer|"
    r"engineering manager|quality (?:assurance|engineer)|test automation"
    r")\b",
    re.IGNORECASE,
)

NON_SOFTWARE_TITLE = re.compile(
    r"\b("
    r"sales|solutions?|support|customer|mechanical|electrical|hardware|"
    r"manufacturing|civil|chemical|field|network|security guard|"
    r"recruit|marketing|advocate|evangelist|developer relations"
    r")\b",
    re.IGNORECASE,
)

UK_ALIASES = re.compile(
    r"\b("
    r"united kingdom|u\.?k\.?|great britain|england|scotland|wales|"
    r"northern ireland|london|manchester|edinburgh|glasgow|bristol|"
    r"birmingham|cambridge|oxford|leeds|liverpool|cardiff|belfast"
    r")\b",
    re.IGNORECASE,
)

LEGAL_SUFFIXES = re.compile(
    r"\b(?:limited|ltd|incorporated|inc|corp(?:oration)?|llc|plc)\b\.?",
    re.IGNORECASE,
)


def is_software_engineering_title(title: str) -> bool:
    return bool(SOFTWARE_TITLE.search(title)) and not bool(
        NON_SOFTWARE_TITLE.search(title)
    )


def matches_location(locations: list[str], requested: str) -> bool:
    location_text = " | ".join(locations)
    normalized_request = requested.strip().casefold()
    if normalized_request in {"uk", "u.k.", "united kingdom", "great britain"}:
        return bool(UK_ALIASES.search(location_text))
    return normalized_request in location_text.casefold()


def normalize_key_part(value: str, *, company: bool = False) -> str:
    value = unicodedata.normalize("NFKD", value)
    value = "".join(char for char in value if not unicodedata.combining(char))
    if company:
        value = LEGAL_SUFFIXES.sub("", value)
    return re.sub(r"[^a-z0-9]+", " ", value.casefold()).strip()


def dedup_key(company: str, title: str) -> tuple[str, str]:
    return (
        normalize_key_part(company, company=True),
        normalize_key_part(title),
    )
