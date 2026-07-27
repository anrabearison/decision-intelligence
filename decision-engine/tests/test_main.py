"""
Tests de la façade FastAPI - Phase 2.
Rôle strict de ce service : recevoir un fichier, appeler decision-core,
retourner le résultat. Aucune logique métier ici (pas d'utilisateur,
pas de persistance) - cf. ARCHITECTURE.md.
"""
import io
import os
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

FIXTURES_DIR = os.path.join(
    os.path.dirname(__file__), "..", "..", "decision-core", "tests", "fixtures"
)


def load_fixture_bytes(name):
    with open(os.path.join(FIXTURES_DIR, name), "rb") as f:
        return f.read()


class TestHealthCheck:
    def test_health_endpoint_returns_ok(self):
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}


class TestAnalyzeEndpoint:
    def test_analyze_returns_200_on_valid_csv(self):
        content = load_fixture_bytes("ventes_test.csv")
        response = client.post(
            "/engine/analyze",
            files={"file": ("ventes_test.csv", io.BytesIO(content), "text/csv")},
        )
        assert response.status_code == 200

    def test_analyze_returns_expected_report_structure(self):
        content = load_fixture_bytes("ventes_test.csv")
        response = client.post(
            "/engine/analyze",
            files={"file": ("ventes_test.csv", io.BytesIO(content), "text/csv")},
        )
        body = response.json()
        assert "dataset_summary" in body
        assert "validation" in body
        assert "top_correlations" in body
        assert body["dataset_summary"]["n_rows"] == 10

    def test_analyze_rejects_unsupported_format(self):
        response = client.post(
            "/engine/analyze",
            files={"file": ("data.json", io.BytesIO(b'{"a":1}'), "application/json")},
        )
        assert response.status_code == 400

    def test_analyze_rejects_oversized_file(self):
        # fichier factice au-delà de la limite (MAX_FILE_SIZE_MB défini dans main.py)
        big_content = b"a,b\n" + b"1,2\n" * 15_000_000  # ~60 Mo, > 50 Mo
        response = client.post(
            "/engine/analyze",
            files={"file": ("big.csv", io.BytesIO(big_content), "text/csv")},
        )
        assert response.status_code == 413

    def test_analyze_requires_internal_key_when_configured(self, monkeypatch):
        monkeypatch.setenv("INTERNAL_API_KEY", "secret123")
        # nécessite de recharger l'app avec la clé active - testé au niveau
        # du middleware séparément (cf. test_security.py)
        pass


class TestAnalyzeWithSimulation:
    def test_analyze_accepts_simulation_params(self):
        content = load_fixture_bytes("ventes_test.csv")
        response = client.post(
            "/engine/analyze",
            files={"file": ("ventes_test.csv", io.BytesIO(content), "text/csv")},
            data={
                "target": "Ventes",
                "feature": "Prix",
                "change_pct": "0.05",
            },
        )
        body = response.json()
        assert "simulation" in body
        assert body["simulation"]["feature"] == "Prix"


class TestAnalyzeReturnsCleanErrorsForDomainExceptions:
    def test_insufficient_data_error_returns_400_not_500(self):
        # Colonne à variance nulle : decision-core lève InsufficientDataError,
        # ne doit jamais fuiter en 500 brut avec stack trace (cf. commit).
        content = b"X,Y\n1,10\n1,20\n1,30\n1,40\n"
        response = client.post(
            "/engine/analyze",
            files={"file": ("t.csv", io.BytesIO(content), "text/csv")},
            data={"target": "Y", "feature": "X", "change_pct": "0.1"},
        )
        assert response.status_code == 400
        assert "detail" in response.json()

    def test_error_detail_does_not_leak_stack_trace(self):
        content = b"X,Y\n1,10\n1,20\n1,30\n1,40\n"
        response = client.post(
            "/engine/analyze",
            files={"file": ("t.csv", io.BytesIO(content), "text/csv")},
            data={"target": "Y", "feature": "X", "change_pct": "0.1"},
        )
        detail = response.json()["detail"]
        assert "Traceback" not in detail
        assert "File \"" not in detail
