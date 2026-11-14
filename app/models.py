"""
Data models for the AI PR Debugger.
Defines strongly typed, validated schemas for review findings, severities, and reports.
"""

from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, Field


class Severity(str, Enum):
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    INFO = "INFO"


class Category(str, Enum):
    SECURITY = "SECURITY"
    BUG = "BUG"
    PERFORMANCE = "PERFORMANCE"
    LOGIC = "LOGIC"
    STYLE = "STYLE"
    RELIABILITY = "RELIABILITY"


class BugFinding(BaseModel):
    """Backwards-compatible finding model with enriched metadata."""
    bug: str = Field(description="Clear title and description of the bug or defect")
    impact: str = Field(description="Operational, security, or business impact of this issue")
    fix: str = Field(description="Recommended fix or code remediation")
    regression_test: str = Field(description="Unit test code snippet or test case that catches this bug")
    file_path: Optional[str] = Field(default=None, description="Path of the affected file")
    line_number: Optional[int] = Field(default=None, description="Line number where the issue starts")
    severity: Severity = Field(default=Severity.HIGH, description="Severity ranking of the finding")
    category: Category = Field(default=Category.BUG, description="Taxonomy classification of the finding")


class ReviewSummary(BaseModel):
    verdict: str = Field(
        default="COMMENT",
        description="Review verdict: APPROVE, REQUEST_CHANGES, or COMMENT"
    )
    total_findings: int = Field(default=0, description="Total count of issues discovered")
    critical_count: int = Field(default=0, description="Count of critical severity issues")
    high_count: int = Field(default=0, description="Count of high severity issues")
    overview: str = Field(description="Executive summary of the PR or code review")


class ReviewReport(BaseModel):
    """Complete structured review report."""
    summary: str = Field(description="High-level summary of the code review")
    findings: List[BugFinding] = Field(default_factory=list, description="List of detected bugs/improvements")
    review_summary: Optional[ReviewSummary] = Field(
        default=None,
        description="Structured verdict and severity breakdown"
    )

