from .models import Board


# The mix of Getro and Consider boards covers large US and European portfolios.
# Board URLs and identifiers are data, so adding/replacing a firm does not require
# changing the fetching pipeline.
BOARDS: tuple[Board, ...] = (
    Board("Accel", "https://jobs.accel.com/jobs", "getro"),
    Board(
        "Lightspeed Venture Partners",
        "https://jobs.lsvp.com/jobs",
        "consider",
        "lightspeed",
    ),
    Board(
        "General Catalyst", "https://jobs.generalcatalyst.com/jobs", "getro"
    ),
    Board(
        "Andreessen Horowitz (a16z)",
        "https://portfoliojobs.a16z.com/jobs",
        "consider",
        "andreessen-horowitz",
    ),
    Board(
        "Sequoia Capital",
        "https://jobs.sequoiacap.com/jobs/",
        "consider",
        "sequoia-capital",
    ),
    Board(
        "Bessemer Venture Partners",
        "https://jobs.bvp.com/jobs",
        "consider",
        "bessemer-ventures",
    ),
    Board("Insight Partners", "https://jobs.insightpartners.com/jobs", "getro"),
    Board("8VC", "https://jobs.8vc.com/jobs", "getro"),
    Board("Menlo Ventures", "https://jobs.menlovc.com/jobs", "getro"),
    Board("Khosla Ventures", "https://jobs.khoslaventures.com/jobs", "getro"),
    Board(
        "Kleiner Perkins",
        "https://jobs.kleinerperkins.com/jobs",
        "consider",
        "kleiner-perkins",
    ),
    Board(
        "Greylock Partners",
        "https://jobs.greylock.com/jobs",
        "consider",
        "greylock",
    ),
    Board(
        "New Enterprise Associates (NEA)",
        "https://careers.nea.com/jobs",
        "consider",
        "nea",
    ),
    Board(
        "Battery Ventures",
        "https://jobs.battery.com/jobs",
        "consider",
        "battery-ventures",
    ),
    Board(
        "Sapphire Ventures",
        "https://jobs.sapphireventures.com/jobs",
        "getro",
    ),
)


def select_boards(names: list[str] | None) -> tuple[Board, ...]:
    if not names:
        return BOARDS
    requested = {name.casefold() for name in names}
    selected = tuple(board for board in BOARDS if board.name.casefold() in requested)
    missing = requested - {board.name.casefold() for board in selected}
    if missing:
        available = ", ".join(board.name for board in BOARDS)
        raise ValueError(
            f"Unknown firm(s): {', '.join(sorted(missing))}. Available: {available}"
        )
    return selected
