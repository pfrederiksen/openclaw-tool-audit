from __future__ import annotations

import json
from pathlib import Path

import pytest

from openclaw_tool_audit.cli import main


def test_cli_json_output(tmp_path: Path, capsys) -> None:
    config_dir = tmp_path / "agents"
    sessions_dir = tmp_path / "sessions"
    config_dir.mkdir()
    sessions_dir.mkdir()
    (config_dir / "main.json").write_text(
        json.dumps({"name": "main", "allowed_tools": ["read_file"]}),
        encoding="utf-8",
    )
    (sessions_dir / "session.json").write_text(
        json.dumps({"agent": "main", "events": [{"type": "tool_call", "name": "read_file"}]}),
        encoding="utf-8",
    )

    exit_code = main(["--config", str(config_dir), "--sessions", str(sessions_dir), "--json"])

    captured = capsys.readouterr()
    assert exit_code == 0
    payload = json.loads(captured.out)
    assert payload["agents"][0]["name"] == "main"
    assert payload["agents"][0]["observed_tools"] == [{"count": 1, "tool": "read_file"}]


def test_cli_version(capsys) -> None:
    with pytest.raises(SystemExit) as exc_info:
        main(["--version"])

    captured = capsys.readouterr()
    assert exc_info.value.code == 0
    assert captured.out.startswith("openclaw-tool-audit ")
