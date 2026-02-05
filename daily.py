"""Daily GitHub Profile README updater.

Updates SVG profile cards with live stats from GitHub API and uptime calculations.
Designed to be resilient, maintainable, and future-proof.
"""

from __future__ import annotations

import logging
import re
import sys
from dataclasses import dataclass
from datetime import date
from functools import cached_property
from pathlib import Path
from time import sleep
from typing import TYPE_CHECKING
from xml.etree import ElementTree

import requests
from dateutil.relativedelta import relativedelta
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

if TYPE_CHECKING:
    from collections.abc import Iterator

# === Logging Setup ===

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger(__name__)


# === Configuration ===

GITHUB_USERNAME = "pyoneerc"
BIRTH_DATE = date(2005, 3, 3)
LIFE_EXPECTANCY_DAYS = 27485  # Argentina male ~75.3 years
SVG_FILES = ("dark_mode.svg", "light_mode.svg")

GITHUB_API = f"https://api.github.com/users/{GITHUB_USERNAME}"
GITHUB_STATS_API = "https://github-readme-stats.vercel.app/api"

# Retry config
MAX_RETRIES = 3
RETRY_BACKOFF = 1.0  # seconds
REQUEST_TIMEOUT = 30


# === HTTP Session with Retries ===


def create_session() -> requests.Session:
    """Create a requests session with automatic retries and backoff."""
    session = requests.Session()

    retry_strategy = Retry(
        total=MAX_RETRIES,
        backoff_factor=RETRY_BACKOFF,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["GET"],
        raise_on_status=False,
    )

    adapter = HTTPAdapter(max_retries=retry_strategy)
    session.mount("https://", adapter)
    session.mount("http://", adapter)

    return session


# Global session (reused across requests for connection pooling)
_session: requests.Session | None = None


def get_session() -> requests.Session:
    """Get or create the global HTTP session."""
    global _session
    if _session is None:
        _session = create_session()
    return _session


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
        """Calculate uptime stats from a birthdate. Always succeeds."""
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
    def fetch(cls, username: str) -> GitHubStats | None:
        """
        Fetch all GitHub stats with resilient error handling.
        Returns None if critical data cannot be fetched.
        """
        session = get_session()

        try:
            # User profile data (critical)
            user_resp = session.get(GITHUB_API, timeout=REQUEST_TIMEOUT)
            if not user_resp.ok:
                log.error(f"GitHub API error: {user_resp.status_code}")
                return None

            user_data = user_resp.json()

            # Stars calculation (non-critical, fallback to 0)
            stars = 0
            try:
                stars = sum(
                    repo.get("stargazers_count", 0)
                    for repo in cls._paginate_repos(session, user_data["repos_url"])
                )
            except Exception as e:
                log.warning(f"Failed to fetch stars: {e}")

            # Readme stats API (non-critical, fallback to "?")
            commits, contributed = "?", "?"
            prs_merged, prs_merged_pct = "?", "?%"

            try:
                stats_svg = cls._fetch_stats_svg(session, username, "include_all_commits=true")
                if stats_svg is not None:
                    commits = cls._extract_stat(stats_svg, "commits") or "?"
                    contributed = cls._extract_stat(stats_svg, "contribs") or "?"
            except Exception as e:
                log.warning(f"Failed to fetch commit stats: {e}")

            try:
                merged_svg = cls._fetch_stats_svg(
                    session, username, "show=prs_merged,prs_merged_percentage"
                )
                if merged_svg is not None:
                    prs_merged = cls._extract_stat(merged_svg, "prs_merged") or "?"
                    pct_raw = cls._extract_stat(merged_svg, "prs_merged_percentage") or "0"
                    prs_merged_pct = pct_raw[:2].strip() + "%"
            except Exception as e:
                log.warning(f"Failed to fetch PR stats: {e}")

            return cls(
                repos=user_data.get("public_repos", 0),
                followers=user_data.get("followers", 0),
                stars=stars,
                commits=commits,
                contributed=contributed,
                prs_merged=prs_merged,
                prs_merged_pct=prs_merged_pct,
            )

        except requests.RequestException as e:
            log.error(f"Network error fetching GitHub stats: {e}")
            return None
        except (KeyError, ValueError) as e:
            log.error(f"Unexpected API response format: {e}")
            return None

    @staticmethod
    def _paginate_repos(session: requests.Session, repos_url: str) -> Iterator[dict]:
        """Yield all repos, handling GitHub API pagination with rate limit awareness."""
        page = 1
        max_pages = 10  # Safety limit

        while page <= max_pages:
            response = session.get(
                repos_url,
                params={"page": page, "per_page": 100},
                timeout=REQUEST_TIMEOUT,
            )

            if response.status_code == 403:
                log.warning("GitHub rate limit hit, stopping pagination")
                break

            if not response.ok:
                break

            repos = response.json()
            if not repos:
                break

            yield from repos
            page += 1

    @staticmethod
    def _fetch_stats_svg(
        session: requests.Session, username: str, params: str
    ) -> ElementTree.Element | None:
        """Fetch and parse GitHub readme stats SVG."""
        url = f"{GITHUB_STATS_API}?username={username}&{params}"
        response = session.get(url, timeout=REQUEST_TIMEOUT)

        if not response.ok:
            return None

        try:
            return ElementTree.fromstring(response.content)
        except ElementTree.ParseError:
            return None

    @staticmethod
    def _extract_stat(svg: ElementTree.Element, testid: str) -> str | None:
        """Extract stat value from SVG by data-testid attribute."""
        ns = {"svg": "http://www.w3.org/2000/svg"}
        elem = svg.find(f'.//svg:text[@data-testid="{testid}"]', ns)
        return elem.text if elem is not None and elem.text else None


