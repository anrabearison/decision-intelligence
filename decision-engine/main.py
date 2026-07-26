"""
decision-engine - façade FastAPI sur decision-core.

Rôle strict : recevoir un fichier, appeler le moteur, retourner le
résultat. Aucune notion d'utilisateur, d'organisation ou de
persistance ici (cf. ARCHITECTURE.md) - c'est le rôle de NestJS
à partir de la Phase 5.

Sécurité : si INTERNAL_API_KEY est définie dans l'environnement, toute
requête doit fournir le header X-Internal-Key correspondant (Phase 5,
quand ce service devient interne, appelé uniquement par NestJS).
En Phase 2 (pas de NestJS), la variable n'est pas définie : le service
reste ouvert, appelé directement par le frontend.
"""
import os
import tempfile

from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import JSONResponse

from decision_core.importer import UnsupportedFileFormatError, import_file
from decision_core.report import generate_report

MAX_FILE_SIZE_MB = 50
MAX_FILE_SIZE_BYTES = MAX_FILE_SIZE_MB * 1024 * 1024

app = FastAPI(title="decision-engine", version="0.1.0")


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
    except UnsupportedFileFormatError as e:
        raise HTTPException(status_code=400, detail=str(e))
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
