"""FastAPI app for ARI Disease Metadata Manager v2."""
import os
import secrets
from pathlib import Path

from fastapi import FastAPI, Request, Body
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware

from .ontology_service import OntologyService
from . import github_service as gh


def _load_dotenv():
    env = Path(__file__).resolve().parent.parent / ".env"
    if env.exists():
        for line in env.read_text().splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip())


_load_dotenv()

ONTOLOGY_FILE = os.environ.get(
    "ARI_ONTOLOGY_FILE",
    str(Path(__file__).resolve().parent.parent / "ontologies" / "ari_t1d.owl")
)

service = OntologyService(ONTOLOGY_FILE)
app = FastAPI(title="ARI Metadata Manager v2")

STATIC_DIR = Path(__file__).resolve().parent.parent / "static"

# ----------------------------------------------------------------- GitHub config
GH_CLIENT_ID = os.environ.get("GITHUB_CLIENT_ID", "")
GH_CLIENT_SECRET = os.environ.get("GITHUB_CLIENT_SECRET", "")
GH_OWNER = os.environ.get("GITHUB_OWNER", "")
GH_REPO = os.environ.get("GITHUB_REPO", "")
GH_BASE_BRANCH = os.environ.get("GITHUB_BASE_BRANCH", "feature/metadata-manager_v2/ARI")
GH_ONTOLOGY_PATH = os.environ.get(
    "GITHUB_ONTOLOGY_PATH", "metadata-manager_v2/ontologies/ari_t1d.owl")
APP_BASE_URL = os.environ.get("APP_BASE_URL", "http://localhost:8001").rstrip("/")
OAUTH_CALLBACK_PATH = os.environ.get("OAUTH_CALLBACK_PATH", "/auth/github/callback")
ALLOWED_LOGINS = [s.strip() for s in os.environ.get("ALLOWED_LOGINS", "").split(",") if s.strip()]
REDIRECT_URI = APP_BASE_URL + OAUTH_CALLBACK_PATH
GH_ENABLED = bool(GH_CLIENT_ID and GH_CLIENT_SECRET and GH_OWNER and GH_REPO)

# Tokens are kept SERVER-SIDE (the signed session cookie holds only an opaque id),
# so the GitHub access token never reaches the browser.
SESSIONS: dict[str, dict] = {}

app.add_middleware(
    SessionMiddleware,
    secret_key=os.environ.get("SESSION_SECRET", secrets.token_hex(32)),
    same_site="lax",
    https_only=APP_BASE_URL.startswith("https"),
)


def _user(request: Request):
    return SESSIONS.get(request.session.get("sid", ""))


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


@app.exception_handler(ValueError)
async def bad_request(request: Request, exc: ValueError):
    return JSONResponse(status_code=400, content={"detail": str(exc)})


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


# ----------------------------------------------------------------- FEEDBACK
@app.get("/api/v2/feedback")
async def feedback_list(disease: str = ""):
    return service.feedback.list(disease or None)


@app.post("/api/v2/feedback")
async def feedback_add(payload: dict = Body(...)):
    """Add feedback for a term. Body: {disease, term, message, keep, author}."""
    return service.feedback.add(
        payload.get("disease", ""), payload.get("term", ""), payload.get("message", ""),
        keep=payload.get("keep", False), author=payload.get("author", "anonymous"))


@app.put("/api/v2/feedback/{fid}")
async def feedback_update(fid: str, payload: dict = Body(...)):
    """Edit feedback. Body: {message?, keep?, author?}."""
    return service.feedback.update(fid, message=payload.get("message"),
                                   keep=payload.get("keep"), author=payload.get("author"))


@app.delete("/api/v2/feedback/{fid}")
async def feedback_delete(fid: str):
    return service.feedback.delete(fid)


# ----------------------------------------------------------------- GITHUB AUTH + PUBLISH
@app.get("/api/v2/me")
async def me(request: Request):
    if not GH_ENABLED:
        return {"github_enabled": False, "authenticated": False}
    u = _user(request)
    if not u:
        return {"github_enabled": True, "authenticated": False}
    i = u["identity"]
    return {"github_enabled": True, "authenticated": True,
            "login": i["login"], "name": i["name"], "avatar": i["avatar"],
            "repo": f"{GH_OWNER}/{GH_REPO}", "base_branch": GH_BASE_BRANCH}


@app.get("/auth/github")
async def auth_github(request: Request):
    if not GH_ENABLED:
        return JSONResponse(status_code=404, content={"detail": "GitHub integration not configured"})
    st = secrets.token_hex(16)
    request.session["oauth_state"] = st
    return RedirectResponse(gh.authorize_url(GH_CLIENT_ID, REDIRECT_URI, st))


@app.get(OAUTH_CALLBACK_PATH)
async def auth_callback(request: Request, code: str = "", state: str = ""):
    if not GH_ENABLED:
        return JSONResponse(status_code=404, content={"detail": "GitHub integration not configured"})
    if not code or state != request.session.get("oauth_state"):
        return JSONResponse(status_code=400, content={"detail": "Invalid OAuth state"})
    token = await gh.exchange_code(GH_CLIENT_ID, GH_CLIENT_SECRET, code, REDIRECT_URI)
    identity = await gh.get_identity(token)
    if ALLOWED_LOGINS and identity["login"] not in ALLOWED_LOGINS:
        return JSONResponse(status_code=403, content={"detail": f"@{identity['login']} is not allowed"})
    sid = secrets.token_urlsafe(24)
    SESSIONS[sid] = {"token": token, "identity": identity}
    request.session["sid"] = sid
    request.session.pop("oauth_state", None)
    return RedirectResponse("/")


@app.post("/api/v2/logout")
async def logout(request: Request):
    SESSIONS.pop(request.session.pop("sid", ""), None)
    return {"ok": True}


@app.post("/api/v2/publish")
async def publish(request: Request, payload: dict = Body(default={})):
    """Commit the current ontology file to GitHub as the signed-in user (PR)."""
    if not GH_ENABLED:
        raise ValueError("GitHub integration is not configured")
    u = _user(request)
    if not u:
        return JSONResponse(status_code=401, content={"detail": "Sign in with GitHub first"})
    disease = payload.get("disease") or "ontology"
    message = payload.get("message") or f"Update {disease}"
    content = Path(ONTOLOGY_FILE).read_bytes()
    return await gh.publish_file(
        token=u["token"], owner=GH_OWNER, repo=GH_REPO, base_branch=GH_BASE_BRANCH,
        path=GH_ONTOLOGY_PATH, content_bytes=content, disease_name=disease,
        message=message, identity=u["identity"])


app.mount("/", StaticFiles(directory=STATIC_DIR, html=True), name="static")
