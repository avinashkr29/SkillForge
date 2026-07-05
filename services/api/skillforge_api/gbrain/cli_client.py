"""Thin wrapper around the official garrytan/gbrain CLI."""

from __future__ import annotations

import json
import shutil
import subprocess
from dataclasses import dataclass


@dataclass(frozen=True)
class GBrainCliStatus:
    available: bool
    healthy: bool
    version: str | None
    message: str


class GBrainCliClient:
    """Calls the upstream `gbrain` binary when installed."""

    def __init__(self, binary: str = "gbrain") -> None:
        self.binary = binary

    def status(self) -> GBrainCliStatus:
        if not shutil.which(self.binary):
            return GBrainCliStatus(
                available=False,
                healthy=False,
                version=None,
                message="gbrain CLI not found on PATH",
            )

        try:
            result = subprocess.run(
                [self.binary, "doctor", "--json"],
                capture_output=True,
                text=True,
                timeout=15,
                check=False,
            )
        except (subprocess.TimeoutExpired, OSError) as exc:
            return GBrainCliStatus(
                available=True,
                healthy=False,
                version=None,
                message=str(exc),
            )

        if result.returncode != 0:
            return GBrainCliStatus(
                available=True,
                healthy=False,
                version=None,
                message=result.stderr.strip() or "gbrain doctor failed",
            )

        try:
            payload = json.loads(result.stdout)
        except json.JSONDecodeError:
            return GBrainCliStatus(
                available=True,
                healthy=True,
                version=None,
                message="gbrain doctor ok (non-json output)",
            )

        return GBrainCliStatus(
            available=True,
            healthy=payload.get("status") in {"ok", "warnings"},
            version=payload.get("version"),
            message=payload.get("status", "ok"),
        )

    def get_page(self, slug: str) -> str | None:
        if not shutil.which(self.binary):
            return None

        try:
            result = subprocess.run(
                [self.binary, "get", slug],
                capture_output=True,
                text=True,
                timeout=20,
                check=False,
            )
        except (subprocess.TimeoutExpired, OSError):
            return None

        if result.returncode != 0 or not result.stdout.strip():
            return None
        return result.stdout

    def search(self, query: str) -> str | None:
        if not shutil.which(self.binary):
            return None

        try:
            result = subprocess.run(
                [self.binary, "search", query],
                capture_output=True,
                text=True,
                timeout=30,
                check=False,
            )
        except (subprocess.TimeoutExpired, OSError):
            return None

        if result.returncode != 0:
            return None
        return result.stdout