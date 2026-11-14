
from unittest.mock import MagicMock, patch

from app.reviewer import BugFinding, ReviewReport, review_code


def test_review_code_returns_structured_report():
    expected_report = ReviewReport(
        summary="Found a calculation bug.",
        findings=[
            BugFinding(
                bug="Addition is used instead of multiplication.",
                impact="The total will be incorrect.",
                fix="Return price * quantity.",
                regression_test=(
                    "Assert calculate_total(100, 3) == 300."
                ),
            )
        ],
    )

    with patch("app.reviewer.ChatOpenAI") as mock_chat:
        mock_llm = MagicMock()
        mock_reviewer = MagicMock()

        mock_chat.return_value = mock_llm
        mock_llm.with_structured_output.return_value = mock_reviewer
        mock_reviewer.invoke.return_value = expected_report

        result = review_code(
            "def calculate_total(price, quantity):\n"
            "    return price + quantity"
        )

    assert result == expected_report
    assert len(result.findings) == 1
    assert "multiplication" in result.findings[0].bug.lower()

    mock_llm.with_structured_output.assert_called_once_with(
        ReviewReport
    )
    mock_reviewer.invoke.assert_called_once()
