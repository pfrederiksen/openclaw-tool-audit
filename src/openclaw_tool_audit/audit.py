from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path

from .models import AgentConfig, AuditSummary, JobSummary, ToolObservation
from .parsers import read_agent_configs, read_observations


@dataclass(frozen=True)
class AuditOptions:
    config_paths: tuple[Path, ...]
    session_paths: tuple[Path, ...]
    agent_filter: str | None = None
    last: str | None = None
    top_tools: int | None = None
    unused_only: bool = False
    broadest_first: bool = False


@dataclass
class AuditReport:
    agents: list[AuditSummary]
    jobs: list[JobSummary]
    missing_config_agents: set[str]
    config_count: int
    observation_count: int

    @property
    def total_tool_counts(self) -> Counter[str]:
        total: Counter[str] = Counter()
        for agent in self.agents:
            total.update(agent.observed_counts)
        return total


def run_audit(options: AuditOptions) -> AuditReport:
    configs = read_agent_configs(options.config_paths)
    observations = _filter_observations(read_observations(options.session_paths), options)
    summaries = _summarize_agents(configs, observations)
    jobs = _summarize_jobs(observations)

    if options.agent_filter:
        summaries = [summary for summary in summaries if summary.name == options.agent_filter]
        jobs = [job for job in jobs if options.agent_filter in job.agents]

    if options.unused_only:
        summaries = [summary for summary in summaries if summary.unused_allowed_tools]

    if options.broadest_first:
        summaries.sort(key=lambda summary: summary.broadness_score, reverse=True)
    else:
        summaries.sort(key=lambda summary: summary.name)

    missing = {
        observation.agent
        for observation in observations
        if observation.agent not in {config.name for config in configs}
    }
    if options.agent_filter:
        missing = {agent for agent in missing if agent == options.agent_filter}

    return AuditReport(
        agents=summaries,
        jobs=jobs,
        missing_config_agents=missing,
        config_count=len(configs),
        observation_count=len(observations),
    )


def _filter_observations(
    observations: list[ToolObservation],
    options: AuditOptions,
) -> list[ToolObservation]:
    if options.last:
        cutoff = _duration_cutoff(options.last)
        if cutoff is not None:
            observations = [
                observation
                for observation in observations
                if observation.source is None
                or datetime.fromtimestamp(
                    observation.source.stat().st_mtime,
                    tz=UTC,
                )
                >= cutoff
            ]
    if options.agent_filter:
        return [
            observation
            for observation in observations
            if observation.agent == options.agent_filter
        ]
    return observations


def _duration_cutoff(value: str) -> datetime | None:
    match = re.fullmatch(r"(\d+)([hdw])", value.strip().lower())
    if not match:
        return None
    amount = int(match.group(1))
    unit = match.group(2)
    if unit == "h":
        delta = timedelta(hours=amount)
    elif unit == "d":
        delta = timedelta(days=amount)
    else:
        delta = timedelta(weeks=amount)
    return datetime.now(tz=UTC) - delta


def _summarize_agents(
    configs: list[AgentConfig],
    observations: list[ToolObservation],
) -> list[AuditSummary]:
    summaries: dict[str, AuditSummary] = {}
    for config in configs:
        summary = summaries.setdefault(config.name, AuditSummary(name=config.name))
        summary.allowed_tools.update(config.allowed_tools)
        if config.source:
            summary.sources.add(str(config.source))
        if config.cron_job:
            summary.jobs.add(config.cron_job)

    for observation in observations:
        summary = summaries.setdefault(observation.agent, AuditSummary(name=observation.agent))
        summary.observed_counts.update([observation.tool])
        if observation.source:
            summary.sources.add(str(observation.source))
        if observation.job:
            summary.jobs.add(observation.job)

    return list(summaries.values())


def _summarize_jobs(observations: list[ToolObservation]) -> list[JobSummary]:
    jobs: dict[str, JobSummary] = {}
    for observation in observations:
        if not observation.job:
            continue
        summary = jobs.setdefault(observation.job, JobSummary(name=observation.job))
        summary.observed_counts.update([observation.tool])
        summary.agents.add(observation.agent)
        if observation.source:
            summary.sources.add(str(observation.source))
    return sorted(jobs.values(), key=lambda job: job.name)
