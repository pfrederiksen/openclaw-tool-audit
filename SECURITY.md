# Security Policy

## Reporting Security Issues

Please report security issues privately through GitHub Security Advisories once the repository is published.

If advisories are not available yet, contact the maintainer directly using the email address associated with the package metadata.

## Scope

`openclaw-tool-audit` is a local visibility tool. It reads local OpenClaw configuration and transcript files, then reports permission-versus-usage differences. It does not enforce permissions, sandbox commands, or block tool execution.

## Handling Sensitive Data

Session transcripts can contain private prompts, file paths, command arguments, and tool outputs. Treat audit output as potentially sensitive, especially JSON and Markdown reports that may be stored or shared.

The CLI does not intentionally transmit data over the network.
