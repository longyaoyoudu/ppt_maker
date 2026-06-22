"""CRUD for model configuration (one row per stage).

API keys are base64-encoded at rest. This is obfuscation, not strong
encryption — sufficient to prevent casual file inspection.
"""
from __future__ import annotations

import base64
import json
from pathlib import Path

from app.db import get_connection, init_db
from app.models import ModelConfig


class ConfigNotFound(LookupError):
    """Raised when a config row is missing."""


def _encode_key(api_key: str) -> str:
    return base64.b64encode(api_key.encode("utf-8")).decode("ascii")


def _decode_key(encoded: str) -> str:
    return base64.b64decode(encoded.encode("ascii")).decode("utf-8")


class ConfigStore:
    def __init__(self, db_path: Path | None = None) -> None:
        if db_path is not None:
            init_db(db_path)
            self._db_path = db_path
        else:
            self._db_path = None  # use default from env

    def save(self, cfg: ModelConfig) -> None:
        with get_connection(self._db_path) as conn:
            conn.execute(
                """
                INSERT INTO model_configs(stage, provider, base_url, api_key, model_name, extra_params, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(stage) DO UPDATE SET
                    provider=excluded.provider,
                    base_url=excluded.base_url,
                    api_key=excluded.api_key,
                    model_name=excluded.model_name,
                    extra_params=excluded.extra_params,
                    updated_at=CURRENT_TIMESTAMP
                """,
                (
                    cfg.stage,
                    cfg.provider,
                    cfg.base_url,
                    _encode_key(cfg.api_key),
                    cfg.model_name,
                    json.dumps(cfg.extra_params) if cfg.extra_params is not None else None,
                ),
            )

    def get(self, stage: str) -> ModelConfig:
        with get_connection(self._db_path) as conn:
            row = conn.execute("SELECT * FROM model_configs WHERE stage=?", (stage,)).fetchone()
        if row is None:
            raise ConfigNotFound(f"No config for stage={stage!r}")
        return ModelConfig(
            stage=row["stage"],
            provider=row["provider"],
            api_key=_decode_key(row["api_key"]),
            model_name=row["model_name"],
            base_url=row["base_url"],
            extra_params=json.loads(row["extra_params"]) if row["extra_params"] else None,
        )

    def list_all(self) -> list[ModelConfig]:
        with get_connection(self._db_path) as conn:
            rows = conn.execute("SELECT stage FROM model_configs").fetchall()
        return [self.get(r["stage"]) for r in rows]
