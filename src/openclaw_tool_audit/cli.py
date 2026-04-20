from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .audit import AuditOptions, run_audit
from .output import render_json, render_markdown, render_text


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    config_paths = tuple(Path(path).expanduser() for path in args.config)
    session_paths = tuple(Path(path).expanduser() for path in args.sessions)

    report = run_audit(
        AuditOptions(
            config_paths=config_paths,
            session_paths=session_paths,
            agent_filter=args.agent,
            last=args.last,
            top_tools=args.top_tools,
            unused_only=args.unused_only,
            broadest_first=args.broadest_first,
        )
    )

    if args.json:
        output = render_json(report, args.top_tools)
    elif args.markdown:
        output = render_markdown(report, args.top_tools)
    else:
        output = render_text(report, args.top_tools)

    sys.stdout.write(output)
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = _DefaultingArgumentParser(
        prog="openclaw-tool-audit",
        description="Audit OpenClaw allowed tools against observed tool usage.",
    )
    parser.add_argument(
        "--config",
        action="append",
        default=[],
        metavar="PATH",
        help="Agent config file or directory. May be repeated.",
    )
    parser.add_argument(
        "--sessions",
        action="append",
        default=[],
        metavar="PATH",
        help="Session/transcript file or directory. May be repeated.",
    )
    parser.add_argument("--agent", help="Only show one agent.")
    parser.add_argument(
        "--last",
        help="Accepted for workflow compatibility. Timestamp filtering is not applied yet.",
    )
    parser.add_argument("--json", action="store_true", help="Emit JSON.")
    parser.add_argument("--markdown", action="store_true", help="Emit Markdown.")
    parser.add_argument("--top-tools", type=int, help="Limit observed tool lists to the top N.")
    parser.add_argument(
        "--unused-only",
        action="store_true",
        help="Only show agents with unused allowed tools.",
    )
    parser.add_argument(
        "--broadest-first",
        action="store_true",
        help="Sort agents by broad allowance signals first.",
    )
    return parser


def _default_paths() -> tuple[list[str], list[str]]:
    cwd = Path.cwd()
    home = Path.home()
    return (
        [
            str(cwd / ".openclaw" / "agents"),
            str(cwd / "agents"),
            str(home / ".openclaw" / "agents"),
        ],
        [
            str(cwd / ".openclaw" / "sessions"),
            str(cwd / "sessions"),
            str(home / ".openclaw" / "sessions"),
        ],
    )


def _with_defaults(namespace: argparse.Namespace) -> argparse.Namespace:
    default_config, default_sessions = _default_paths()
    if not namespace.config:
        namespace.config = default_config
    if not namespace.sessions:
        namespace.sessions = default_sessions
    return namespace


class _DefaultingArgumentParser(argparse.ArgumentParser):
    def parse_args(
        self,
        args: list[str] | None = None,
        namespace: argparse.Namespace | None = None,
    ):
        return _with_defaults(super().parse_args(args, namespace))


if __name__ == "__main__":
    raise SystemExit(main())
