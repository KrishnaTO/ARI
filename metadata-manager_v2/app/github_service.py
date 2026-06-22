"""Per-user GitHub integration for the Metadata Manager.

Each editor signs in with their own GitHub account; their access token is held
server-side only (in the session) and used to commit the edited ontology file
on a new branch — named after the disease — and open a pull request. Commits
are therefore attributed to the editor on GitHub. The only persistent secret is
the OAuth App client secret, which never leaves the server.
"""
import asyncio
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


async def publish_file(*, token: str, owner: str, repo: str, base_branch: str, pr_body: str = "",
                       extra_files: dict = None, path: str, content_bytes: bytes,
                       disease_name: str, message: str, identity: dict,
                       reuse_branch: str = None, labels: list = None) -> dict:
    """Commit content_bytes (+ extra_files) to a branch and open/update a PR.

    Collaborators with push access commit a branch directly in the upstream repo.
    Outside contributors (no push access) get their own fork created automatically;
    the branch + commits go onto their fork and a cross-repo PR is opened upstream.
    If reuse_branch exists, further changes append to the same branch/PR.
    """
    labels = labels or ["edit term"]
    label_colors = {"edit term": "0e8a16", "sssom": "5319e7"}

    def _author():
        return {"name": identity["name"], "email": identity["email"]}

    async with httpx.AsyncClient(timeout=30, headers=_headers(token)) as c:
        # Where can this user push? Upstream if collaborator, else their fork.
        info = await c.get(f"{API}/repos/{owner}/{repo}")
        can_push = bool(info.json().get("permissions", {}).get("push")) if info.status_code == 200 else False

        if can_push:
            c_owner, c_repo = owner, repo
        else:
            login = identity["login"]
            fk = await c.get(f"{API}/repos/{login}/{repo}")
            if fk.status_code == 404:
                cr = await c.post(f"{API}/repos/{owner}/{repo}/forks")
                if cr.status_code >= 300:
                    raise ValueError(f"Could not fork {owner}/{repo}: {cr.json().get('message')}")
                for _ in range(15):                       # forks are async; wait for it
                    await asyncio.sleep(2)
                    fk = await c.get(f"{API}/repos/{login}/{repo}")
                    if fk.status_code == 200:
                        break
                else:
                    raise ValueError("Your fork is still being created — try publishing again in a moment.")
            fj = fk.json()
            c_owner, c_repo = fj["owner"]["login"], fj["name"]

        # Base sha always comes from UPSTREAM so the branch is current even on a stale fork.
        base = (await c.get(f"{API}/repos/{owner}/{repo}/git/ref/heads/{base_branch}")).json()
        if "object" not in base:
            raise ValueError(f"Base branch '{base_branch}' not found: {base.get('message')}")
        base_sha = base["object"]["sha"]

        branch = None
        if reuse_branch:
            ref = await c.get(f"{API}/repos/{c_owner}/{c_repo}/git/ref/heads/{reuse_branch}")
            if ref.status_code == 200 and "object" in ref.json():
                branch = reuse_branch
        if not branch:
            branch = f"edit/{identity['login']}/{slugify(disease_name)}-{int(time.time())}"
            r = await c.post(f"{API}/repos/{c_owner}/{c_repo}/git/refs",
                             json={"ref": f"refs/heads/{branch}", "sha": base_sha})
            if r.status_code >= 300:
                raise ValueError(f"Could not create branch: {r.json().get('message')}")
        head_label = f"{c_owner}:{branch}"

        # commit the ontology (sha looked up on the branch in the commit repo)
        cur = await c.get(f"{API}/repos/{c_owner}/{c_repo}/contents/{path}", params={"ref": branch})
        sha = cur.json().get("sha") if cur.status_code == 200 else None
        put = await c.put(f"{API}/repos/{c_owner}/{c_repo}/contents/{path}", json={
            "message": message or f"Update {disease_name}",
            "content": base64.b64encode(content_bytes).decode(),
            "branch": branch, "sha": sha, "author": _author(), "committer": _author(),
        })
        if put.status_code >= 300 and not extra_files:
            raise ValueError(f"Commit failed: {put.json().get('message')}")

        for fpath, fbytes in (extra_files or {}).items():
            cf = await c.get(f"{API}/repos/{c_owner}/{c_repo}/contents/{fpath}", params={"ref": branch})
            fsha = cf.json().get("sha") if cf.status_code == 200 else None
            fput = await c.put(f"{API}/repos/{c_owner}/{c_repo}/contents/{fpath}", json={
                "message": f"Cross-reference mappings ({disease_name})",
                "content": base64.b64encode(fbytes).decode(),
                "branch": branch, "sha": fsha, "author": _author(), "committer": _author(),
            })
            if fput.status_code >= 300:
                raise ValueError(f"Mapping commit failed for {fpath}: {fput.json().get('message')}")

        # PR is always opened/looked up on UPSTREAM; head may be a fork (owner:branch)
        found = await c.get(f"{API}/repos/{owner}/{repo}/pulls",
                            params={"head": head_label, "state": "open"})
        prs = found.json() if found.status_code == 200 else []
        if prs:
            prj = prs[0]
            if message:
                await c.patch(f"{API}/repos/{owner}/{repo}/pulls/{prj['number']}", json={"title": message})
        else:
            pr = await c.post(f"{API}/repos/{owner}/{repo}/pulls", json={
                "title": message or f"Edit {disease_name}", "head": head_label, "base": base_branch,
                "maintainer_can_modify": True,
                "body": pr_body or f"Edit to **{disease_name}** by @{identity['login']}.",
            })
            if pr.status_code >= 300:
                raise ValueError(f"PR creation failed: {pr.json().get('message')}")
            prj = pr.json()

        # apply labels on the upstream PR (best effort; outside contributors can't label)
        try:
            for name in labels:
                await c.post(f"{API}/repos/{owner}/{repo}/labels",
                             json={"name": name, "color": label_colors.get(name, "ededed")})
            await c.post(f"{API}/repos/{owner}/{repo}/issues/{prj['number']}/labels",
                         json={"labels": labels})
        except Exception:
            pass
    return {"branch": branch, "pr_number": prj["number"], "pr_url": prj["html_url"], "fork": (not can_push)}


async def list_branches(token: str | None, owner: str, repo: str) -> list[str]:
    """All branch names in the repo (token optional for public repos)."""
    hdrs = {"Accept": "application/vnd.github+json"}
    if token:
        hdrs["Authorization"] = f"Bearer {token}"
    out, page = [], 1
    async with httpx.AsyncClient(timeout=20, headers=hdrs) as c:
        while True:
            r = await c.get(f"{API}/repos/{owner}/{repo}/branches",
                            params={"per_page": 100, "page": page})
            if r.status_code >= 300:
                raise ValueError(f"Could not list branches: {r.json().get('message')}")
            batch = r.json()
            out += [b["name"] for b in batch]
            if len(batch) < 100:
                break
            page += 1
    return out


async def get_file_at(token: str | None, owner: str, repo: str, path: str, ref: str) -> bytes:
    """Raw bytes of `path` on `ref` (token optional for public repos)."""
    hdrs = {"Accept": "application/vnd.github.raw+json"}
    if token:
        hdrs["Authorization"] = f"Bearer {token}"
    async with httpx.AsyncClient(timeout=30, headers=hdrs) as c:
        r = await c.get(f"{API}/repos/{owner}/{repo}/contents/{path}", params={"ref": ref})
        if r.status_code >= 300:
            raise ValueError(f"Could not fetch {path}@{ref}: {r.status_code} {r.text[:200]}")
        return r.content
