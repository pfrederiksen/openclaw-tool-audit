from __future__ import annotations

import json
import re
import tomllib
from collections.abc import Iterable, Iterator, Mapping
from pathlib import Path
from typing import Any

from .models import AgentConfig, ToolObservation

CONFIG_EXTENSIONS = {".json", ".toml", ".yaml", ".yml"}
SESSION_EXTENSIONS = {".json", ".jsonl", ".ndjson", ".txt", ".md", ".log"}

TOOL_TEXT_PATTERNS = [
    re.compile(r"\bto=([A-Za-z0-9_.:-]+)"),
    re.compile(r'"recipient_name"\s*:\s*"([^"]+)"'),
    re.compile(r'"tool(?:_name)?"\s*:\s*"([^"]+)"'),
    re.compile(r'"name"\s*:\s*"([^"]+)"\s*,\s*"arguments"\s*:'),
    re.compile(r"<tool>\s*([A-Za-z0-9_.:-]+)\s*</tool>"),
]


def read_agent_configs(paths: Iterable[Path]) -> list[AgentConfig]:
    configs: list[AgentConfig] = []
    for root in paths:
        if not root.exists():
            continue
        files = (
            [root]
            if root.is_file()
            else sorted(p for p in root.rglob("*") if p.suffix in CONFIG_EXTENSIONS)
        )
        for path in files:
            parsed = _load_structured_file(path)
            if parsed is None:
                continue
            config = _config_from_data(parsed, path)
            if config is not None:
                configs.append(config)
    return configs


def read_observations(paths: Iterable[Path]) -> list[ToolObservation]:
    observations: list[ToolObservation] = []
    for root in paths:
        if not root.exists():
            continue
        files = (
            [root]
            if root.is_file()
            else sorted(p for p in root.rglob("*") if p.suffix in SESSION_EXTENSIONS)
        )
        for path in files:
            observations.extend(_observations_from_file(path))
    return observations


def _load_structured_file(path: Path) -> Any | None:
    try:
        text = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        text = path.read_text(errors="ignore")

    try:
        if path.suffix == ".json":
            return json.loads(text)
        if path.suffix == ".toml":
            return tomllib.loads(text)
        if path.suffix in {".yaml", ".yml"}:
            return _load_yaml(text)
    except (json.JSONDecodeError, tomllib.TOMLDecodeError, ValueError):
        return None
    return None


def _load_yaml(text: str) -> Any:
    try:
        import yaml  # type: ignore[import-untyped]

        return yaml.safe_load(text)
    except ImportError:
        return _minimal_yaml(text)


def _minimal_yaml(text: str) -> dict[str, Any]:
    result: dict[str, Any] = {}
    current_key: str | None = None
    for raw_line in text.splitlines():
        line = raw_line.split("#", 1)[0].rstrip()
        if not line.strip():
            continue
        if not line.startswith(" ") and ":" in line:
            key, value = line.split(":", 1)
            key = key.strip()
            value = value.strip()
            current_key = key
            if value:
                result[key] = _yaml_scalar_or_list(value)
            else:
                result[key] = []
            continue
        stripped = line.strip()
        if current_key and stripped.startswith("- "):
            existing = result.setdefault(current_key, [])
            if isinstance(existing, list):
                existing.append(_strip_quotes(stripped[2:].strip()))
    return result


def _yaml_scalar_or_list(value: str) -> Any:
    if value.startswith("[") and value.endswith("]"):
        return [_strip_quotes(item.strip()) for item in value[1:-1].split(",") if item.strip()]
    return _strip_quotes(value)


def _strip_quotes(value: str) -> str:
    return value.strip().strip('"').strip("'")


def _config_from_data(data: Any, path: Path) -> AgentConfig | None:
    if not isinstance(data, Mapping):
        return None

    agent_block = _first_mapping(data, ["agent", "openclaw", "config"]) or data
    name = _first_string(agent_block, ["name", "id", "agent_name"]) or path.stem
    cron_job = _first_string(data, ["cron_job", "job", "job_name", "schedule_name"])
    if cron_job is None:
        cron_job = _first_string(agent_block, ["cron_job", "job", "job_name", "schedule_name"])

    allowed = _find_allowed_tools(data)
    if not allowed:
        return None

    return AgentConfig(
        name=name,
        allowed_tools=frozenset(_normalize_tool(tool) for tool in allowed),
        source=path,
        cron_job=cron_job,
    )


def _find_allowed_tools(data: Any) -> list[str]:
    keys = _allowed_tool_keys()
    values: list[str] = []
    for key, value in _walk_items(data):
        if key in keys:
            values.extend(_coerce_tool_list(value))
    return values


def _allowed_tool_keys() -> set[str]:
    return {
        "allowed_tools",
        "tools",
        "tool_allowlist",
        "allow_tools",
        "allowedToolNames",
        "allowed_tools_list",
    }


def _coerce_tool_list(value: Any) -> list[str]:
    if isinstance(value, str):
        return [item.strip() for item in re.split(r"[, ]+", value) if item.strip()]
    if isinstance(value, list | tuple | set):
        result: list[str] = []
        for item in value:
            if isinstance(item, str):
                result.append(item)
            elif isinstance(item, Mapping):
                maybe_name = _first_string(item, ["name", "tool", "id"])
                if maybe_name:
                    result.append(maybe_name)
                else:
                    result.extend(_nested_tool_names(item))
        return result
    if isinstance(value, Mapping):
        enabled: list[str] = []
        for key, item_value in value.items():
            if item_value is True:
                enabled.append(str(key))
                continue
            if (
                isinstance(item_value, str)
                and item_value.lower() in {"allow", "allowed", "enabled"}
            ):
                enabled.append(str(key))
                continue
            if isinstance(item_value, Mapping) and _mapping_enables_tool(item_value):
                enabled.append(str(key))
                continue
            nested = _nested_tool_names(item_value)
            if nested:
                enabled.append(str(key))
                enabled.extend(nested)
        return enabled
    return []


