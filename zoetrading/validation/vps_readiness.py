"""VPS readiness checks that protect business logic portability."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class VpsReadinessReport:
    ready: bool
    blockers: tuple[str, ...]


def check_vps_readiness(*, mt5_installed: bool, python_installed: bool, secrets_externalized: bool, supervisor_configured: bool, business_logic_changed: bool) -> VpsReadinessReport:
    blockers: list[str] = []
    if business_logic_changed:
        blockers.append("VPS migration must not change trading business logic")
    if not mt5_installed:
        blockers.append("MT5 is not installed on VPS")
    if not python_installed:
        blockers.append("Python is not installed on VPS")
    if not secrets_externalized:
        blockers.append("secrets are not externalized")
    if not supervisor_configured:
        blockers.append("process supervisor/startup is not configured")
    return VpsReadinessReport(ready=not blockers, blockers=tuple(blockers))

