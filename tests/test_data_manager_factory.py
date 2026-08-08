import pytest

from utils.data_manager import DataManager
from utils.data_manager_factory import create_data_manager, get_storage_backend
from utils.supabase_data_manager import SupabaseDataManager


def test_factory_defaults_to_csv(monkeypatch, temp_data_dir):
    monkeypatch.delenv("STOCK_TRACKER_STORAGE_BACKEND", raising=False)
    monkeypatch.setattr(
        "utils.data_manager_factory.has_supabase_connection_config",
        lambda: False,
    )

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


def test_factory_detects_saved_supabase_credentials(monkeypatch):
    monkeypatch.delenv("STOCK_TRACKER_STORAGE_BACKEND", raising=False)
    monkeypatch.setattr(
        "utils.data_manager_factory.has_supabase_connection_config",
        lambda: True,
    )

    assert get_storage_backend() == "supabase"


def test_supabase_manager_builds_direct_url_from_existing_credentials(monkeypatch):
    monkeypatch.delenv("SUPABASE_DATABASE_URL", raising=False)
    monkeypatch.setenv("SUPABASE_URL", "https://project-ref.supabase.co")
    monkeypatch.setenv("database_password", "password-with-special-characters!@")

    manager = SupabaseDataManager()

    assert manager.engine.url.host == "db.project-ref.supabase.co"
    assert manager.engine.url.username == "postgres"
    assert manager.engine.url.database == "postgres"
