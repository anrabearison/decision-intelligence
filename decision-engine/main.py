"""
decision-engine - façade FastAPI sur decision-core.

Rôle strict : recevoir un fichier, appeler le moteur, retourner le
résultat. Aucune notion d'utilisateur, d'organisation ou de
persistance ici (cf. SPEC.md section 3) - c'est le rôle de NestJS
à partir de la Phase 5.

Sécurité : si INTERNAL_API_KEY est définie dans l'environnement, toute
requête doit fournir le header X-Internal-Key correspondant (Phase 5,
quand ce service devient interne, appelé uniquement par NestJS).
En Phase 2 (pas de NestJS), la variable n'est pas définie : le service
reste ouvert, appelé directement par le frontend.
"""
import logging
import os
import tempfile
from typing import Optional

from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

from decision_core.importer import UnsupportedFileFormatError, import_file
from decision_core.report import generate_report

logger = logging.getLogger("decision-engine")

MAX_FILE_SIZE_MB = 50
MAX_FILE_SIZE_BYTES = MAX_FILE_SIZE_MB * 1024 * 1024

# Erreurs "données du client" : tout ce que decision-core peut lever pour
# un problème imputable à l'input (fichier vide/corrompu, colonne absente,
# colonne du mauvais type, échantillon insuffisant...). Un audit exhaustif
# a montré que lister les exceptions typées une par une (InsufficientDataError,
# UnsupportedFileFormatError...) est structurellement insuffisant : pandas
# lève aussi EmptyDataError/ParserError (sous-classes de ValueError), et
# une simulation sur une colonne inexistante ou catégorielle lève KeyError/
# TypeError, jamais anticipés individuellement. D'où cette liste large de
# classes de base plutôt qu'une liste d'exceptions spécifiques à maintenir
# indéfiniment - complétée par un filet de sécurité générique ci-dessous
# pour tout ce qui n'aurait pas été anticipé.
CLIENT_DATA_ERRORS = (ValueError, TypeError, KeyError, UnsupportedFileFormatError)


def _format_client_error(exc: Exception) -> str:
    if isinstance(exc, KeyError):
        # str(KeyError('X')) vaut "'X'" (guillemets superflus, peu clair) -
        # reformulé pour rester compréhensible côté client.
        return f"Colonne introuvable : {exc}. Vérifiez le nom de la colonne."
    return str(exc)


app = FastAPI(title="decision-engine", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],  # Autorise le frontend React/Vite
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


async def handle_client_data_error(request: Request, exc: Exception):
    return JSONResponse(status_code=400, content={"detail": _format_client_error(exc)})


async def generic_error_handler(request: Request, exc: Exception):
    # Filet de sécurité générique : tout ce qui n'est pas une erreur de
    # données du client (donc probablement un bug imprévu côté serveur)
    # reste un 500, volontairement générique - jamais de détails internes
    # exposés au client, mais journalisé côté serveur pour le débogage.
    logger.exception("Erreur non anticipée dans decision-engine")
    return JSONResponse(status_code=500, content={"detail": "Une erreur interne est survenue."})


for _error_type in CLIENT_DATA_ERRORS:
    app.add_exception_handler(_error_type, handle_client_data_error)
app.add_exception_handler(Exception, generic_error_handler)


@app.middleware("http")
async def verify_internal_key(request: Request, call_next):
    expected_key = os.environ.get("INTERNAL_API_KEY")
    if expected_key:
        provided_key = request.headers.get("X-Internal-Key")
        if provided_key != expected_key:
            return JSONResponse(status_code=403, content={"error": "forbidden"})
    return await call_next(request)


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.post("/engine/analyze")
async def analyze(
    file: UploadFile = File(...),
    target: str | None = Form(None),
    feature: str | None = Form(None),
    change_pct: float | None = Form(None),
):
    content = await file.read()
    if len(content) > MAX_FILE_SIZE_BYTES:
        raise HTTPException(
            status_code=413,
            detail=f"Fichier trop volumineux (max {MAX_FILE_SIZE_MB} Mo).",
        )

    suffix = os.path.splitext(file.filename or "")[1] or ".csv"
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        tmp.write(content)
        tmp_path = tmp.name

    try:
        df = import_file(tmp_path)
    finally:
        os.remove(tmp_path)

    simulation_config = None
    if target and feature and change_pct is not None:
        simulation_config = {
            "target": target,
            "feature": feature,
            "change_pct": change_pct,
        }

    report = generate_report(df, simulation_config=simulation_config)
    return report
