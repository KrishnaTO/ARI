"""FastAPI app for ARI Disease Metadata Manager v2."""
import os
from pathlib import Path

from fastapi import FastAPI, Request, Body
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from .ontology_service import OntologyService

ONTOLOGY_FILE = os.environ.get(
    "ARI_ONTOLOGY_FILE",
    str(Path(__file__).resolve().parent.parent / "ontologies" / "ari_t1d.owl")
)

service = OntologyService(ONTOLOGY_FILE)
app = FastAPI(title="ARI Metadata Manager v2")

STATIC_DIR = Path(__file__).resolve().parent.parent / "static"


@app.middleware("http")
async def no_cache_assets(request: Request, call_next):
    """Always revalidate the app's HTML/CSS/JS so edits are picked up on reload."""
    response = await call_next(request)
    path = request.url.path
    if path == "/" or path.endswith((".html", ".css", ".js")):
        response.headers["Cache-Control"] = "no-cache, must-revalidate"
    return response


@app.exception_handler(KeyError)
async def not_found(request: Request, exc: KeyError):
    return JSONResponse(status_code=404, content={"detail": str(exc.args[0])})


@app.get("/api/v2/overview")
async def overview():
    return service.overview()


@app.get("/api/v2/diseases")
async def diseases_list():
    return service.get_diseases_list()


@app.get("/api/v2/tree/alphabetical")
async def alphabetical_tree():
    return service.get_alphabetical_tree()


@app.get("/api/v2/tree/tissue")
async def tissue_tree():
    return service.get_tissue_hierarchy()


@app.get("/api/v2/symptoms")
async def symptoms_index():
    return service.get_symptoms_index()


@app.get("/api/v2/schema")
async def schema():
    """Field schema for editable disease-data item categories."""
    return service.get_schema()


@app.get("/api/v2/disease/{iri:path}")
async def disease_detail(iri: str):
    return service.get_disease_detail(iri)


@app.put("/api/v2/disease/{iri:path}")
async def update_disease(iri: str, payload: dict = Body(...)):
    """Edit disease fields. Body: {"changes": {...}, "editor": "name"}."""
    changes = payload.get("changes", payload)
    editor = payload.get("editor", "user")
    return service.update_disease(iri, changes, editor=editor)


@app.post("/api/v2/disease/{iri:path}/item")
async def add_item(iri: str, payload: dict = Body(...)):
    """Add a data item to a disease. Body: {category, values:{...}, editor}."""
    return service.add_item(iri, payload["category"], payload.get("values", {}),
                            editor=payload.get("editor", "user"))


@app.put("/api/v2/item/{iri:path}")
async def update_item(iri: str, payload: dict = Body(...)):
    """Edit a data item. Body: {category, changes:{...}, disease, editor}."""
    return service.update_item(iri, payload["category"], payload.get("changes", {}),
                               disease_iri=payload.get("disease", ""),
                               editor=payload.get("editor", "user"))


@app.delete("/api/v2/item/{iri:path}")
async def delete_item(iri: str, payload: dict = Body(...)):
    """Delete a data item. Body: {category, disease, editor}."""
    return service.delete_item(iri, payload.get("category", ""),
                               payload["disease"], editor=payload.get("editor", "user"))


@app.get("/api/v2/releases")
async def releases_list():
    return {"current": service._current_version(), "releases": service.list_releases()}


@app.post("/api/v2/releases")
async def create_release(payload: dict = Body(default={})):
    """Admin action: cut a versioned release snapshot of the ontology."""
    version = payload.get("version", "")
    notes = payload.get("notes", "")
    editor = payload.get("editor", "admin")
    return service.create_release(version=version, notes=notes, editor=editor)


@app.get("/api/v2/search")
async def search(q: str = ""):
    return service.search(q)


app.mount("/", StaticFiles(directory=STATIC_DIR, html=True), name="static")
