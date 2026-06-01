"""
GitHub Checker - Repository Analysis
=====================================
Verifies whether a token has a GitHub repository,
checks repository activity, stars, forks, and
evaluates code legitimacy signals.
"""
import asyncio
import logging
from typing import Dict, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime, timedelta

import aiohttp

logger = logging.getLogger(__name__)

# GitHub API
GITHUB_API_URL = "https://api.github.com"
GITHUB_RAW_URL = "https://raw.githubusercontent.com"


@dataclass
class GitHubResult:
    """Result of a GitHub repository analysis."""

    token_address: str
    token_name: str = ""
    token_symbol: str = ""
    repo_url: str = ""
    repo_name: str = ""
    repo_owner: str = ""
    repo_description: str = ""
    stars: int = 0
    forks: int = 0
    watchers: int = 0
    open_issues: int = 0
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    pushed_at: Optional[datetime] = None
    has_readme: bool = False
    has_license: bool = False
    has_contributing: bool = False
    language: str = ""
    topics: list = field(default_factory=list)
    is_fork: bool = False
    is_template: bool = False
    is_archived: bool = False
    days_since_last_update: int = 999
    is_active: bool = False
    is_legitimate: bool = False
    score: int = 0  # 0-100 repository quality score
    risk_warning: str = ""

    def __post_init__(self):
        if self.is_archived:
            self.risk_warning = "⚠ Repository is archived – development has stopped."
        if self.score >= 50:
            self.is_legitimate = True
    raw_data: Dict[str, Any] = field(default_factory=dict)
    success: bool = False
    found_repo: bool = False
    error_message: str = ""

    @property
    def status_text(self) -> str:
        if not self.found_repo:
            return "🔴 No GitHub repository found"
        if self.score >= 70:
            return "🟢 Active & legitimate repository"
        elif self.score >= 40:
            return "🟡 Basic repository (needs verification)"
        else:
            return "🔴 Suspicious or inactive repository"

    @property
    def status_color(self) -> str:
        if not self.found_repo:
            return "#9ca3af"
        if self.score >= 70:
            return "#22c55e"
        elif self.score >= 40:
            return "#f59e0b"
        return "#ef4444"

    def to_dict(self) -> Dict:
        return {
            "token_address": self.token_address,
            "token_name": self.token_name,
            "token_symbol": self.token_symbol,
            "repo_url": self.repo_url,
            "repo_name": self.repo_name,
            "repo_owner": self.repo_owner,
            "stars": self.stars,
            "forks": self.forks,
            "open_issues": self.open_issues,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "has_readme": self.has_readme,
            "has_license": self.has_license,
            "language": self.language,
            "is_active": self.is_active,
            "is_legitimate": self.is_legitimate,
            "score": self.score,
            "risk_warning": self.risk_warning,
            "found_repo": self.found_repo,
            "status_text": self.status_text,
            "success": self.success,
        }


