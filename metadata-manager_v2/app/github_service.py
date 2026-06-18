"""Per-user GitHub integration for the Metadata Manager.

Each editor signs in with their own GitHub account; their access token is held
server-side only (in the session) and used to commit the edited ontology file
on a new branch — named after the disease — and open a pull request. Commits
are therefore attributed to the editor on GitHub. The only persistent secret is
the OAuth App client secret, which never leaves the server.
"""
import base64
import re
import time
import httpx

GH = "https://github.com"
API = "https://api.github.com"


def slugify(text: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", (text or "").lower()).strip("-")
    return (s or "disease")[:60]


def authorize_url(client_id: str, redirect_uri: str, state: str) -> str:
    from urllib.parse import urlencode
    return f"{GH}/login/oauth/authorize?" + urlencode({
        "client_id": client_id, "redirect_uri": redirect_uri,
        "scope": "repo user:email", "state": state, "allow_signup": "false",
    })


async def exchange_code(client_id: str, client_secret: str, code: str, redirect_uri: str) -> str:
    async with httpx.AsyncClient(timeout=20) as c:
        r = await c.post(f"{GH}/login/oauth/access_token",
                         headers={"Accept": "application/json"},
                         json={"client_id": client_id, "client_secret": client_secret,
                               "code": code, "redirect_uri": redirect_uri})
    data = r.json()
    if "access_token" not in data:
        raise ValueError(f"OAuth token exchange failed: {data}")
    return data["access_token"]


def _headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json"}


async def get_identity(token: str) -> dict:
    async with httpx.AsyncClient(timeout=20, headers=_headers(token)) as c:
        user = (await c.get(f"{API}/user")).json()
        email = user.get("email")
        try:
            emails = (await c.get(f"{API}/user/emails")).json()
            verified = [e for e in emails if e.get("verified")]
            primary = next((e for e in verified if e.get("primary")), verified[0] if verified else None)
            if primary:
                email = primary["email"]
        except Exception:
            pass
    if not email:
        email = f"{user['id']}+{user['login']}@users.noreply.github.com"
    return {"login": user["login"], "name": user.get("name") or user["login"],
            "email": email, "avatar": user.get("avatar_url", "")}


async def publish_file(*, token: str, owner: str, repo: str, base_branch: str,
                       path: str, content_bytes: bytes, disease_name: str,
                       message: str, identity: dict) -> dict:
    """Commit content_bytes to `path` on a new disease-named branch, open a PR."""
    branch = f"edit/{identity['login']}/{slugify(disease_name)}-{int(time.time())}"
    async with httpx.AsyncClient(timeout=30, headers=_headers(token)) as c:
        base = (await c.get(f"{API}/repos/{owner}/{repo}/git/ref/heads/{base_branch}")).json()
        if "object" not in base:
            raise ValueError(f"Base branch '{base_branch}' not found: {base.get('message')}")
        base_sha = base["object"]["sha"]

        r = await c.post(f"{API}/repos/{owner}/{repo}/git/refs",
                         json={"ref": f"refs/heads/{branch}", "sha": base_sha})
        if r.status_code >= 300:
            raise ValueError(f"Could not create branch: {r.json().get('message')}")

        # current file sha on the base branch (needed to update an existing file)
        cur = await c.get(f"{API}/repos/{owner}/{repo}/contents/{path}", params={"ref": base_branch})
        sha = cur.json().get("sha") if cur.status_code == 200 else None

        put = await c.put(f"{API}/repos/{owner}/{repo}/contents/{path}", json={
            "message": message or f"Update {disease_name}",
            "content": base64.b64encode(content_bytes).decode(),
            "branch": branch, "sha": sha,
            "author": {"name": identity["name"], "email": identity["email"]},
            "committer": {"name": identity["name"], "email": identity["email"]},
        })
        if put.status_code >= 300:
            raise ValueError(f"Commit failed: {put.json().get('message')}")

        pr = await c.post(f"{API}/repos/{owner}/{repo}/pulls", json={
            "title": message or f"Edit {disease_name}",
            "head": branch, "base": base_branch,
            "body": f"Edit to **{disease_name}** submitted via the ARI Metadata Manager by @{identity['login']}.",
        })
        if pr.status_code >= 300:
            raise ValueError(f"PR creation failed: {pr.json().get('message')}")
        prj = pr.json()
    return {"branch": branch, "pr_number": prj["number"], "pr_url": prj["html_url"]}
