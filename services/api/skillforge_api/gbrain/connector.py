"""GBrain connector — mock implementation backed by local SOP documents."""

from __future__ import annotations

import os
import re
from datetime import datetime, timezone
from pathlib import Path

from skillforge_shared.models import GBrainDocument

REPO_ROOT = Path(__file__).resolve().parents[4]
DEFAULT_MOCK_DIR = REPO_ROOT / "data" / "gbrain-mock"


class GBrainConnector:
    """Pulls company knowledge documents from GBrain (mocked via local files)."""

    def __init__(self, mock_dir: Path | None = None) -> None:
        self.mock_dir = Path(
            os.environ.get("GBRAIN_MOCK_DIR", mock_dir or DEFAULT_MOCK_DIR)
        )
        self._documents: dict[str, GBrainDocument] = {}
        self._load_mock_documents()

    def _load_mock_documents(self) -> None:
        if not self.mock_dir.exists():
            return

        for path in sorted(self.mock_dir.glob("*.md")):
            content = path.read_text(encoding="utf-8")
            product_code = self._extract_product_code(content) or path.stem.upper()
            doc_id = f"gb-doc-{product_code.lower()}"

            self._documents[doc_id] = GBrainDocument(
                id=doc_id,
                title=self._extract_title(content, path.stem),
                product_code=product_code,
                content=content,
                tags=["assembly", "sop", "lego", product_code.lower()],
                updated_at=datetime.now(timezone.utc),
            )

    @staticmethod
    def _extract_title(content: str, fallback: str) -> str:
        for line in content.splitlines():
            if line.startswith("# "):
                return line[2:].strip()
        return fallback.replace("-", " ").title()

    @staticmethod
    def _extract_product_code(content: str) -> str | None:
        match = re.search(r"\*\*Product Code:\*\*\s*(\S+)", content)
        return match.group(1) if match else None

    def list_documents(self) -> list[GBrainDocument]:
        return sorted(self._documents.values(), key=lambda doc: doc.product_code)

    def get_document(self, document_id: str) -> GBrainDocument | None:
        return self._documents.get(document_id)

    def search_documents(self, query: str) -> list[GBrainDocument]:
        needle = query.lower()
        return [
            doc
            for doc in self.list_documents()
            if needle in doc.title.lower()
            or needle in doc.product_code.lower()
            or needle in doc.content.lower()
        ]