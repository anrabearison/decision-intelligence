"""
Tests du middleware de clé API interne.
Actif seulement si INTERNAL_API_KEY est définie dans l'environnement
(permet de développer sans clé en local, cf. ARCHITECTURE.md Phase 2 vs 5).
"""
import io
import importlib
import os
import sys


def _reload_app_with_env(monkeypatch, key_value):
    if key_value is None:
        monkeypatch.delenv("INTERNAL_API_KEY", raising=False)
    else:
        monkeypatch.setenv("INTERNAL_API_KEY", key_value)
    if "main" in sys.modules:
        importlib.reload(sys.modules["main"])
    else:
        import main  # noqa
    from fastapi.testclient import TestClient
    import main as main_module
    return TestClient(main_module.app)


class TestNoKeyConfigured:
    def test_requests_allowed_when_no_key_set(self, monkeypatch):
        client = _reload_app_with_env(monkeypatch, None)
        response = client.get("/health")
        assert response.status_code == 200


class TestKeyConfigured:
    def test_request_without_key_is_rejected(self, monkeypatch):
        client = _reload_app_with_env(monkeypatch, "secret123")
        response = client.get("/health")
        assert response.status_code == 403

    def test_request_with_wrong_key_is_rejected(self, monkeypatch):
        client = _reload_app_with_env(monkeypatch, "secret123")
        response = client.get("/health", headers={"X-Internal-Key": "wrong"})
        assert response.status_code == 403

    def test_request_with_correct_key_is_allowed(self, monkeypatch):
        client = _reload_app_with_env(monkeypatch, "secret123")
        response = client.get("/health", headers={"X-Internal-Key": "secret123"})
        assert response.status_code == 200
