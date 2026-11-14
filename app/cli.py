"""
Command-Line Interface (CLI) for AI PR Debugger.
Provides terminal reporting, GitHub-flavored markdown export, JSON output, and git diff review.
"""

import argparse
import json
import os
import sys
from typing import Optional

try:
    from colorama import Fore, Style, init as colorama_init
    colorama_init(autoreset=True)
    HAS_COLORAMA = True
except ImportError:
    HAS_COLORAMA = False

from app.models import ReviewReport, Severity
from app.reviewer import review_code, review_diff, get_llm
from app.diff_parser import get_git_diff
from app.github_integration import parse_github_pr_url, fetch_pr_diff, post_github_review


def _colorize(text: str, color: str, bold: bool = False) -> str:
    if not HAS_COLORAMA:
        return text
    prefix = ""
    if bold:
        prefix += Style.BRIGHT
    if color == "red":
        prefix += Fore.RED
    elif color == "yellow":
        prefix += Fore.YELLOW
    elif color == "green":
        prefix += Fore.GREEN
    elif color == "cyan":
        prefix += Fore.CYAN
    elif color == "magenta":
        prefix += Fore.MAGENTA
    elif color == "blue":
        prefix += Fore.BLUE
    return f"{prefix}{text}{Style.RESET_ALL}"


def render_terminal(report: ReviewReport, min_severity: Optional[Severity] = None) -> None:
    """Print an eye-catching, structured terminal report."""
    severity_order = {
        Severity.CRITICAL: 5,
        Severity.HIGH: 4,
        Severity.MEDIUM: 3,
        Severity.LOW: 2,
        Severity.INFO: 1,
    }
    min_val = severity_order.get(min_severity, 0) if min_severity else 0

    filtered_findings = [
        f for f in report.findings
        if severity_order.get(f.severity, 0) >= min_val
    ]

    print("\n" + "=" * 70)
    print(_colorize("  AI PR DEBUGGER - AUTOMATED CODE AUDIT REPORT", "cyan", bold=True))
    print("=" * 70)

    summary = report.review_summary
    verdict = summary.verdict if summary else ("REQUEST_CHANGES" if report.findings else "APPROVE")
    verdict_color = "red" if verdict == "REQUEST_CHANGES" else ("green" if verdict == "APPROVE" else "yellow")
    print(f" Verdict: {_colorize(f'[{verdict}]', verdict_color, bold=True)}")
    print(f" Summary: {report.summary.strip()}")

    if summary:
        print(
            f" Findings: Total: {summary.total_findings} | "
            f"Critical: {_colorize(str(summary.critical_count), 'red', bold=True)} | "
            f"High: {_colorize(str(summary.high_count), 'yellow', bold=True)}"
        )
    print("-" * 70)

    if not filtered_findings:
        print(_colorize("\n✔ No issues found meeting severity threshold! Looks great.\n", "green", bold=True))
        return

    for idx, finding in enumerate(filtered_findings, start=1):
        sev_color = "red" if finding.severity in (Severity.CRITICAL, Severity.HIGH) else "yellow"
        location = ""
        if finding.file_path:
            location = f" in {finding.file_path}"
            if finding.line_number:
                location += f":L{finding.line_number}"

        print(f"\n{_colorize(f'#{idx} [{finding.severity.value}]', sev_color, bold=True)} "
              f"{_colorize(f'[{finding.category.value}]', 'magenta')} "
              f"{_colorize(finding.bug, 'cyan', bold=True)}{location}")
        
        print(f"  {_colorize('Impact:', 'yellow', bold=True)} {finding.impact}")
        print(f"  {_colorize('Recommended Fix:', 'green', bold=True)}")
        for fix_line in finding.fix.strip().splitlines():
            print(f"    {fix_line}")
        
        print(f"  {_colorize('Regression Test:', 'blue', bold=True)}")
        for test_line in finding.regression_test.strip().splitlines():
            print(f"    {test_line}")

    print("\n" + "=" * 70 + "\n")


