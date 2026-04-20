# Contributing

## Development Setup

```bash
uv run --extra dev pytest
uv run ruff check .
uv run python -m build
```

The package has no required runtime dependencies. Keep parser changes conservative and add fixtures/tests for every newly supported OpenClaw config or transcript shape.

## Design Constraints

- Keep the CLI focused on permission-versus-usage visibility.
- Prefer readable security-review output over dense diagnostics.
- Do not add enforcement behavior to this tool.
- Avoid collecting or transmitting transcript data.

## Release Process

Releases are tag-driven from `v*.*.*` tags. The GitHub Actions release workflow builds the package, publishes it to PyPI, creates a GitHub release, and bumps the Homebrew tap formula.
