"""
GitHub Pull Request fetcher
Fetches PR metadata and diff content from GitHub API
"""
import re
import requests
from typing import Dict, Optional


class PRFetcher:
    """Fetch PR information from GitHub"""

    def __init__(self, github_token: Optional[str] = None):
        """
        Initialize PR fetcher

        Args:
            github_token: Optional GitHub personal access token for private repos
        """
        self.github_token = github_token
        self.headers = {}
        if github_token:
            self.headers['Authorization'] = f'token {github_token}'

    def parse_pr_url(self, pr_url: str) -> Dict[str, str]:
        """
        Parse GitHub PR URL to extract owner, repo, and PR number

        Args:
            pr_url: GitHub PR URL (e.g., https://github.com/owner/repo/pull/123)

        Returns:
            Dict with 'owner', 'repo', 'pr_number'
        """
        pattern = r'github\.com/([^/]+)/([^/]+)/pull/(\d+)'
        match = re.search(pattern, pr_url)

        if not match:
            raise ValueError(f"Invalid GitHub PR URL: {pr_url}")

        return {
            'owner': match.group(1),
            'repo': match.group(2),
            'pr_number': match.group(3)
        }

    def fetch_pr_metadata(self, pr_url: str) -> Dict:
        """
        Fetch PR metadata from GitHub API

        Args:
            pr_url: GitHub PR URL

        Returns:
            PR metadata dict
        """
        parsed = self.parse_pr_url(pr_url)
        api_url = f"https://api.github.com/repos/{parsed['owner']}/{parsed['repo']}/pulls/{parsed['pr_number']}"

        response = requests.get(api_url, headers=self.headers)
        response.raise_for_status()

        return response.json()

    def fetch_pr_diff(self, pr_url: str) -> str:
        """
        Fetch PR diff content

        Args:
            pr_url: GitHub PR URL

        Returns:
            Raw diff content as string
        """
        parsed = self.parse_pr_url(pr_url)
        diff_url = f"https://patch-diff.githubusercontent.com/raw/{parsed['owner']}/{parsed['repo']}/pull/{parsed['pr_number']}.diff"

        response = requests.get(diff_url, headers=self.headers)
        response.raise_for_status()

        return response.text

    def fetch_pr_files(self, pr_url: str) -> list:
        """
        Fetch list of files changed in PR

        Args:
            pr_url: GitHub PR URL

        Returns:
            List of file change objects
        """
        parsed = self.parse_pr_url(pr_url)
        api_url = f"https://api.github.com/repos/{parsed['owner']}/{parsed['repo']}/pulls/{parsed['pr_number']}/files"

        response = requests.get(api_url, headers=self.headers)
        response.raise_for_status()

        return response.json()