def render_markdown(report: ReviewReport) -> str:
    """Format report as GitHub-Flavored Markdown for PR comments."""
    summary = report.review_summary
    verdict = summary.verdict if summary else ("REQUEST_CHANGES" if report.findings else "APPROVE")
    verdict_badge = "🔴 REQUEST CHANGES" if verdict == "REQUEST_CHANGES" else ("🟢 APPROVED" if verdict == "APPROVE" else "🟡 COMMENT")

    lines = [
        f"## 🤖 AI PR Debugger Report",
        f"",
        f"**Verdict:** `{verdict_badge}`",
        f"",
        f"> {report.summary.strip()}",
        f"",
    ]

    if summary:
        lines.append(
            f"| Total Findings | Critical | High | Category Breakdown |",
        )
        lines.append(f"| :---: | :---: | :---: | :---: |")
        lines.append(
            f"| **{summary.total_findings}** | {summary.critical_count} | {summary.high_count} | Automated Scan |"
        )
        lines.append("")

    if not report.findings:
        lines.append("### ✅ No defects identified. Clean PR!")
        return "\n".join(lines)

    lines.append("### 🔍 Detailed Findings")
    lines.append("")

    for idx, f in enumerate(report.findings, start=1):
        loc = f" (`{f.file_path}`)" if f.file_path else ""
        lines.append(f"#### {idx}. [{f.severity.value}] {f.bug}{loc}")
        lines.append(f"- **Category:** `{f.category.value}`")
        lines.append(f"- **Impact:** {f.impact}")
        lines.append(f"- **Recommended Fix:**")
        lines.append(f"```python\n{f.fix.strip()}\n```")
        lines.append(f"- **Regression Test:**")
        lines.append(f"```python\n{f.regression_test.strip()}\n```")
        lines.append("")

    lines.append("---")
    lines.append("*Generated by [AI PR Debugger](https://github.com/your-username/ai-pr-debugger)*")
    return "\n".join(lines)


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="AI PR Debugger - Automated Code Review & Bug Detection"
    )
    subparsers = parser.add_subparsers(dest="command", help="Available subcommands")

    # Command: review
    review_parser = subparsers.add_parser("review", help="Review a file, directory, or diff")
    review_parser.add_argument("target", nargs="?", help="Path to file, diff, script, or GitHub PR URL")
    review_parser.add_argument("--git", action="store_true", help="Review current uncommitted git changes")
    review_parser.add_argument("--staged", action="store_true", help="Review staged git changes")
    review_parser.add_argument("--branch", help="Target branch to compare against (e.g. main)")
    review_parser.add_argument("--format", choices=["terminal", "markdown", "json"], default="terminal", help="Output format")
    review_parser.add_argument("--min-severity", choices=["CRITICAL", "HIGH", "MEDIUM", "LOW", "INFO"], help="Minimum severity to display")
    review_parser.add_argument("--mock", action="store_true", help="Run with mock LLM for offline testing")
    review_parser.add_argument("--model", help="Override LLM model name")
    review_parser.add_argument("--output", help="Save output to file")
    review_parser.add_argument("--post-review", action="store_true", help="Post review comment back to GitHub PR (requires GITHUB_TOKEN)")

    # Command: test-gateway
    subparsers.add_parser("test-gateway", help="Check LLM provider connection")

    args = parser.parse_args(argv)

    if not args.command:
        parser.print_help()
        sys.exit(0)

    if args.command == "test-gateway":
        print("Testing LLM gateway connectivity...")
        try:
            llm = get_llm()
            res = llm.invoke("Reply with exactly: gateway connected")
            print(_colorize(f"✔ Gateway connected successfully: {res.content.strip()}", "green", bold=True))
        except Exception as e:
            print(_colorize(f"✘ Gateway connection failed: {e}", "red", bold=True))
            print("Tip: Use '--mock' flag or update LLM_BASE_URL / OPENAI_API_KEY in .env.")
            sys.exit(1)
        return

    if args.command == "review":
        content = ""
        is_diff = False

        github_pr_info = None

        if args.git or args.staged or args.branch:
            content = get_git_diff(target_branch=args.branch, staged=args.staged)
            is_diff = True
            if not content.strip():
                print(_colorize("No git changes detected.", "yellow"))
                sys.exit(0)
        elif args.target:
            github_pr_info = parse_github_pr_url(args.target)
            if github_pr_info:
                print(_colorize(f"📥 Fetching diff for GitHub PR: {args.target}...", "cyan"))
                content = fetch_pr_diff(args.target)
                is_diff = True
            elif not os.path.exists(args.target):
                print(_colorize(f"Error: File not found: {args.target}", "red"))
                sys.exit(1)
            else:
                with open(args.target, "r", encoding="utf-8") as f:
                    content = f.read()
                if args.target.endswith((".diff", ".patch")):
                    is_diff = True
        else:
            print(_colorize("Error: Please provide a file target, GitHub PR URL, or use --git / --staged flag.", "red"))
            review_parser.print_help()
            sys.exit(1)

        min_sev = Severity(args.min_severity) if args.min_severity else None

        print(_colorize("🔍 Analyzing code with AI PR Debugger...", "cyan"))
        try:
            if is_diff:
                report = review_diff(content, model=args.model, mock=args.mock)
            else:
                report = review_code(content, model=args.model, mock=args.mock)
        except Exception as e:
            print(_colorize(f"Review execution failed: {e}", "red"))
            if not args.mock:
                print("Tip: Run with --mock to test offline without an active LLM gateway.")
            sys.exit(1)

        # Output formatting
        if args.format == "json":
            out_str = report.model_dump_json(indent=2)
            if args.output:
                with open(args.output, "w", encoding="utf-8") as f:
                    f.write(out_str)
                print(_colorize(f"Report saved to {args.output}", "green"))
            else:
                print(out_str)
        elif args.format == "markdown":
            md_str = render_markdown(report)
            if args.output:
                with open(args.output, "w", encoding="utf-8") as f:
                    f.write(md_str)
                print(_colorize(f"Markdown report saved to {args.output}", "green"))
            else:
                print(md_str)
        else:
            render_terminal(report, min_severity=min_sev)
            if args.output:
                with open(args.output, "w", encoding="utf-8") as f:
                    f.write(render_markdown(report))
                print(_colorize(f"Markdown report saved to {args.output}", "green"))

        # Optional GitHub PR review posting
        if args.post_review:
            if not github_pr_info:
                print(_colorize("Warning: --post-review requires a GitHub PR URL or slug as target.", "yellow"))
            else:
                owner, repo, pr_number = github_pr_info
                md_review = render_markdown(report)
                verdict = report.review_summary.verdict if report.review_summary else "COMMENT"
                try:
                    post_github_review(owner, repo, pr_number, md_review, verdict=verdict)
                    print(_colorize(f"✔ Successfully posted formal review ({verdict}) to PR #{pr_number}!", "green", bold=True))
                except Exception as e:
                    print(_colorize(f"✘ Failed to post review to GitHub: {e}", "red"))


if __name__ == "__main__":
    main()

