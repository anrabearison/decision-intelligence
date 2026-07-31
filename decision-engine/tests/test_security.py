"""
Tests du middleware de clé API interne.
Actif seulement si INTERNAL_API_KEY est définie dans l'environnement
(permet de développer sans clé en local, cf. SPEC.md section 5).
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


class TestCorsPreflightNotBlockedByInternalKey:
    def test_options_preflight_not_blocked_when_key_configured(self, monkeypatch):
        # Trouvé en audit : un navigateur n'envoie jamais de header
        # personnalisé (X-Internal-Key) sur une requête préflight OPTIONS
        # - le middleware bloquait ces requêtes en 403, ce qui casserait
        # totalement le CORS dès que INTERNAL_API_KEY est actif (Phase 5).
        client = _reload_app_with_env(monkeypatch, "secret123")
        response = client.options(
            "/engine/analyze",
            headers={
                "Origin": "http://localhost:5173",
                "Access-Control-Request-Method": "POST",
            },
        )
        assert response.status_code != 403

    def test_actual_request_without_key_still_rejected(self, monkeypatch):
        # Non-régression : seule la requête OPTIONS est exemptée, pas
        # les vraies requêtes (GET/POST) qui doivent rester protégées.
        client = _reload_app_with_env(monkeypatch, "secret123")
        response = client.get("/health")
        assert response.status_code == 403


class TestCorsAllowedOrigins:
    def test_default_origin_is_localhost_frontend(self, monkeypatch):
        monkeypatch.delenv("ALLOWED_ORIGINS", raising=False)
        client = _reload_app_with_env(monkeypatch, None)
        response = client.get("/health", headers={"Origin": "http://localhost:5173"})
        assert response.headers.get("access-control-allow-origin") == "http://localhost:5173"

    def test_allowed_origins_configurable_via_env(self, monkeypatch):
        monkeypatch.setenv("ALLOWED_ORIGINS", "https://mon-app.vercel.app,http://localhost:5173")
        client = _reload_app_with_env(monkeypatch, None)
        response = client.get("/health", headers={"Origin": "https://mon-app.vercel.app"})
        assert response.headers.get("access-control-allow-origin") == "https://mon-app.vercel.app"