class GitHubChecker:
    """Checks token GitHub repositories for legitimacy signals."""

    def __init__(self, github_token: str = "", timeout: int = 30):
        self.github_token = github_token
        self.timeout = timeout
        self.session: Optional[aiohttp.ClientSession] = None

    async def _get_session(self) -> aiohttp.ClientSession:
        if self.session is None or self.session.closed:
            headers = {
                "User-Agent": "BaseBot/1.0 GitHubChecker",
                "Accept": "application/vnd.github.v3+json",
            }
            if self.github_token:
                headers["Authorization"] = f"Bearer {self.github_token}"
            self.session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=self.timeout),
                headers=headers,
            )
        return self.session

    async def close(self):
        if self.session and not self.session.closed:
            await self.session.close()

    async def check(self, token_address: str, token_name: str = "", token_symbol: str = "",
                    github_url: str = "") -> GitHubResult:
        """
        Analyze the GitHub repository for a token.
        Accepts a direct GitHub URL or tries to search.
        """
        result = GitHubResult(
            token_address=token_address,
            token_name=token_name,
            token_symbol=token_symbol,
            repo_url=github_url,
        )

        if not github_url or "github.com" not in github_url.lower():
            # Try to find repo by token name/symbol
            found_url = await self._search_repo(token_name, token_symbol)
            if found_url:
                github_url = found_url
                result.repo_url = found_url
            else:
                result.error_message = "No GitHub URL provided or found"
                result.found_repo = False
                return result

        result.found_repo = True

        # Parse owner/repo from URL
        owner, repo = self._parse_repo_url(github_url)
        if not owner or not repo:
            result.error_message = f"Invalid GitHub URL: {github_url}"
            return result

        result.repo_owner = owner
        result.repo_name = repo

        # Fetch repo data
        session = await self._get_session()
        repo_data = await self._fetch_repo(session, owner, repo)
        if not repo_data:
            result.error_message = f"Repository {owner}/{repo} not found"
            result.found_repo = False
            return result

        result.raw_data = repo_data
        self._parse_repo_data(result, repo_data)

        # Check for README, LICENSE, CONTRIBUTING
        await self._check_files(session, result)

        # Calculate score
        self._calculate_score(result)

        result.success = True
        logger.info(
            f"GitHub check for {token_symbol or token_name}: "
            f"score={result.score}/100, {result.status_text}"
        )

        return result

    async def _search_repo(self, token_name: str, token_symbol: str) -> str:
        """Search GitHub for the token's repository."""
        session = await self._get_session()
        search_query = f"{token_name} {token_symbol} token" if token_name and token_symbol else token_name
        if not search_query.strip():
            return ""

        try:
            params = {"q": search_query, "sort": "stars", "order": "desc", "per_page": 5}
            url = f"{GITHUB_API_URL}/search/repositories"
            async with session.get(url, params=params) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    items = data.get("items", [])
                    if items:
                        return items[0].get("html_url", "")
        except Exception as e:
            logger.debug(f"GitHub search error: {e}")
        return ""

    async def _fetch_repo(self, session: aiohttp.ClientSession, owner: str, repo: str) -> Optional[Dict]:
        """Fetch repository metadata from GitHub API."""
        try:
            url = f"{GITHUB_API_URL}/repos/{owner}/{repo}"
            async with session.get(url) as resp:
                if resp.status == 200:
                    return await resp.json()
                elif resp.status == 403:
                    logger.warning("GitHub API rate limit exceeded")
                elif resp.status == 404:
                    logger.debug(f"Repo {owner}/{repo} not found")
        except Exception as e:
            logger.error(f"Error fetching repo: {e}")
        return None

    def _parse_repo_data(self, result: GitHubResult, data: Dict):
        """Parse repository metadata."""
        result.repo_description = data.get("description", "") or ""
        result.stars = data.get("stargazers_count", 0)
        result.forks = data.get("forks_count", 0)
        result.watchers = data.get("watchers_count", 0)
        result.open_issues = data.get("open_issues_count", 0)
        result.is_fork = data.get("fork", False)
        result.is_template = data.get("is_template", False)
        result.is_archived = data.get("archived", False)
        result.language = data.get("language", "") or ""
        result.topics = data.get("topics", []) or []

        # Parse dates
        for date_field, attr_name in [
            ("created_at", "created_at"),
            ("updated_at", "updated_at"),
            ("pushed_at", "pushed_at"),
        ]:
            date_str = data.get(date_field)
            if date_str:
                try:
                    setattr(result, attr_name, datetime.fromisoformat(date_str.replace("Z", "+00:00")))
                except (ValueError, TypeError):
                    pass

        # Calculate days since last update
        if result.pushed_at:
            result.days_since_last_update = (datetime.now().replace(tzinfo=None) -
                                              result.pushed_at.replace(tzinfo=None)).days
            result.is_active = result.days_since_last_update <= 90

    async def _check_files(self, session: aiohttp.ClientSession, result: GitHubResult):
        """Check for README, LICENSE, CONTRIBUTING files."""
        # README check
        try:
            url = f"{GITHUB_API_URL}/repos/{result.repo_owner}/{result.repo_name}/readme"
            async with session.get(url) as resp:
                result.has_readme = (resp.status == 200)
        except Exception:
            pass

        # License check
        try:
            url = f"{GITHUB_API_URL}/repos/{result.repo_owner}/{result.repo_name}/license"
            async with session.get(url) as resp:
                result.has_license = (resp.status == 200)
        except Exception:
            pass

        # CONTRIBUTING check
        try:
            url = f"{GITHUB_API_URL}/repos/{result.repo_owner}/{result.repo_name}/contents/CONTRIBUTING.md"
            async with session.get(url) as resp:
                result.has_contributing = (resp.status == 200)
        except Exception:
            pass

    def _calculate_score(self, result: GitHubResult):
        """Calculate a repository quality score (0-100)."""
        score = 0
        warnings = []

        # Stars (max 25)
        if result.stars >= 100:
            score += 25
        elif result.stars >= 50:
            score += 20
        elif result.stars >= 10:
            score += 10
        elif result.stars > 0:
            score += 5
        else:
            warnings.append("No stars")

        # Forks (max 10)
        if result.forks >= 20:
            score += 10
        elif result.forks > 0:
            score += 5

        # Has README (15)
        if result.has_readme:
            score += 15
        else:
            warnings.append("No README file")

        # Has license (15)
        if result.has_license:
            score += 15
        else:
            warnings.append("No LICENSE file")

        # Activity (max 20)
        if result.days_since_last_update <= 7:
            score += 20
        elif result.days_since_last_update <= 30:
            score += 15
        elif result.days_since_last_update <= 90:
            score += 8
        else:
            warnings.append(f"No update in {result.days_since_last_update} days")

        # Not a fork (5)
        if not result.is_fork:
            score += 5

        # Not archived (5)
        if not result.is_archived:
            score += 5
        else:
            warnings.append("Repository is archived")

        # Has topics (5)
        if result.topics:
            score += 5

        result.score = score
        result.is_legitimate = score >= 50

        # Build risk warning
        if not result.found_repo:
            result.risk_warning = "🚨 No GitHub repository! Hidden development is a red flag."
        elif result.is_archived:
            result.risk_warning = "⚠ Repository is archived – development has stopped."
        elif not result.has_license:
            result.risk_warning = "⚠ No open-source license – code may be proprietary."
        elif result.score < 30:
            result.risk_warning = "🚨 Very low quality repository – possible scam."

        if warnings:
            result.risk_warning = result.risk_warning or "; ".join(warnings)

    @staticmethod
    def _parse_repo_url(url: str) -> tuple:
        """Extract owner/repo from GitHub URL."""
        url = url.strip().rstrip("/").rstrip(".git")
        # Handle: https://github.com/owner/repo
        parts = url.split("github.com/")
        if len(parts) < 2:
            return "", ""
        path = parts[1].split("/")
        if len(path) >= 2:
            return path[0], path[1]
        return "", ""


class MockGitHubChecker(GitHubChecker):
    """Mock version for testing."""

    async def check(self, token_address: str, token_name: str = "", token_symbol: str = "",
                    github_url: str = "") -> GitHubResult:
        result = GitHubResult(
            token_address=token_address,
            token_name=token_name,
            token_symbol=token_symbol,
            repo_url=github_url or f"https://github.com/{token_name.lower()}/{token_symbol.lower()}",
            repo_name=token_symbol.lower() if token_symbol else "token",
            repo_owner=token_name.lower() if token_name else "dev",
            repo_description="A legitimate DeFi token on Base",
            stars=42,
            forks=12,
            open_issues=3,
            has_readme=True,
            has_license=True,
            language="Solidity",
            topics=["defi", "base", "token"],
            is_active=True,
            is_legitimate=True,
            score=85,
            found_repo=True,
            days_since_last_update=3,
            success=True,
        )
        return result