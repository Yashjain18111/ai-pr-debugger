"""
GitHub integration utilities for AI PR Debugger.
Fetches Pull Request diffs from GitHub and posts automated reviews via GitHub REST API.
"""

import os
import re
from typing import Optional, Tuple
import requests

from app.models import ReviewReport


def parse_github_pr_url(url: str) -> Optional[Tuple[str, str, int]]:
    """Extract (owner, repo, pr_number) from a GitHub PR URL or string."""
    pattern = r"github\.com/([^/]+)/([^/]+)/pull/(\d+)"
    match = re.search(pattern, url)
    if match:
        owner, repo, pr_num = match.group(1), match.group(2), int(match.group(3))
        return owner, repo, pr_num

    slug_pattern = r"^([^/]+)/([^#]+)#(\d+)$"
    match_slug = re.match(slug_pattern, url.strip())
    if match_slug:
        return match_slug.group(1), match_slug.group(2), int(match_slug.group(3))

    return None


def fetch_pr_diff(
    pr_url: str,
    github_token: Optional[str] = None
) -> str:
    """Fetch the raw unified diff of a GitHub Pull Request."""
    parsed = parse_github_pr_url(pr_url)
    if not parsed:
        raise ValueError(
            f"Invalid GitHub PR reference: '{pr_url}'. Expected format: https://github.com/owner/repo/pull/123 or owner/repo#123"
        )

    owner, repo, pr_number = parsed
    api_url = f"https://api.github.com/repos/{owner}/{repo}/pulls/{pr_number}"

    headers = {
        "Accept": "application/vnd.github.v3.diff",
        "User-Agent": "AI-PR-Debugger",
    }
    token = github_token or os.getenv("GITHUB_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"

    response = requests.get(api_url, headers=headers, timeout=15)
    if response.status_code == 404:
        raise RuntimeError(f"Pull request not found or repository is private: {pr_url}")
    if response.status_code != 200:
        raise RuntimeError(
            f"Failed to fetch PR diff ({response.status_code}): {response.text}"
        )

    return response.text


def post_github_review(
    owner: str,
    repo: str,
    pr_number: int,
    markdown_body: str,
    verdict: str = "COMMENT",
    github_token: Optional[str] = None,
) -> dict:
    """Submit a formal Pull Request Review on GitHub."""
    token = github_token or os.getenv("GITHUB_TOKEN")
    if not token:
        raise ValueError("GITHUB_TOKEN environment variable is required to post a review.")

    url = f"https://api.github.com/repos/{owner}/{repo}/pulls/{pr_number}/reviews"
    headers = {
        "Accept": "application/vnd.github.v3+json",
        "Authorization": f"Bearer {token}",
        "User-Agent": "AI-PR-Debugger",
    }

    # GitHub review events: APPROVE, REQUEST_CHANGES, COMMENT
    event_map = {
        "APPROVE": "APPROVE",
        "REQUEST_CHANGES": "REQUEST_CHANGES",
        "COMMENT": "COMMENT",
    }
    event = event_map.get(verdict.upper(), "COMMENT")

    payload = {
        "body": markdown_body,
        "event": event,
    }

    response = requests.post(url, json=payload, headers=headers, timeout=15)
    if response.status_code not in (200, 201):
        raise RuntimeError(
            f"Failed to post PR review ({response.status_code}): {response.text}"
        )

    return response.json()

