from __future__ import annotations

import json
from pathlib import Path

from openclaw_tool_audit.audit import AuditOptions, run_audit


def write(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def test_allowed_vs_observed_diffing(tmp_path: Path) -> None:
    config_dir = tmp_path / "agents"
    sessions_dir = tmp_path / "sessions"
    write(
        config_dir / "main.json",
        json.dumps({"name": "main", "allowed_tools": ["read_file", "write_file", "shell"]}),
    )
    write(
        sessions_dir / "session.json",
        json.dumps(
            {
                "agent": "main",
                "events": [
                    {"type": "tool_call", "name": "read_file"},
                    {"type": "tool_call", "name": "network"},
                ],
            }
        ),
    )

    report = run_audit(AuditOptions((config_dir,), (sessions_dir,)))
    summary = report.agents[0]

    assert summary.allowed_tools == {"read_file", "write_file", "shell"}
    assert summary.observed_tools == {"read_file", "network"}
    assert summary.unused_allowed_tools == {"write_file", "shell"}
    assert summary.unexpected_observed_tools == {"network"}


def test_counts_usage_and_jobs(tmp_path: Path) -> None:
    config_dir = tmp_path / "agents"
    sessions_dir = tmp_path / "sessions"
    write(config_dir / "daily.toml", 'name = "daily"\nallowed_tools = ["fetch", "summarize"]\n')
    write(
        sessions_dir / "session.jsonl",
        "\n".join(
            [
                json.dumps(
                    {"agent": "daily", "job": "nightly", "type": "tool_call", "name": "fetch"}
                ),
                json.dumps(
                    {"agent": "daily", "job": "nightly", "type": "tool_call", "name": "fetch"}
                ),
                json.dumps(
                    {
                        "agent": "daily",
                        "job": "nightly",
                        "type": "tool_call",
                        "function": {"name": "summarize"},
                    }
                ),
            ]
        ),
    )

    report = run_audit(AuditOptions((config_dir,), (sessions_dir,)))
    summary = report.agents[0]

    assert summary.observed_counts["fetch"] == 2
    assert summary.observed_counts["summarize"] == 1
    assert report.jobs[0].name == "nightly"
    assert report.jobs[0].observed_counts["fetch"] == 2


def test_missing_config_handling(tmp_path: Path) -> None:
    sessions_dir = tmp_path / "sessions"
    write(
        sessions_dir / "session.json",
        json.dumps({"agent": "ad-hoc", "events": [{"type": "tool_call", "name": "web"}]}),
    )

    report = run_audit(AuditOptions((tmp_path / "missing",), (sessions_dir,)))

    assert report.config_count == 0
    assert report.missing_config_agents == {"ad-hoc"}
    assert report.agents[0].name == "ad-hoc"
    assert report.agents[0].allowed_tools == set()
