"""GBrain connector — official CLI + brain repo, with mock fallback."""

from __future__ import annotations

import os
import re
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path

from skillforge_shared.models import GBrainDocument

from skillforge_api.gbrain.cli_client import GBrainCliClient

REPO_ROOT = Path(__file__).resolve().parents[4]
DEFAULT_BRAIN_DIR = REPO_ROOT / "brain" / "manufacturing"
DEFAULT_MOCK_DIR = REPO_ROOT / "data" / "gbrain-mock"
GBRAIN_SLUG_PREFIX = "manufacturing"


class ConnectorMode(str, Enum):
    CLI = "gbrain-cli"
    FILESYSTEM = "brain-filesystem"
    MOCK = "mock-fallback"


class GBrainConnector:
    """Pulls company knowledge from the official GBrain stack.

    Resolution order:
    1. Official `gbrain` CLI (https://github.com/garrytan/gbrain) when healthy
    2. GBrain markdown repo at `brain/manufacturing/`
    3. Legacy mock files at `data/gbrain-mock/`
    """

    def __init__(
        self,
        brain_dir: Path | None = None,
        mock_dir: Path | None = None,
        cli_client: GBrainCliClient | None = None,
    ) -> None:
        self.brain_dir = Path(os.environ.get("GBRAIN_BRAIN_DIR", brain_dir or DEFAULT_BRAIN_DIR))
        self.mock_dir = Path(os.environ.get("GBRAIN_MOCK_DIR", mock_dir or DEFAULT_MOCK_DIR))
        self.cli = cli_client or GBrainCliClient()
        self.mode = self._resolve_mode()
        self._documents: dict[str, GBrainDocument] = {}
        self._load_documents()

    def _resolve_mode(self) -> ConnectorMode:
        forced = os.environ.get("GBRAIN_CONNECTOR_MODE", "").lower()
        if forced == "mock":
            return ConnectorMode.MOCK
        if forced == "filesystem":
            return ConnectorMode.FILESYSTEM

        cli_status = self.cli.status()
        if cli_status.available and cli_status.healthy and self.brain_dir.exists():
            return ConnectorMode.CLI
        if self.brain_dir.exists() and any(self.brain_dir.glob("*.md")):
            return ConnectorMode.FILESYSTEM
        return ConnectorMode.MOCK

    def status(self) -> dict[str, str | bool | None]:
        cli_status = self.cli.status()
        return {
            "mode": self.mode.value,
            "officialRepo": "https://github.com/garrytan/gbrain",
            "gstackRepo": "https://github.com/garrytan/gstack",
            "cliAvailable": cli_status.available,
            "cliHealthy": cli_status.healthy,
            "cliVersion": cli_status.version,
            "brainDir": str(self.brain_dir),
            "documentCount": len(self._documents),
        }

    def _load_documents(self) -> None:
        source_dir = self._source_directory()
        if source_dir is None:
            return

        for path in sorted(source_dir.glob("*.md")):
            slug = f"{GBRAIN_SLUG_PREFIX}/{path.stem}"
            content = self._read_page_content(slug, path)
            product_code = self._extract_product_code(content, path) or path.stem.upper()
            doc_id = f"gb-doc-{product_code.lower()}"

            self._documents[doc_id] = GBrainDocument(
                id=doc_id,
                title=self._extract_title(content, path.stem),
                product_code=product_code,
                content=content,
                tags=["assembly", "sop", "lego", product_code.lower(), "gbrain"],
                updated_at=datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc),
            )

    def _source_directory(self) -> Path | None:
        if self.mode == ConnectorMode.MOCK:
            return self.mock_dir if self.mock_dir.exists() else None
        return self.brain_dir if self.brain_dir.exists() else None

    def _read_page_content(self, slug: str, fallback_path: Path) -> str:
        if self.mode == ConnectorMode.CLI:
            cli_content = self.cli.get_page(slug)
            if cli_content:
                return cli_content
        return fallback_path.read_text(encoding="utf-8")

    @staticmethod
    def _extract_title(content: str, fallback: str) -> str:
        frontmatter = re.search(r"^title:\s*(.+)$", content, re.MULTILINE)
        if frontmatter:
            return frontmatter.group(1).strip().strip('"')

        for line in content.splitlines():
            if line.startswith("# "):
                return line[2:].strip()
        return fallback.replace("-", " ").title()

    @staticmethod
    def _extract_product_code(content: str, path: Path) -> str | None:
        frontmatter = re.search(r"^product_code:\s*(\S+)", content, re.MULTILINE)
        if frontmatter:
            return frontmatter.group(1).strip()

        match = re.search(r"\*\*Product Code:\*\*\s*(\S+)", content)
        if match:
            return match.group(1)
        return None

    def list_documents(self) -> list[GBrainDocument]:
        return sorted(self._documents.values(), key=lambda doc: doc.product_code)

    def get_document(self, document_id: str) -> GBrainDocument | None:
        return self._documents.get(document_id)

    def search_documents(self, query: str) -> list[GBrainDocument]:
        if self.mode == ConnectorMode.CLI:
            cli_hits = self.cli.search(query)
            if cli_hits:
                # Prefer indexed brain results, then filter loaded docs by query terms.
                needle = query.lower()
                hits = [
                    doc
                    for doc in self.list_documents()
                    if needle in doc.title.lower()
                    or needle in doc.product_code.lower()
                    or needle in doc.content.lower()
                ]
                if hits:
                    return hits

        needle = query.lower()
        return [
            doc
            for doc in self.list_documents()
            if needle in doc.title.lower()
            or needle in doc.product_code.lower()
            or needle in doc.content.lower()
        ]