# === SVG Updater ===


class SVGUpdater:
    """Efficient SVG content updater using regex patterns."""

    # Pre-compiled regex patterns for each stat field
    PATTERNS: dict[str, re.Pattern[str]] = {
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
        self._original_hash: int | None = None

    @cached_property
    def content(self) -> str:
        """Lazy-load file content."""
        return self.filepath.read_text(encoding="utf-8")

    def update(self, pattern_key: str, value: str) -> bool:
        """
        Replace a pattern match with a new value.
        Returns True if pattern was found and updated.
        """
        if self._content is None:
            self._content = self.content
            self._original_hash = hash(self._content)

        pattern = self.PATTERNS.get(pattern_key)
        if pattern is None:
            log.warning(f"Unknown pattern key: {pattern_key}")
            return False

        new_content, count = pattern.subn(rf"\g<1>{value}\g<2>", self._content)

        if count == 0:
            log.warning(f"Pattern '{pattern_key}' not found in {self.filepath.name}")
            return False

        self._content = new_content
        return True

    def save(self) -> bool:
        """
        Write updated content back to file if changed.
        Returns True if file was modified.
        """
        if self._content is None:
            return False

        # Only write if content actually changed
        if hash(self._content) == self._original_hash:
            log.info(f"No changes to {self.filepath.name}")
            return False

        try:
            self.filepath.write_text(self._content, encoding="utf-8")
            return True
        except OSError as e:
            log.error(f"Failed to write {self.filepath.name}: {e}")
            return False


# === Main Execution ===


def update_all_svgs(uptime: UptimeStats, github: GitHubStats | None) -> int:
    """
    Apply all updates to SVG files.
    Returns number of files successfully updated.
    """
    base_path = Path(__file__).parent
    updated_count = 0

    for svg_file in SVG_FILES:
        filepath = base_path / svg_file

        if not filepath.exists():
            log.warning(f"SVG file not found: {svg_file}")
            continue

        updater = SVGUpdater(filepath)

        # Uptime stats (always available)
        updater.update("uptime", uptime.formatted_uptime)
        updater.update("total_days", f"({uptime.total_days}d)")
        updater.update("life_pct", f"({uptime.life_percentage}%)")

        # GitHub stats (may be None if API failed)
        if github is not None:
            updater.update("repos", str(github.repos))
            updater.update("followers", str(github.followers))
            updater.update("stars", str(github.stars))
            updater.update("contributed", github.contributed)
            updater.update("commits", github.commits)
            updater.update("prs_merged", f"{github.prs_merged} ({github.prs_merged_pct})")

        if updater.save():
            log.info(f"✓ Updated {svg_file}")
            updated_count += 1

    return updated_count


def main() -> int:
    """
    Entry point: fetch stats and update SVGs.
    Returns exit code (0 = success, 1 = partial failure, 2 = total failure).
    """
    log.info("🔄 Starting daily update...")

    # Uptime calculation (never fails)
    uptime = UptimeStats.from_birthdate(BIRTH_DATE)
    log.info(f"Uptime: {uptime.formatted_uptime} ({uptime.life_percentage}%)")

    # GitHub stats (may fail gracefully)
    github = GitHubStats.fetch(GITHUB_USERNAME)
    if github is None:
        log.warning("⚠️  GitHub stats unavailable, updating uptime only")
    else:
        log.info(
            f"GitHub: {github.repos} repos | {github.stars} stars | {github.commits} commits"
        )

    # Update SVGs
    updated = update_all_svgs(uptime, github)

    if updated == len(SVG_FILES):
        log.info("✅ All files updated successfully!")
        return 0
    elif updated > 0:
        log.warning(f"⚠️  Partial update: {updated}/{len(SVG_FILES)} files")
        return 1
    else:
        log.error("❌ No files were updated")
        return 2


if __name__ == "__main__":
    sys.exit(main())
