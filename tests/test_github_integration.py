from unittest.mock import MagicMock, patch
import pytest

from app.github_integration import parse_github_pr_url, fetch_pr_diff, post_github_review


def test_parse_github_pr_url():
    assert parse_github_pr_url("https://github.com/torvalds/linux/pull/123") == ("torvalds", "linux", 123)
    assert parse_github_pr_url("octocat/Hello-World#42") == ("octocat", "Hello-World", 42)
    assert parse_github_pr_url("invalid-url") is None


def test_fetch_pr_diff():
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.text = "diff --git a/test.py b/test.py"

    with patch("requests.get", return_value=mock_response) as mock_get:
        diff = fetch_pr_diff("https://github.com/octocat/Hello-World/pull/1", github_token="fake-token")
        assert "diff --git" in diff
        mock_get.assert_called_once()


def test_post_github_review():
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"id": 12345, "state": "APPROVED"}

    with patch("requests.post", return_value=mock_response) as mock_post:
        res = post_github_review("octocat", "Hello-World", 1, "Looks good!", verdict="APPROVE", github_token="fake-token")
        assert res["state"] == "APPROVED"
        mock_post.assert_called_once()

