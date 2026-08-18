"""Backup helpers for SQLite journal and configs."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
import shutil


@dataclass(frozen=True)
class BackupManifest:
    created_at: datetime
    files: tuple[Path, ...]


def backup_runtime_files(*, db_path: str | Path, config_dir: str | Path, destination: str | Path) -> BackupManifest:
    destination_path = Path(destination)
    destination_path.mkdir(parents=True, exist_ok=True)
    copied: list[Path] = []
    db = Path(db_path)
    if db.exists():
        target = destination_path / db.name
        shutil.copy2(db, target)
        copied.append(target)
    config_root = Path(config_dir)
    if config_root.exists():
        config_target = destination_path / "config"
        if config_target.exists():
            shutil.rmtree(config_target)
        shutil.copytree(config_root, config_target)
        copied.append(config_target)
    return BackupManifest(created_at=datetime.now(UTC), files=tuple(copied))

