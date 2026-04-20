from __future__ import annotations

import json
from collections import Counter
from typing import Any

from .audit import AuditReport
from .models import AuditSummary


def render_text(report: AuditReport, top_tools: int | None = None) -> str:
    lines: list[str] = []
    lines.append("OpenClaw Tool Audit")
    lines.append("===================")
    lines.append(f"Agent configs: {report.config_count}")
    lines.append(f"Observed tool invocations: {report.observation_count}")
    if report.missing_config_agents:
        missing = ", ".join(sorted(report.missing_config_agents))
        lines.append("Missing config for observed agent(s): " + missing)
    lines.append("")

    if report.total_tool_counts:
        lines.append("Top tools overall:")
        for tool, count in _top(report.total_tool_counts, top_tools):
            lines.append(f"  {tool}: {count}")
        lines.append("")

    for summary in report.agents:
        lines.extend(_render_agent_text(summary, top_tools))
        lines.append("")

    if report.jobs:
        lines.append("Cron/job summaries:")
        for job in report.jobs:
            agents = ", ".join(sorted(job.agents)) or "-"
            tools = _format_counts(job.observed_counts, top_tools)
            lines.append(f"  {job.name} [{agents}]: {tools}")

    return "\n".join(lines).rstrip() + "\n"


def render_markdown(report: AuditReport, top_tools: int | None = None) -> str:
    lines: list[str] = ["# OpenClaw Tool Audit", ""]
    lines.append(f"- Agent configs: `{report.config_count}`")
    lines.append(f"- Observed tool invocations: `{report.observation_count}`")
    if report.missing_config_agents:
        missing = ", ".join(sorted(report.missing_config_agents))
        lines.append("- Missing config for observed agent(s): " + missing)
    lines.append("")

    lines.append("## Agents")
    lines.append("")
    lines.append(
        "| Agent | Allowed tools | Observed tools | Unused allowed | Broad allowance signals |"
    )
    lines.append("| --- | --- | --- | --- | --- |")
    for summary in report.agents:
        lines.append(
            "| "
            + " | ".join(
                [
                    _md(summary.name),
                    _md(", ".join(sorted(summary.allowed_tools)) or "-"),
                    _md(_format_counts(summary.observed_counts, top_tools)),
                    _md(", ".join(sorted(summary.unused_allowed_tools)) or "-"),
                    _md("; ".join(summary.broad_allowance_reasons) or "-"),
                ]
            )
            + " |"
        )

    if report.jobs:
        lines.extend(["", "## Cron/Job Summaries", ""])
        lines.append("| Job | Agents | Observed tools |")
        lines.append("| --- | --- | --- |")
        for job in report.jobs:
            lines.append(
                "| "
                + " | ".join(
                    [
                        _md(job.name),
                        _md(", ".join(sorted(job.agents)) or "-"),
                        _md(_format_counts(job.observed_counts, top_tools)),
                    ]
                )
                + " |"
            )

    return "\n".join(lines) + "\n"


def render_json(report: AuditReport, top_tools: int | None = None) -> str:
    return json.dumps(_report_to_dict(report, top_tools), indent=2, sort_keys=True) + "\n"


def _render_agent_text(summary: AuditSummary, top_tools: int | None) -> list[str]:
    lines = [f"Agent: {summary.name}"]
    lines.append("  Allowed tools: " + (", ".join(sorted(summary.allowed_tools)) or "-"))
    lines.append("  Observed tools: " + _format_counts(summary.observed_counts, top_tools))
    unused = ", ".join(sorted(summary.unused_allowed_tools)) or "-"
    lines.append("  Unused allowed tools: " + unused)
    if summary.unexpected_observed_tools:
        unexpected = ", ".join(sorted(summary.unexpected_observed_tools))
        lines.append("  Observed but not allowed: " + unexpected)
    if summary.broad_allowance_reasons:
        lines.append("  Suspicious broad allowances: " + "; ".join(summary.broad_allowance_reasons))
    if summary.jobs:
        lines.append("  Jobs: " + ", ".join(sorted(summary.jobs)))
    return lines


def _report_to_dict(report: AuditReport, top_tools: int | None) -> dict[str, Any]:
    return {
        "config_count": report.config_count,
        "observation_count": report.observation_count,
        "missing_config_agents": sorted(report.missing_config_agents),
        "top_tools": [
            {"tool": tool, "count": count}
            for tool, count in _top(report.total_tool_counts, top_tools)
        ],
        "agents": [
            {
                "name": summary.name,
                "allowed_tools": sorted(summary.allowed_tools),
                "observed_tools": [
                    {"tool": tool, "count": count}
                    for tool, count in _top(summary.observed_counts, top_tools)
                ],
                "unused_allowed_tools": sorted(summary.unused_allowed_tools),
                "observed_but_not_allowed": sorted(summary.unexpected_observed_tools),
                "suspicious_broad_allowances": summary.broad_allowance_reasons,
                "jobs": sorted(summary.jobs),
                "sources": sorted(summary.sources),
            }
            for summary in report.agents
        ],
        "jobs": [
            {
                "name": job.name,
                "agents": sorted(job.agents),
                "observed_tools": [
                    {"tool": tool, "count": count}
                    for tool, count in _top(job.observed_counts, top_tools)
                ],
                "sources": sorted(job.sources),
            }
            for job in report.jobs
        ],
    }


def _format_counts(counter: Counter[str], limit: int | None) -> str:
    if not counter:
        return "-"
    return ", ".join(f"{tool} ({count})" for tool, count in _top(counter, limit))


def _top(counter: Counter[str], limit: int | None) -> list[tuple[str, int]]:
    items = counter.most_common(limit)
    return sorted(items, key=lambda item: (-item[1], item[0]))


def _md(value: str) -> str:
    return value.replace("|", "\\|")
