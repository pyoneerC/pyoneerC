"""Daily GitHub Profile README updater.

Updates SVG profile cards with live stats from GitHub API and uptime calculations.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date
from functools import cached_property
from pathlib import Path
from typing import TYPE_CHECKING
from xml.etree import ElementTree

import requests
from dateutil.relativedelta import relativedelta

if TYPE_CHECKING:
    from collections.abc import Iterator


# === Configuration ===

GITHUB_USERNAME = "pyoneerc"
BIRTH_DATE = date(2005, 3, 3)
LIFE_EXPECTANCY_DAYS = 27485  # Argentina male life expectancy ~75.3 years
SVG_FILES = ("dark_mode.svg", "light_mode.svg")

GITHUB_API = f"https://api.github.com/users/{GITHUB_USERNAME}"
GITHUB_STATS_API = "https://github-readme-stats.vercel.app/api"


# === Data Models ===


@dataclass(frozen=True, slots=True)
class UptimeStats:
    """Immutable container for uptime calculations."""

    years: int
    months: int
    days: int
    total_days: int
    life_percentage: float

    @classmethod
    def from_birthdate(cls, birthdate: date) -> UptimeStats:
        """Calculate uptime stats from a birthdate."""
        today = date.today()
        delta = relativedelta(today, birthdate)
        total_days = (today - birthdate).days

        return cls(
            years=delta.years,
            months=delta.months,
            days=delta.days,
            total_days=total_days,
            life_percentage=round((total_days / LIFE_EXPECTANCY_DAYS) * 100, 2),
        )

    @property
    def formatted_uptime(self) -> str:
        """Human-readable uptime string with proper pluralization."""
        m = "month" if self.months == 1 else "months"
        d = "day" if self.days == 1 else "days"
        return f"{self.years} years, {self.months} {m}, {self.days} {d}"


@dataclass(frozen=True, slots=True)
class GitHubStats:
    """Immutable container for GitHub statistics."""

    repos: int
    followers: int
    stars: int
    commits: str
    contributed: str
    prs_merged: str
    prs_merged_pct: str

    @classmethod
    def fetch(cls, username: str) -> GitHubStats:
        """Fetch all GitHub stats in minimal API calls."""
        # User profile data
        user_data = requests.get(f"{GITHUB_API}", timeout=30).json()

        # Calculate total stars across all repos (paginated)
        stars = sum(
            repo["stargazers_count"]
            for repo in cls._paginate_repos(user_data["repos_url"])
        )

        # Fetch stats from readme-stats API
        stats_svg = cls._fetch_stats_svg(username, "include_all_commits=true")
        merged_svg = cls._fetch_stats_svg(
            username, "show=prs_merged,prs_merged_percentage"
        )

        return cls(
            repos=user_data["public_repos"],
            followers=user_data["followers"],
            stars=stars,
            commits=cls._extract_stat(stats_svg, "commits"),
            contributed=cls._extract_stat(stats_svg, "contribs"),
            prs_merged=cls._extract_stat(merged_svg, "prs_merged"),
            prs_merged_pct=cls._extract_stat(merged_svg, "prs_merged_percentage")[:2]
            + "%",
        )

    @staticmethod
    def _paginate_repos(repos_url: str) -> Iterator[dict]:
        """Yield all repos, handling GitHub API pagination."""
        page = 1
        while True:
            response = requests.get(
                repos_url, params={"page": page, "per_page": 100}, timeout=30
            )
            repos = response.json()
            if not repos:
                break
            yield from repos
            page += 1

    @staticmethod
    def _fetch_stats_svg(username: str, params: str) -> ElementTree.Element:
        """Fetch and parse GitHub readme stats SVG."""
        url = f"{GITHUB_STATS_API}?username={username}&{params}"
        response = requests.get(url, timeout=30)
        return ElementTree.fromstring(response.content)

    @staticmethod
    def _extract_stat(svg: ElementTree.Element, testid: str) -> str:
        """Extract stat value from SVG by data-testid attribute."""
        ns = {"svg": "http://www.w3.org/2000/svg"}
        elem = svg.find(f'.//svg:text[@data-testid="{testid}"]', ns)
        return elem.text if elem is not None else "0"


# === SVG Updater ===


class SVGUpdater:
    """Efficient SVG content updater using regex patterns."""

    # Pre-compiled regex patterns for each stat field
    PATTERNS: dict[str, re.Pattern] = {
        "uptime": re.compile(
            r'(<tspan x="370" y="90" class="keyColor">Uptime</tspan>: <tspan class="valueColor">)[^<]*(</tspan>)'
        ),
        "total_days": re.compile(
            r'(<tspan x="680" y= "90" class="valueColor">)[^<]*(</tspan>)'
        ),
        "life_pct": re.compile(
            r'(<tspan x="760" y= "90" class="valueColor">)[^<]*(</tspan>)'
        ),
        "repos": re.compile(
            r'(<tspan x="370" y="490" class="keyColor">Repos</tspan>: <tspan class="valueColor">)[^<]*(</tspan>)'
        ),
        "followers": re.compile(
            r'(<tspan x="370" y="510" class="keyColor">Followers</tspan>: <tspan class="valueColor">)[^<]*(</tspan>)'
        ),
        "stars": re.compile(
            r'(<tspan x="520" y="510" class="keyColor">\|   Stars</tspan>: <tspan class="valueColor">)[^<]*(</tspan>)'
        ),
        "contributed": re.compile(
            r'(<tspan x="480" y="490" class="keyColor">Contributed</tspan>: <tspan class="valueColor">)[^<]*(</tspan>)'
        ),
        "commits": re.compile(
            r'(<tspan x="660" y="510" class="keyColor">\|   Commits</tspan>: <tspan class="valueColor">)[^<]*(</tspan>)'
        ),
        "prs_merged": re.compile(
            r'(<tspan x="660" y="490" class="keyColor">\|   Merged PRs</tspan>: <tspan class="valueColor">)[^<]*(</tspan>)'
        ),
    }

    def __init__(self, filepath: Path) -> None:
        self.filepath = filepath
        self._content: str | None = None

    @cached_property
    def content(self) -> str:
        """Lazy-load file content."""
        return self.filepath.read_text(encoding="utf-8")

    def update(self, pattern_key: str, value: str) -> None:
        """Replace a pattern match with a new value."""
        if self._content is None:
            self._content = self.content

        pattern = self.PATTERNS[pattern_key]
        self._content = pattern.sub(rf"\g<1>{value}\g<2>", self._content)

    def save(self) -> None:
        """Write updated content back to file."""
        if self._content is not None:
            self.filepath.write_text(self._content, encoding="utf-8")


# === Main Execution ===


def update_all_svgs(uptime: UptimeStats, github: GitHubStats) -> None:
    """Apply all updates to SVG files."""
    base_path = Path(__file__).parent

    for svg_file in SVG_FILES:
        updater = SVGUpdater(base_path / svg_file)

        # Uptime stats
        updater.update("uptime", uptime.formatted_uptime)
        updater.update("total_days", f"({uptime.total_days}d)")
        updater.update("life_pct", f"({uptime.life_percentage}%)")

        # GitHub stats
        updater.update("repos", str(github.repos))
        updater.update("followers", str(github.followers))
        updater.update("stars", str(github.stars))
        updater.update("contributed", github.contributed)
        updater.update("commits", github.commits)
        updater.update("prs_merged", f"{github.prs_merged} ({github.prs_merged_pct})")

        updater.save()
        print(f"✓ Updated {svg_file}")


def main() -> None:
    """Entry point: fetch stats and update SVGs."""
    print("🔄 Fetching stats...")

    uptime = UptimeStats.from_birthdate(BIRTH_DATE)
    github = GitHubStats.fetch(GITHUB_USERNAME)

    print(f"  Uptime: {uptime.formatted_uptime}")
    print(f"  Repos: {github.repos} | Stars: {github.stars} | Commits: {github.commits}")

    update_all_svgs(uptime, github)
    print("✅ Done!")


if __name__ == "__main__":
    main()
