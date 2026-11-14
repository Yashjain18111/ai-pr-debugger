from unittest.mock import patch
from app.cli import main, render_markdown
from app.models import BugFinding, Category, ReviewReport, ReviewSummary, Severity


def test_render_markdown_generates_pr_comment():
    report = ReviewReport(
        summary="Audit summary.",
        findings=[
            BugFinding(
                bug="Sample bug description.",
                impact="High impact on latency.",
                fix="Optimized lookup.",
                regression_test="def test_fix(): pass",
                severity=Severity.HIGH,
                category=Category.PERFORMANCE,
                file_path="service/handler.py",
                line_number=42,
            )
        ],
        review_summary=ReviewSummary(
            verdict="REQUEST_CHANGES",
            total_findings=1,
            critical_count=0,
            high_count=1,
            overview="Audit summary.",
        ),
    )

    markdown = render_markdown(report)
    assert "AI PR Debugger Report" in markdown
    assert "REQUEST CHANGES" in markdown
    assert "service/handler.py" in markdown
    assert "High impact on latency" in markdown


def test_cli_review_mock_command(capsys):
    with patch("sys.argv", ["ai-pr-debugger", "review", "examples/buggy_code.py", "--mock"]):
        main()
    captured = capsys.readouterr()
    assert "AI PR DEBUGGER - AUTOMATED CODE AUDIT REPORT" in captured.out
    assert "REQUEST_CHANGES" in captured.out

