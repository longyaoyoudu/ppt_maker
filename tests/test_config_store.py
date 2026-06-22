"""Tests for the model config store."""
import base64

import pytest

from app.config_store import ConfigStore, ConfigNotFound
from app.models import ModelConfig


def test_save_and_get_round_trip(tmp_dir):
    store = ConfigStore(db_path=tmp_dir / "test.db")
    cfg = ModelConfig(stage="outline", provider="openai", api_key="secret-123", model_name="gpt-4o")
    store.save(cfg)
    loaded = store.get("outline")
    assert loaded == cfg


def test_get_missing_raises(tmp_dir):
    store = ConfigStore(db_path=tmp_dir / "test.db")
    with pytest.raises(ConfigNotFound):
        store.get("ppt")


def test_api_key_is_encoded_at_rest(tmp_dir):
    db_path = tmp_dir / "test.db"
    store = ConfigStore(db_path=db_path)
    store.save(ModelConfig(stage="outline", provider="openai", api_key="plaintext-key", model_name="gpt"))
    raw_bytes = db_path.read_bytes()
    encoded = base64.b64encode(b"plaintext-key")
    assert b"plaintext-key" not in raw_bytes
    assert encoded in raw_bytes


def test_update_overwrites(tmp_dir):
    store = ConfigStore(db_path=tmp_dir / "test.db")
    store.save(ModelConfig(stage="ppt", provider="claude", api_key="k1", model_name="claude-sonnet-4-6"))
    store.save(ModelConfig(stage="ppt", provider="openai", api_key="k2", model_name="gpt-4o"))
    assert store.get("ppt").provider == "openai"


def test_list_stages(tmp_dir):
    store = ConfigStore(db_path=tmp_dir / "test.db")
    store.save(ModelConfig(stage="outline", provider="openai", api_key="k", model_name="m"))
    store.save(ModelConfig(stage="ppt", provider="claude", api_key="k", model_name="m"))
    stages = {s.stage for s in store.list_all()}
    assert stages == {"outline", "ppt"}
