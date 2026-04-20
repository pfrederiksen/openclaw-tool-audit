# Changelog

## 0.1.1 - 2026-04-20

- Fixed parser crashes on nested tool config values where mapping values can be lists or nested mappings.
- Improved observed transcript parsing for real OpenClaw session JSONL shapes.
- Added support for embedded assistant content tool calls, OpenAI-style `tool_calls`, `input_tool_call`, camelCase tool/function keys, session-level agent/job envelopes, and text-embedded tool markers.
- Added sanitized OpenClaw session fixtures and regression tests for nested config and transcript-backed observation counts.

## 0.1.0 - 2026-04-20

- Initial release of `openclaw-tool-audit`.
- Adds config parsing for JSON, TOML, and simple YAML agent definitions.
- Adds session/transcript scanning for structured JSON, JSONL, and conservative text patterns.
- Reports allowed tools, observed tools, unused allowed tools, observed-but-not-allowed tools, top tool counts, cron/job summaries, and broad allowance signals.
- Supports terminal, JSON, and Markdown output.
- Adds `--agent`, `--last`, `--top-tools`, `--unused-only`, and `--broadest-first`.
