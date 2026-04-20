"""OpenClaw permission-versus-usage audit utilities."""

from importlib.metadata import PackageNotFoundError, version

from .audit import AuditOptions, AuditReport, run_audit

try:
    __version__ = version("openclaw-tool-audit")
except PackageNotFoundError:
    __version__ = "0.0.0"

__all__ = ["AuditOptions", "AuditReport", "__version__", "run_audit"]