def _mapping_enables_tool(value: Mapping[str, Any]) -> bool:
    for item_value in value.values():
        if item_value is True:
            return True
        if isinstance(item_value, str) and item_value.lower() in {"allow", "allowed", "enabled"}:
            return True
    return False


def _nested_tool_names(value: Any) -> list[str]:
    if isinstance(value, Mapping):
        direct_name = _first_string(value, ["name", "tool", "id"])
        if direct_name:
            return [direct_name]
        nested: list[str] = []
        for key, item_value in value.items():
            if key in _allowed_tool_keys():
                nested.extend(_coerce_tool_list(item_value))
            elif isinstance(item_value, Mapping):
                nested.extend(_nested_tool_names(item_value))
            elif isinstance(item_value, list | tuple | set):
                for item in item_value:
                    nested.extend(_nested_tool_names(item))
        return nested
    if isinstance(value, list | tuple | set):
        nested: list[str] = []
        for item in value:
            if isinstance(item, str):
                nested.append(item)
            elif isinstance(item, Mapping):
                nested.extend(_nested_tool_names(item))
        return nested
    return []


def _observations_from_file(path: Path) -> list[ToolObservation]:
    try:
        text = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        text = path.read_text(errors="ignore")

    if path.suffix == ".json":
        try:
            return list(_observations_from_data(json.loads(text), path))
        except json.JSONDecodeError:
            pass

    if path.suffix in {".jsonl", ".ndjson", ".log"}:
        observations: list[ToolObservation] = []
        for line in text.splitlines():
            if not line.strip().startswith(("{", "[")):
                continue
            try:
                observations.extend(_observations_from_data(json.loads(line), path))
            except json.JSONDecodeError:
                continue
        if observations:
            return observations

    return list(_observations_from_text(text, path))


def _observations_from_data(data: Any, path: Path) -> Iterator[ToolObservation]:
    default_agent = _find_agent_name(data) or "unknown"
    default_job = _find_job_name(data)
    for event in _walk_mappings(data):
        tool = _tool_name_from_event(event)
        if tool is None:
            continue
        yield ToolObservation(
            agent=_find_agent_name(event) or default_agent,
            tool=_normalize_tool(tool),
            source=path,
            job=_find_job_name(event) or default_job,
        )


def _observations_from_text(text: str, path: Path) -> Iterator[ToolObservation]:
    for pattern in TOOL_TEXT_PATTERNS:
        for match in pattern.finditer(text):
            yield ToolObservation(
                agent="unknown",
                tool=_normalize_tool(match.group(1)),
                source=path,
            )


def _tool_name_from_event(event: Mapping[str, Any]) -> str | None:
    event_type = str(event.get("type", "")).lower()
    if event_type in {"tool_call", "tool_use", "function_call"}:
        direct = _first_string(event, ["tool", "tool_name", "name", "recipient_name"])
        if direct:
            return direct
    if "recipient_name" in event and isinstance(event["recipient_name"], str):
        return event["recipient_name"]
    if "tool" in event and isinstance(event["tool"], str):
        return event["tool"]
    if "tool_name" in event and isinstance(event["tool_name"], str):
        return event["tool_name"]
    function = event.get("function")
    if isinstance(function, Mapping):
        return _first_string(function, ["name"])
    if "function_call" in event and isinstance(event["function_call"], Mapping):
        return _first_string(event["function_call"], ["name"])
    return None


def _find_agent_name(data: Any) -> str | None:
    if not isinstance(data, Mapping):
        return None
    metadata = data.get("metadata")
    candidates = [
        _first_string(data, ["agent", "agent_name", "agent_id"]),
        _first_string(metadata, ["agent", "agent_name", "agent_id"])
        if isinstance(metadata, Mapping)
        else None,
    ]
    openclaw = data.get("openclaw")
    if isinstance(openclaw, Mapping):
        candidates.append(_first_string(openclaw, ["agent", "agent_name", "agent_id", "name"]))
    return next((candidate for candidate in candidates if candidate), None)


def _find_job_name(data: Any) -> str | None:
    if not isinstance(data, Mapping):
        return None
    metadata = data.get("metadata")
    candidates = [
        _first_string(data, ["cron_job", "job", "job_name", "schedule_name"]),
        _first_string(metadata, ["cron_job", "job", "job_name", "schedule_name"])
        if isinstance(metadata, Mapping)
        else None,
    ]
    return next((candidate for candidate in candidates if candidate), None)


def _walk_items(data: Any) -> Iterator[tuple[str, Any]]:
    if isinstance(data, Mapping):
        for key, value in data.items():
            yield str(key), value
            yield from _walk_items(value)
    elif isinstance(data, list | tuple):
        for value in data:
            yield from _walk_items(value)


def _walk_mappings(data: Any) -> Iterator[Mapping[str, Any]]:
    if isinstance(data, Mapping):
        yield data
        for value in data.values():
            yield from _walk_mappings(value)
    elif isinstance(data, list | tuple):
        for value in data:
            yield from _walk_mappings(value)


def _first_mapping(data: Mapping[str, Any], keys: Iterable[str]) -> Mapping[str, Any] | None:
    for key in keys:
        value = data.get(key)
        if isinstance(value, Mapping):
            return value
    return None


def _first_string(data: Any, keys: Iterable[str]) -> str | None:
    if not isinstance(data, Mapping):
        return None
    for key in keys:
        value = data.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


def _normalize_tool(tool: str) -> str:
    return tool.strip()
