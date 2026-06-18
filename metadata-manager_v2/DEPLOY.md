# Deploying the ARI Metadata Manager on AWS Lightsail

FastAPI app (uvicorn) behind nginx with TLS, kept in sync with a GitHub branch.
Editors sign in with their own GitHub account; edits open PRs under their identity.

## Which version the app shows
The app populates from, and opens edit PRs against, the branch in
`GITHUB_BASE_BRANCH` (the "setting"). Default: `feature/metadata-manager_v2/ARI`.
A systemd timer pulls that branch every few minutes and restarts the app, so the
**latest version of the branch always populates**. Point it at a different branch
by changing `GITHUB_BASE_BRANCH` in `.env` (then `systemctl restart ari-mm`).

Releases are handled on GitHub (there is no in-app Admin/release dialog).

## 1. GitHub OAuth App
GitHub → Settings → Developer settings → OAuth Apps → New OAuth App.
This deployment uses the bare Lightsail IP over **HTTP** (no domain/TLS), so use
the public IP in both URLs (replace `IP` with your instance's static IP):
- Homepage URL: `http://IP`
- Authorization callback URL: `http://IP/auth/github/callback`
Note the Client ID + secret.

> Running without TLS is insecure — see "Security: running over HTTP" at the
> bottom before exposing this beyond a trusted network.

## 2. Lightsail instance

> Prerequisite: push the branch to GitHub first (`git push origin feature/metadata-manager_v2/ARI`)
> and choose a plan with **>= 1 GB RAM** (or rely on the swap step below).
- Create an Ubuntu 22.04 instance; attach a **static IP**; open **port 80** in the
  Lightsail firewall (no 443 needed without TLS). No domain required.
- Point your domain's A record at the static IP.

## 3. Install + deploy
```bash
sudo apt update && sudo apt install -y nginx git python3-venv
sudo useradd --system --create-home --home-dir /opt/ari --shell /usr/sbin/nologin ariapp
# make the app dir traversable so you can inspect it as your own user
sudo chmod 755 /opt/ari
# to run commands AS the service user (its shell is nologin):
#   sudo -u ariapp bash    # then cd /opt/ari/repo, git, etc.

# clone the repo and check out the tracked branch
sudo -u ariapp git clone https://github.com/KrishnaTO/ARI.git /opt/ari/repo
cd /opt/ari/repo && sudo -u ariapp git checkout feature/metadata-manager_v2/ARI
# the checkout (and everything git touches) must be owned by the service user,
# or `sudo -u ariapp git ...` and the auto-update timer get Permission denied:
sudo chown -R ariapp:ariapp /opt/ari

# add swap FIRST on small instances — owlready2 compiles from source and is
# OOM-killed (pip exits with code -9) on <2 GB RAM without swap:
if ! sudo swapon --show | grep -q /swapfile; then
  sudo fallocate -l 2G /swapfile && sudo chmod 600 /swapfile
  sudo mkswap /swapfile && sudo swapon /swapfile
  echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
fi

# python env (--no-cache-dir keeps peak memory down)
sudo -u ariapp python3 -m venv /opt/ari/venv
sudo -u ariapp /opt/ari/venv/bin/pip install --no-cache-dir -r metadata-manager_v2/requirements.txt

# config (secrets server-side only)
cd metadata-manager_v2
sudo -u ariapp cp .env.example .env
sudo -u ariapp nano .env     # client id/secret; APP_BASE_URL=http://IP ; SESSION_SECRET=$(openssl rand -hex 32)
# (APP_BASE_URL must be http://<your static IP> so the OAuth redirect + cookie match)
sudo chmod 600 .env
```

## 4. Service + auto-update + TLS
```bash
cd /opt/ari/repo/metadata-manager_v2/deploy
sudo cp ari-mm.service ari-mm-update.service ari-mm-update.timer /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now ari-mm           # runs uvicorn on 127.0.0.1:8001
sudo systemctl enable --now ari-mm-update.timer   # pulls the branch every 10 min

# allow the app user to restart the service from update.sh
echo 'ariapp ALL=(root) NOPASSWD: /bin/systemctl restart ari-mm' | sudo tee /etc/sudoers.d/ari-mm

sudo cp nginx.conf /etc/nginx/sites-available/ari-mm   # HTTP-only, server_name _
sudo ln -sf /etc/nginx/sites-available/ari-mm /etc/nginx/sites-enabled/ari-mm
sudo rm -f /etc/nginx/sites-enabled/default
sudo nginx -t && sudo systemctl reload nginx
# No certbot / no TLS: the app is served at  http://<your static IP>
# When you later get a domain, point its A record here and run:
#   sudo apt install -y certbot python3-certbot-nginx && sudo certbot --nginx -d YOUR_DOMAIN
```

## 5. Verify
- `http://<your static IP>` loads; `/api/v2/me` shows `github_enabled: true`.
- Sign in, edit a disease, Publish → PR opens on `edit/<you>/<disease-slug>-<ts>`
  against `GITHUB_BASE_BRANCH`, authored by you.
- After a branch update merges, the timer pulls it and the app reflects it within ~10 min
  (or run `deploy/update.sh` to refresh immediately).

## Hardening
- `.env` is `chmod 600`, git-ignored, never web-served (nginx denies dotfiles).
- App bound to `127.0.0.1:8001`; only nginx is public; HTTPS enforced.
- GitHub token is held server-side (session holds only an opaque id); never sent to the browser.
- Set `ALLOWED_LOGINS` to restrict who may publish.

## Troubleshooting

**`cd /opt/ari/repo` → Permission denied.** The repo is owned by the `ariapp`
service user and `/opt/ari` is that user's home, so your login user can't enter it.
Either make it traversable:
```bash
sudo chmod 755 /opt/ari
```
or operate as the service user:
```bash
sudo -u ariapp bash
cd /opt/ari/repo
```
Never `chown` the tree to your personal user — the service runs as `ariapp` and
its `.env`/checkout must stay owned by `ariapp` (with `.env` at `chmod 600`).

**`git pull` / update.sh fails with "dubious ownership".** If you ran any git
command as the wrong user, mark the path safe for the service user:
```bash
sudo -u ariapp git config --global --add safe.directory /opt/ari/repo
```

## Security: running over HTTP (no TLS)

Serving over a bare IP means all browser <-> server traffic is **unencrypted**.
The GitHub *access token* still stays server-side (it's never sent to the browser),
but the risks that remain are real:

- **Session-cookie theft = acting as you on GitHub.** Login is tracked by a
  session cookie that maps to your server-side GitHub token. Over HTTP that
  cookie crosses the network in clear text and (because the site isn't HTTPS) is
  not marked `Secure`. Anyone who can sniff the connection (shared Wi-Fi, an
  upstream network hop) can copy it and publish commits/PRs to the repo **as you**.
- **OAuth code interception.** The `?code=...` returned by GitHub travels over
  HTTP on the way back to the app. It's single-use and short-lived, but on an
  open network it can be grabbed and replayed before you use it.
- **No server authentication / MITM.** Users can't verify they're talking to the
  real instance; a man-in-the-middle could impersonate it, harvest the OAuth
  flow, or alter responses. The server->GitHub API calls themselves are HTTPS, so
  only the browser<->server leg is exposed.
- **Credentials in the open.** Anything typed into the page (commit messages,
  etc.) is visible in transit.

Mitigations while on HTTP (treat this as a private preview, not public):
- Lock the Lightsail firewall to **your own IP(s)** only.
- Set `ALLOWED_LOGINS` in `.env` so only named GitHub users can publish.
- Use a fine-grained GitHub OAuth App scope and rotate the client secret if exposed.
- Prefer reaching it over an **SSH tunnel** (`ssh -L 8001:127.0.0.1:8001 ...`) instead
  of opening port 80 publicly.
- Move to a domain + free TLS (certbot or Cloudflare) before any real/multi-user use —
  it's a 2-minute `certbot --nginx` step once a domain points at the IP.
