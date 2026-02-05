#!/usr/bin/env python3
"""Daily GitHub Profile README updater.

Updates SVG profile cards with live stats from GitHub API and uptime calculations.

This module follows Google Python Style Guide conventions:
https://google.github.io/styleguide/pyguide.html

Example:
    $ python daily.py
    2026-02-04 21:00:00 | INFO     | ✓ Updated dark_mode.svg

Attributes:
    DEFAULT_CONFIG: Default configuration for the updater.
"""

from __future__ import annotations

import abc
import logging
import re
import sys
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import TYPE_CHECKING, Final, Protocol, Self
from xml.etree import ElementTree

import requests
from dateutil.relativedelta import relativedelta
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

if TYPE_CHECKING:
    from collections.abc import Iterator, Mapping


# ============================================================================
# Logging Configuration
# ============================================================================

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
_logger: Final = logging.getLogger(__name__)


# ============================================================================
# Exceptions
# ============================================================================


class UpdaterError(Exception):
    """Base exception for all updater errors."""


class GitHubAPIError(UpdaterError):
    """Raised when GitHub API requests fail."""

    def __init__(self, message: str, status_code: int | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code


class SVGParseError(UpdaterError):
    """Raised when SVG parsing or updating fails."""


# ============================================================================
# Configuration
# ============================================================================


@dataclass(frozen=True, slots=True)
class Config:
    """Immutable configuration for the profile updater.

    Attributes:
        github_username: GitHub username to fetch stats for.
        birth_date: Date of birth for uptime calculation.
        life_expectancy_days: Expected lifespan in days for percentage calc.
        svg_files: Tuple of SVG filenames to update.
        base_path: Base directory containing SVG files.
        request_timeout: HTTP request timeout in seconds.
        max_retries: Maximum number of retry attempts for failed requests.
        retry_backoff: Backoff factor between retries.
    """

    github_username: str
    birth_date: date
    life_expectancy_days: int = 27485
    svg_files: tuple[str, ...] = ("dark_mode.svg", "light_mode.svg")
    base_path: Path = field(default_factory=lambda: Path(__file__).parent)
    request_timeout: int = 30
    max_retries: int = 3
    retry_backoff: float = 1.0


# Default configuration
DEFAULT_CONFIG: Final = Config(
    github_username="pyoneerc",
    birth_date=date(2005, 3, 3),
)


# ============================================================================
# Protocols (Interfaces)
# ============================================================================


class HTTPClient(Protocol):
    """Protocol for HTTP client abstraction (enables testing with mocks)."""

    def get(
        self,
        url: str,
        *,
        params: Mapping[str, str] | None = None,
        timeout: int = 30,
    ) -> requests.Response:
        """Perform an HTTP GET request."""
        ...


class StatsProvider(Protocol):
    """Protocol for stats data providers."""

    def fetch(self) -> Mapping[str, str | int]:
        """Fetch stats as a dictionary."""
        ...


# ============================================================================
# HTTP Client Implementation
# ============================================================================


class ResilientHTTPClient:
    """HTTP client with automatic retries and connection pooling.

    This client implements exponential backoff for transient failures and
    handles rate limiting gracefully.

    Attributes:
        session: The underlying requests session.
        timeout: Default timeout for requests.
    """

    def __init__(
        self,
        timeout: int = 30,
        max_retries: int = 3,
        backoff_factor: float = 1.0,
    ) -> None:
        """Initialize the HTTP client.

        Args:
            timeout: Default request timeout in seconds.
            max_retries: Maximum retry attempts for failed requests.
            backoff_factor: Multiplier for exponential backoff between retries.
        """
        self.timeout = timeout
        self._session = self._create_session(max_retries, backoff_factor)

    def _create_session(
        self,
        max_retries: int,
        backoff_factor: float,
    ) -> requests.Session:
        """Create a configured requests session with retry logic."""
        session = requests.Session()

        retry_strategy = Retry(
            total=max_retries,
            backoff_factor=backoff_factor,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["GET"],
            raise_on_status=False,
        )

        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("https://", adapter)
        session.mount("http://", adapter)

        return session

    def get(
        self,
        url: str,
        *,
        params: Mapping[str, str] | None = None,
        timeout: int | None = None,
    ) -> requests.Response:
        """Perform an HTTP GET request.

        Args:
            url: The URL to request.
            params: Optional query parameters.
            timeout: Request timeout (uses default if not specified).

        Returns:
            The HTTP response object.

        Raises:
            GitHubAPIError: If the request fails after all retries.
        """
        try:
            return self._session.get(
                url,
                params=dict(params) if params else None,
                timeout=timeout or self.timeout,
            )
        except requests.RequestException as e:
            raise GitHubAPIError(f"Request failed: {e}") from e

    def close(self) -> None:
        """Close the underlying session."""
        self._session.close()

    def __enter__(self) -> Self:
        return self

    def __exit__(self, *_: object) -> None:
        self.close()


# ============================================================================
# Data Models
# ============================================================================


@dataclass(frozen=True, slots=True)
class UptimeStats:
    """Immutable container for uptime calculations.

    Attributes:
        years: Number of complete years.
        months: Number of complete months (0-11).
        days: Number of days in current month.
        total_days: Total days since birth.
        life_percentage: Percentage of expected lifespan elapsed.
    """

    years: int
    months: int
    days: int
    total_days: int
    life_percentage: float

    @classmethod
    def from_birthdate(
        cls,
        birthdate: date,
        life_expectancy_days: int,
    ) -> UptimeStats:
        """Calculate uptime stats from a birthdate.

        Args:
            birthdate: The date of birth.
            life_expectancy_days: Expected lifespan in days.

        Returns:
            UptimeStats instance with calculated values.
        """
        today = date.today()
        delta = relativedelta(today, birthdate)
        total_days = (today - birthdate).days

        return cls(
            years=delta.years,
            months=delta.months,
            days=delta.days,
            total_days=total_days,
            life_percentage=round((total_days / life_expectancy_days) * 100, 2),
        )

    @property
    def formatted(self) -> str:
        """Format uptime as human-readable string with proper pluralization."""
        month_word = "month" if self.months == 1 else "months"
        day_word = "day" if self.days == 1 else "days"
        return f"{self.years} years, {self.months} {month_word}, {self.days} {day_word}"


@dataclass(frozen=True, slots=True)
class GitHubStats:
    """Immutable container for GitHub statistics.

    Attributes:
        repos: Number of public repositories.
        followers: Number of followers.
        stars: Total stars across all repositories.
        commits: Total commit count (as string, may include 'k' suffix).
        contributed: Number of repos contributed to.
        prs_merged: Number of merged pull requests.
        prs_merged_pct: Percentage of PRs that were merged.
    """

    repos: int
    followers: int
    stars: int
    commits: str
    contributed: str
    prs_merged: str
    prs_merged_pct: str

    @classmethod
    def default(cls) -> GitHubStats:
        """Return a GitHubStats instance with placeholder values."""
        return cls(
            repos=0,
            followers=0,
            stars=0,
            commits="?",
            contributed="?",
            prs_merged="?",
            prs_merged_pct="?%",
        )


# ============================================================================
# GitHub Stats Fetcher
# ============================================================================


class GitHubStatsFetcher:
    """Fetches GitHub statistics from the API.

    This class encapsulates all GitHub API interactions and provides
    graceful degradation when individual endpoints fail.

    Attributes:
        username: The GitHub username to fetch stats for.
        client: The HTTP client to use for requests.
    """

    _GITHUB_API: Final = "https://api.github.com/users"
    _STATS_API: Final = "https://github-readme-stats.vercel.app/api"
    _SVG_NAMESPACE: Final = {"svg": "http://www.w3.org/2000/svg"}
    _MAX_REPO_PAGES: Final = 10

    def __init__(self, username: str, client: HTTPClient) -> None:
        """Initialize the fetcher.

        Args:
            username: GitHub username to fetch stats for.
            client: HTTP client for making requests.
        """
        self.username = username
        self._client = client

    def fetch(self) -> GitHubStats:
        """Fetch all GitHub statistics.

        Returns:
            GitHubStats instance with fetched data.
            Falls back to defaults for any data that couldn't be fetched.
        """
        # Fetch user profile (critical data)
        user_data = self._fetch_user_profile()
        if user_data is None:
            _logger.warning("Failed to fetch user profile, using defaults")
            return GitHubStats.default()

        # Fetch additional stats (non-critical, fallback gracefully)
        stars = self._calculate_total_stars(user_data.get("repos_url", ""))
        commits, contributed = self._fetch_commit_stats()
        prs_merged, prs_merged_pct = self._fetch_pr_stats()

        return GitHubStats(
            repos=user_data.get("public_repos", 0),
            followers=user_data.get("followers", 0),
            stars=stars,
            commits=commits,
            contributed=contributed,
            prs_merged=prs_merged,
            prs_merged_pct=prs_merged_pct,
        )

    def _fetch_user_profile(self) -> dict | None:
        """Fetch user profile from GitHub API."""
        url = f"{self._GITHUB_API}/{self.username}"
        try:
            response = self._client.get(url)
            if response.ok:
                return response.json()
            _logger.error(f"GitHub API returned {response.status_code}")
        except GitHubAPIError as e:
            _logger.error(f"Failed to fetch profile: {e}")
        return None

    def _calculate_total_stars(self, repos_url: str) -> int:
        """Calculate total stars across all repositories."""
        if not repos_url:
            return 0

        total = 0
        try:
            for repo in self._paginate_repos(repos_url):
                total += repo.get("stargazers_count", 0)
        except GitHubAPIError as e:
            _logger.warning(f"Failed to fetch all repos: {e}")
        return total

    def _paginate_repos(self, repos_url: str) -> Iterator[dict]:
        """Yield all repositories, handling pagination."""
        for page in range(1, self._MAX_REPO_PAGES + 1):
            response = self._client.get(
                repos_url,
                params={"page": str(page), "per_page": "100"},
            )

            if response.status_code == 403:
                _logger.warning("Rate limited during pagination")
                break

            if not response.ok:
                break

            repos = response.json()
            if not repos:
                break

            yield from repos

    def _fetch_commit_stats(self) -> tuple[str, str]:
        """Fetch commit and contribution stats."""
        url = f"{self._STATS_API}?username={self.username}&include_all_commits=true"
        try:
            response = self._client.get(url)
            if response.ok:
                svg = ElementTree.fromstring(response.content)
                commits = self._extract_svg_stat(svg, "commits") or "?"
                contributed = self._extract_svg_stat(svg, "contribs") or "?"
                return commits, contributed
        except (GitHubAPIError, ElementTree.ParseError) as e:
            _logger.warning(f"Failed to parse commit stats: {e}")
        return "?", "?"

    def _fetch_pr_stats(self) -> tuple[str, str]:
        """Fetch pull request statistics."""
        url = f"{self._STATS_API}?username={self.username}&show=prs_merged,prs_merged_percentage"
        try:
            response = self._client.get(url)
            if response.ok:
                svg = ElementTree.fromstring(response.content)
                merged = self._extract_svg_stat(svg, "prs_merged") or "?"
                pct_raw = self._extract_svg_stat(svg, "prs_merged_percentage") or "0"
                pct = pct_raw[:2].strip() + "%"
                return merged, pct
        except (GitHubAPIError, ElementTree.ParseError) as e:
            _logger.warning(f"Failed to parse PR stats: {e}")
        return "?", "?%"

    def _extract_svg_stat(self, svg: ElementTree.Element, testid: str) -> str | None:
        """Extract a stat value from SVG by data-testid attribute."""
        elem = svg.find(f'.//svg:text[@data-testid="{testid}"]', self._SVG_NAMESPACE)
        return elem.text if elem is not None and elem.text else None


# ============================================================================
# SVG Updater
# ============================================================================


class SVGUpdater:
    """Updates SVG files with new stat values using regex patterns.

    This class provides efficient, single-pass updates to SVG content
    with change detection to avoid unnecessary disk writes.

    Attributes:
        filepath: Path to the SVG file.
    """

    _PATTERNS: Final[dict[str, re.Pattern[str]]] = {
        "uptime": re.compile(
            r'(<tspan x="370" y="90" class="keyColor">Uptime</tspan>: '
            r'<tspan class="valueColor">)[^<]*(</tspan>)'
        ),
        "total_days": re.compile(
            r'(<tspan x="680" y= "90" class="valueColor">)[^<]*(</tspan>)'
        ),
        "life_pct": re.compile(
            r'(<tspan x="760" y= "90" class="valueColor">)[^<]*(</tspan>)'
        ),
        "repos": re.compile(
            r'(<tspan x="370" y="490" class="keyColor">Repos</tspan>: '
            r'<tspan class="valueColor">)[^<]*(</tspan>)'
        ),
        "followers": re.compile(
            r'(<tspan x="370" y="510" class="keyColor">Followers</tspan>: '
            r'<tspan class="valueColor">)[^<]*(</tspan>)'
        ),
        "stars": re.compile(
            r'(<tspan x="520" y="510" class="keyColor">\|   Stars</tspan>: '
            r'<tspan class="valueColor">)[^<]*(</tspan>)'
        ),
        "contributed": re.compile(
            r'(<tspan x="480" y="490" class="keyColor">Contributed</tspan>: '
            r'<tspan class="valueColor">)[^<]*(</tspan>)'
        ),
        "commits": re.compile(
            r'(<tspan x="660" y="510" class="keyColor">\|   Commits</tspan>: '
            r'<tspan class="valueColor">)[^<]*(</tspan>)'
        ),
        "prs_merged": re.compile(
            r'(<tspan x="660" y="490" class="keyColor">\|   Merged PRs</tspan>: '
            r'<tspan class="valueColor">)[^<]*(</tspan>)'
        ),
    }

    def __init__(self, filepath: Path) -> None:
        """Initialize the updater.

        Args:
            filepath: Path to the SVG file to update.

        Raises:
            SVGParseError: If the file cannot be read.
        """
        self.filepath = filepath
        self._original_content: str = ""
        self._content: str = ""
        self._load()

    def _load(self) -> None:
        """Load the SVG file content."""
        try:
            self._original_content = self.filepath.read_text(encoding="utf-8")
            self._content = self._original_content
        except OSError as e:
            raise SVGParseError(f"Failed to read {self.filepath}: {e}") from e

    def update(self, key: str, value: str) -> bool:
        """Update a stat value in the SVG content.

        Args:
            key: The stat key (must be in _PATTERNS).
            value: The new value to set.

        Returns:
            True if the pattern was found and updated, False otherwise.
        """
        pattern = self._PATTERNS.get(key)
        if pattern is None:
            _logger.warning(f"Unknown pattern key: {key}")
            return False

        new_content, count = pattern.subn(rf"\g<1>{value}\g<2>", self._content)

        if count == 0:
            _logger.warning(f"Pattern '{key}' not found in {self.filepath.name}")
            return False

        self._content = new_content
        return True

    def save(self) -> bool:
        """Write updated content to file if changed.

        Returns:
            True if file was written, False if unchanged or on error.
        """
        if self._content == self._original_content:
            _logger.debug(f"No changes to {self.filepath.name}")
            return False

        try:
            self.filepath.write_text(self._content, encoding="utf-8")
            return True
        except OSError as e:
            _logger.error(f"Failed to write {self.filepath.name}: {e}")
            return False

    @property
    def has_changes(self) -> bool:
        """Check if content has been modified."""
        return self._content != self._original_content


# ============================================================================
# Profile Updater (Main Orchestrator)
# ============================================================================


class ProfileUpdater:
    """Orchestrates the profile update process.

    This is the main entry point that coordinates fetching stats
    and updating SVG files.

    Attributes:
        config: Configuration for the updater.
    """

    def __init__(self, config: Config | None = None) -> None:
        """Initialize the updater.

        Args:
            config: Configuration to use. Defaults to DEFAULT_CONFIG.
        """
        self.config = config or DEFAULT_CONFIG

    def run(self) -> int:
        """Execute the full update process.

        Returns:
            Exit code: 0 = success, 1 = partial failure, 2 = total failure.
        """
        _logger.info("🔄 Starting daily update...")

        # Calculate uptime (never fails)
        uptime = UptimeStats.from_birthdate(
            self.config.birth_date,
            self.config.life_expectancy_days,
        )
        _logger.info(f"Uptime: {uptime.formatted} ({uptime.life_percentage}%)")

        # Fetch GitHub stats
        with ResilientHTTPClient(
            timeout=self.config.request_timeout,
            max_retries=self.config.max_retries,
            backoff_factor=self.config.retry_backoff,
        ) as client:
            fetcher = GitHubStatsFetcher(self.config.github_username, client)
            github = fetcher.fetch()

        _logger.info(
            f"GitHub: {github.repos} repos | {github.stars} stars | "
            f"{github.commits} commits"
        )

        # Update SVG files
        updated = self._update_svg_files(uptime, github)

        # Return appropriate exit code
        total = len(self.config.svg_files)
        if updated == total:
            _logger.info("✅ All files updated successfully!")
            return 0
        elif updated > 0:
            _logger.warning(f"⚠️  Partial update: {updated}/{total} files")
            return 1
        else:
            _logger.error("❌ No files were updated")
            return 2

    def _update_svg_files(self, uptime: UptimeStats, github: GitHubStats) -> int:
        """Update all SVG files with new stats.

        Args:
            uptime: Calculated uptime statistics.
            github: Fetched GitHub statistics.

        Returns:
            Number of files successfully updated.
        """
        updated_count = 0

        for svg_file in self.config.svg_files:
            filepath = self.config.base_path / svg_file

            if not filepath.exists():
                _logger.warning(f"SVG file not found: {svg_file}")
                continue

            try:
                updater = SVGUpdater(filepath)

                # Uptime stats
                updater.update("uptime", uptime.formatted)
                updater.update("total_days", f"({uptime.total_days}d)")
                updater.update("life_pct", f"({uptime.life_percentage}%)")

                # GitHub stats
                updater.update("repos", str(github.repos))
                updater.update("followers", str(github.followers))
                updater.update("stars", str(github.stars))
                updater.update("contributed", github.contributed)
                updater.update("commits", github.commits)
                updater.update(
                    "prs_merged",
                    f"{github.prs_merged} ({github.prs_merged_pct})",
                )

                if updater.save():
                    _logger.info(f"✓ Updated {svg_file}")
                    updated_count += 1

            except SVGParseError as e:
                _logger.error(f"Failed to process {svg_file}: {e}")

        return updated_count


# ============================================================================
# Entry Point
# ============================================================================


def main() -> int:
    """Main entry point.

    Returns:
        Exit code for the process.
    """
    updater = ProfileUpdater()
    return updater.run()


if __name__ == "__main__":
    sys.exit(main())
