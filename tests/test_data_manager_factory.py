import pytest

from utils.data_manager import DataManager
from utils.data_manager_factory import create_data_manager, get_storage_backend
from utils.supabase_data_manager import SupabaseDataManager


def test_factory_defaults_to_csv(monkeypatch, temp_data_dir):
    monkeypatch.delenv("STOCK_TRACKER_STORAGE_BACKEND", raising=False)

    manager = create_data_manager(data_dir=temp_data_dir)

    assert isinstance(manager, DataManager)


def test_factory_uses_env_backend_for_supabase(monkeypatch):
    monkeypatch.setenv("STOCK_TRACKER_STORAGE_BACKEND", "supabase")
    monkeypatch.setattr(
        "utils.data_manager_factory.SupabaseDataManager",
        lambda: "supabase-manager",
    )

    assert get_storage_backend() == "supabase"
    assert create_data_manager() == "supabase-manager"


def test_factory_rejects_unknown_backend(monkeypatch):
    monkeypatch.setenv("STOCK_TRACKER_STORAGE_BACKEND", "unknown")

    with pytest.raises(ValueError, match="Unsupported storage backend"):
        create_data_manager()


def test_supabase_manager_uses_database_url_environment_fallback(monkeypatch):
    monkeypatch.setenv("SUPABASE_DATABASE_URL", "sqlite:///:memory:")
    monkeypatch.setattr(
        "utils.supabase_data_manager.st.connection",
        lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("no secrets")),
    )

    manager = SupabaseDataManager()

    assert str(manager.engine.url) == "sqlite:///:memory:"
