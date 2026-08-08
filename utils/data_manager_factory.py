import os

import streamlit as st
from dotenv import load_dotenv

from .data_manager import DataManager
from .supabase_data_manager import SupabaseDataManager


load_dotenv()


def get_storage_backend() -> str:
    """Return configured storage backend without exposing credential values."""
    env_backend = os.environ.get("STOCK_TRACKER_STORAGE_BACKEND")
    if env_backend:
        return env_backend.strip().lower()

    try:
        return st.secrets.get("storage", {}).get("backend", "csv").strip().lower()
    except Exception:
        return "csv"


def create_data_manager(data_dir: str = "data"):
    """Create the configured data manager, defaulting to the CSV backend."""
    backend = get_storage_backend()
    if backend == "supabase":
        return SupabaseDataManager()
    if backend == "csv":
        return DataManager(data_dir=data_dir)
    raise ValueError(f"Unsupported storage backend: {backend}")
