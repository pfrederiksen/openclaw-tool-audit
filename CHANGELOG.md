# Changelog

## 0.1.0 - 2026-04-20

- Initial release of `openclaw-tool-audit`.
- Adds config parsing for JSON, TOML, and simple YAML agent definitions.
- Adds session/transcript scanning for structured JSON, JSONL, and conservative text patterns.
- Reports allowed tools, observed tools, unused allowed tools, observed-but-not-allowed tools, top tool counts, cron/job summaries, and broad allowance signals.
- Supports terminal, JSON, and Markdown output.
- Adds `--agent`, `--last`, `--top-tools`, `--unused-only`, and `--broadest-first`.
