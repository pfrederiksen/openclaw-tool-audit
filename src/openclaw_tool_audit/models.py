from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path


@dataclass(frozen=True)
class AgentConfig:
    name: str
    allowed_tools: frozenset[str]
    source: Path | None = None
    cron_job: str | None = None


@dataclass(frozen=True)
class ToolObservation:
    agent: str
    tool: str
    source: Path | None = None
    job: str | None = None


@dataclass
class AuditSummary:
    name: str
    allowed_tools: set[str] = field(default_factory=set)
    observed_counts: Counter[str] = field(default_factory=Counter)
    sources: set[str] = field(default_factory=set)
    jobs: set[str] = field(default_factory=set)

    @property
    def observed_tools(self) -> set[str]:
        return set(self.observed_counts)

    @property
    def unused_allowed_tools(self) -> set[str]:
        if "*" in self.allowed_tools or "all" in {tool.lower() for tool in self.allowed_tools}:
            return set()
        return self.allowed_tools - self.observed_tools

    @property
    def unexpected_observed_tools(self) -> set[str]:
        lowered = {tool.lower() for tool in self.allowed_tools}
        if "*" in self.allowed_tools or "all" in lowered:
            return set()
        return self.observed_tools - self.allowed_tools

    @property
    def unused_ratio(self) -> float:
        if not self.allowed_tools or "*" in self.allowed_tools:
            return 0.0
        return len(self.unused_allowed_tools) / len(self.allowed_tools)

    @property
    def broad_allowance_reasons(self) -> list[str]:
        reasons: list[str] = []
        broad_tokens = {
            "*",
            "all",
            "bash",
            "shell",
            "exec",
            "filesystem",
            "file_system",
            "network",
            "web",
            "browser",
            "github",
        }

        matching = sorted(tool for tool in self.allowed_tools if tool.lower() in broad_tokens)
        if matching:
            reasons.append("broad token(s): " + ", ".join(matching))
        if len(self.allowed_tools) >= 10 and self.unused_ratio >= 0.6:
            reasons.append("large allowlist with high unused ratio")
        elif len(self.allowed_tools) >= 6 and self.unused_ratio >= 0.75:
            reasons.append("mostly unused allowlist")
        return reasons

    @property
    def broadness_score(self) -> float:
        return (
            len(self.broad_allowance_reasons) * 10
            + self.unused_ratio * max(len(self.allowed_tools), 1)
        )


@dataclass
class JobSummary:
    name: str
    observed_counts: Counter[str] = field(default_factory=Counter)
    agents: set[str] = field(default_factory=set)
    sources: set[str] = field(default_factory=set)
