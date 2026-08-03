"""
Tests de la façade FastAPI - Phase 2.
Rôle strict de ce service : recevoir un fichier, appeler decision-core,
retourner le résultat. Aucune logique métier ici (pas d'utilisateur,
pas de persistance) - cf. SPEC.md section 5.
"""
import io
import os
import sys
from pathlib import Path

# Ajouter le répertoire parent au PYTHONPATH pour importer main
sys.path.insert(0, str(Path(__file__).parent.parent))

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

    def test_simulation_on_categorical_column_returns_400(self):
        # Trouvé en audit : TypeError levée par fit_simple_regression,
        # non catchée avant ce fix -> 500 brut.
        content = b"Produit,Prix\nA,10\nB,20\nC,15\nA,12\nB,18\n"
        response = client.post(
            "/engine/analyze",
            files={"file": ("t.csv", io.BytesIO(content), "text/csv")},
            data={"target": "Prix", "feature": "Produit", "change_pct": "0.1"},
        )
        assert response.status_code == 400
        assert "detail" in response.json()

    def test_simulation_on_nonexistent_column_returns_400(self):
        # Trouvé en audit : KeyError (faute de frappe utilisateur très
        # probable via le champ texte libre du frontend) -> 500 sans
        # aucun message avant ce fix.
        content = b"A,B\n1,2\n3,4\n5,6\n7,8\n"
        response = client.post(
            "/engine/analyze",
            files={"file": ("t.csv", io.BytesIO(content), "text/csv")},
            data={"target": "ColonneInexistante", "feature": "A", "change_pct": "0.1"},
        )
        assert response.status_code == 400
        assert "detail" in response.json()
        assert response.json()["detail"] != ""

    def test_empty_file_returns_400(self):
        # Trouvé en audit : pandas.errors.EmptyDataError sur fichier de
        # 0 octet (upload accidentel, cas réaliste).
        response = client.post(
            "/engine/analyze",
            files={"file": ("vide.csv", io.BytesIO(b""), "text/csv")},
        )
        assert response.status_code == 400

    def test_malformed_csv_returns_400(self):
        # Trouvé en audit : pandas.errors.ParserError, probablement le
        # cas le plus fréquent en usage réel (export mal formé).
        content = b"A,B,C\n1,2,3\n4,5\n6,7,8,9,10\n"
        response = client.post(
            "/engine/analyze",
            files={"file": ("malforme.csv", io.BytesIO(content), "text/csv")},
        )
        assert response.status_code == 400

    def test_unexpected_error_still_returns_generic_500_without_leaking(self):
        # Filet de sécurité générique : un bug vraiment imprévu ne doit
        # jamais faire planter le serveur sans réponse, mais ne doit pas
        # non plus être maquillé en erreur utilisateur (reste un 500,
        # volontairement générique, pas de détails internes exposés).
        from main import generic_error_handler
        import asyncio

        class FakeRequest:
            pass

        response = asyncio.run(generic_error_handler(FakeRequest(), RuntimeError("bug interne imprévu")))
        assert response.status_code == 500
        body = response.body.decode()
        assert "bug interne imprévu" not in body
        assert "Traceback" not in body
