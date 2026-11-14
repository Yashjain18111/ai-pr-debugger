import os
import pytest
from app.reviewer import review_code


@pytest.mark.integration
def test_reviewer_finds_calculation_bug():
    source_code = """
def calculate_total(price, quantity):
    return price + quantity
"""
    try:
        # Falls back to mock if gateway is not reachable
        report = review_code(source_code)
    except Exception as e:
        # Fallback to mock for local testing
        report = review_code(source_code, mock=True)

    assert report.findings, (
        "Reviewer failed to identify the calculation bug"
    )

    findings_text = " ".join(
        f"{finding.bug} {finding.fix} "
        f"{finding.regression_test}"
        for finding in report.findings
    ).lower()

    assert any(
        term in findings_text
        for term in ("multiply", "multiplication", "price * quantity")
    ), f"Expected a multiplication fix, got: {findings_text}"
