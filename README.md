# openclaw-tool-audit

`openclaw-tool-audit` is a small CLI for reviewing OpenClaw tool permissions against actual local tool usage. It is intentionally focused on permission-versus-usage visibility for security reviews.

## Install

```bash
pipx install openclaw-tool-audit
brew install pfrederiksen/tap/openclaw-tool-audit
```

From a checkout:

```bash
python -m pip install -e .
openclaw-tool-audit --help
```

## Examples

```bash
openclaw-tool-audit
openclaw-tool-audit --agent main --last 14d
openclaw-tool-audit --json
openclaw-tool-audit --markdown --broadest-first
openclaw-tool-audit --config fixtures/agents --sessions fixtures/sessions --top-tools 5
openclaw-tool-audit --version
```

By default the CLI checks these config locations:

- `./.openclaw/agents`
- `./agents`
- `~/.openclaw/agents`

And these observed session locations:

- `./.openclaw/sessions`
- `./sessions`
- `~/.openclaw/sessions`
- `~/.openclaw/transcripts`
- `~/.openclaw/agents/<agentId>/sessions`

Use `--config PATH` and `--sessions PATH` to point at specific files or directories. Both flags may be repeated.

## Where Allowed Tools Come From

Allowed tools are read from local agent configuration files. The CLI supports `.json`, `.toml`, `.yaml`, and `.yml` files.

It looks for common allowlist fields at any depth:

- `allowed_tools`
- `tools`
- `tool_allowlist`
- `allow_tools`
- `allowedToolNames`
- `allowed_tools_list`

Values may be a list of strings, a comma/space separated string, a list of objects with `name`, `tool`, or `id`, or a mapping where enabled tools are marked `true`, `allow`, `allowed`, or `enabled`.

## Where Observed Tools Come From

Observed tools are read from local session or transcript files. The CLI supports `.json`, `.jsonl`, `.ndjson`, `.txt`, `.md`, and `.log`.

Structured JSON scanning recognizes common tool-call shapes:

- `{"type": "tool_call", "name": "read_file"}`
- `{"type": "tool_use", "tool": "web"}`
- `{"type": "tool", "tool": {"name": "shell"}}`
- `{"type": "input_tool_call", "name": "read"}`
- `{"type": "tool_use", "toolName": "edit"}`
- `{"recipient_name": "functions.exec_command"}`
- `{"function": {"name": "fetch_url"}}`
- `{"function_call": {"name": "summarize"}}`
- `{"functionCall": {"name": "web_fetch"}}`
- `{"message": {"tool_calls": [{"function": {"name": "exec"}}]}}`
- `{"message": {"content": [{"type": "input_tool_call", "name": "read"}]}}`

Plain text transcripts are scanned with conservative patterns such as `to=tool_name`, `recipient_name`, and `<tool>tool_name</tool>`.

## Output

Terminal output includes:

- allowed tools
- observed tools and invocation counts
- unused allowed tools
- observed-but-not-allowed tools
- tools used most often
- suspicious broad allowances
- cron/job summaries when job names are present in transcripts

Suspicious broad allowances are heuristics. The CLI flags wildcard-like tools, broad capability tokens such as `shell`, `filesystem`, `network`, `web`, and `github`, and allowlists where most entries were not observed.

## Options

```text
--agent NAME       Only show one agent.
--last 14d         Filter observations by transcript file mtime. Supports h, d, and w.
--json             Emit JSON.
--markdown         Emit Markdown.
--top-tools N      Limit observed tool lists to the top N.
--unused-only      Only show agents with unused allowed tools.
--broadest-first   Sort agents by broad allowance signals first.
```

## Development

```bash
python -m pip install -e ".[dev]"
pytest
```

This project has no runtime dependencies. YAML support uses PyYAML when available and otherwise falls back to a small parser that handles simple key/value and list allowlists.

## Release

Releases are tag-driven. Create a version tag such as:

```bash
git tag v0.1.0
git push origin v0.1.0
```

The release workflow builds the package, publishes to PyPI, creates a GitHub release, and bumps the Homebrew formula in `pfrederiksen/homebrew-tap`.

Required repository secrets:

- `HOMEBREW_TAP_TOKEN`, a GitHub token that can push to `pfrederiksen/homebrew-tap`.

For PyPI, either configure Trusted Publishing for this repository or set `PYPI_API_TOKEN` as a repository secret.

Do not commit PyPI tokens to the repository.

## Limitations

- OpenClaw config and transcript formats are inferred from common local shapes; unusual schemas may need explicit `--config` and `--sessions` paths or parser updates.
- `--last` currently filters by transcript file modification time, not by event-level timestamps.
- Text transcript parsing is best effort and may miss custom tool-call formats.
- The audit is visibility-focused; it does not enforce permissions or block tool usage.
