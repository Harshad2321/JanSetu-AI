"""
JanSetu AI — Streamlit Companion Configuration.

Exposes backend connection settings with environment variable overrides.
Never exposes API keys or internal database paths.
"""

import os

def _get_setting(key: str, default: str = "") -> str:
    """Safely check Streamlit Cloud secrets first, then OS environment variables."""
    try:
        import streamlit as st
        if hasattr(st, "secrets"):
            if key in st.secrets:
                return str(st.secrets[key]).strip()
            lower_k = key.lower()
            if lower_k in st.secrets:
                return str(st.secrets[lower_k]).strip()
    except Exception:
        pass

    return (os.getenv(key) or os.getenv(key.lower()) or os.getenv(key.upper()) or default).strip()


# Base URL for the FastAPI backend service (Render deployment or local)
API_BASE_URL = _get_setting("FASTAPI_BASE_URL") or _get_setting("API_BASE_URL") or "http://localhost:8000"
API_BASE_URL = API_BASE_URL.rstrip("/")

DEFAULT_TIMEOUT_SECONDS = float(_get_setting("API_TIMEOUT_SECONDS", "30.0"))
