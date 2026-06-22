"""History store: persist outlines and PPT generations for later retrieval."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from app.db import get_connection, init_db
from app.models import Outline


@dataclass
class Generation:
    id: int | None = None
    outline_id: int = 0
    style: str = "business"
    image_mode: str = "placeholder"
    pptx_path: str | None = None
    pdf_path: str | None = None


@dataclass
class OutlineRow:
    id: int
    topic: str
    requirements: str | None
    content: Outline
    created_at: str


class HistoryStore:
    def __init__(self, db_path: Path | None = None) -> None:
        if db_path is not None:
            init_db(db_path)
            self._db_path = db_path
        else:
            self._db_path = None

    def save_outline(self, outline: Outline, requirements: str | None = None) -> int:
        with get_connection(self._db_path) as conn:
            cur = conn.execute(
                "INSERT INTO outlines(topic, requirements, content_json) VALUES (?, ?, ?)",
                (outline.topic, requirements, outline.model_dump_json()),
            )
            return int(cur.lastrowid)

    def update_outline(self, outline_id: int, outline: Outline) -> None:
        with get_connection(self._db_path) as conn:
            conn.execute(
                "UPDATE outlines SET content_json=? WHERE id=?",
                (outline.model_dump_json(), outline_id),
            )

    def get_outline(self, outline_id: int) -> OutlineRow | None:
        with get_connection(self._db_path) as conn:
            row = conn.execute(
                "SELECT id, topic, requirements, content_json, created_at FROM outlines WHERE id=?",
                (outline_id,),
            ).fetchone()
        if row is None:
            return None
        return OutlineRow(
            id=row["id"],
            topic=row["topic"],
            requirements=row["requirements"],
            content=Outline.model_validate_json(row["content_json"]),
            created_at=row["created_at"],
        )

    def list_outlines(self) -> list[OutlineRow]:
        with get_connection(self._db_path) as conn:
            rows = conn.execute(
                "SELECT id, topic, requirements, content_json, created_at FROM outlines ORDER BY id DESC"
            ).fetchall()
        return [
            OutlineRow(
                id=r["id"],
                topic=r["topic"],
                requirements=r["requirements"],
                content=Outline.model_validate_json(r["content_json"]),
                created_at=r["created_at"],
            )
            for r in rows
        ]

    def save_generation(self, gen: Generation) -> int:
        with get_connection(self._db_path) as conn:
            cur = conn.execute(
                "INSERT INTO generations(outline_id, style, image_mode, pptx_path, pdf_path) VALUES (?, ?, ?, ?, ?)",
                (gen.outline_id, gen.style, gen.image_mode, gen.pptx_path, gen.pdf_path),
            )
            return int(cur.lastrowid)

    def get_generation(self, generation_id: int) -> Generation | None:
        with get_connection(self._db_path) as conn:
            row = conn.execute(
                "SELECT id, outline_id, style, image_mode, pptx_path, pdf_path FROM generations WHERE id=?",
                (generation_id,),
            ).fetchone()
        if row is None:
            return None
        return Generation(
            id=row["id"],
            outline_id=row["outline_id"],
            style=row["style"] or "business",
            image_mode=row["image_mode"] or "placeholder",
            pptx_path=row["pptx_path"],
            pdf_path=row["pdf_path"],
        )

    def list_generations(self) -> list[Generation]:
        with get_connection(self._db_path) as conn:
            rows = conn.execute(
                "SELECT id, outline_id, style, image_mode, pptx_path, pdf_path FROM generations ORDER BY id DESC"
            ).fetchall()
        return [
            Generation(
                id=r["id"],
                outline_id=r["outline_id"],
                style=r["style"] or "business",
                image_mode=r["image_mode"] or "placeholder",
                pptx_path=r["pptx_path"],
                pdf_path=r["pdf_path"],
            )
            for r in rows
        ]
