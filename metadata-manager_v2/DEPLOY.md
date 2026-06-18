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
- Homepage URL: `https://editor.example.com`
- Authorization callback URL: `https://editor.example.com/auth/github/callback`
Note the Client ID + secret.

## 2. Lightsail instance
- Create an Ubuntu 22.04 instance; attach a static IP; open ports 80 and 443.
- Point your domain's A record at the static IP.

## 3. Install + deploy
```bash
sudo apt update && sudo apt install -y nginx git python3-venv
sudo useradd --system --create-home --home-dir /opt/ari ariapp

# clone the repo and check out the tracked branch
sudo -u ariapp git clone https://github.com/KrishnaTO/ARI.git /opt/ari/repo
cd /opt/ari/repo && sudo -u ariapp git checkout feature/metadata-manager_v2/ARI

# python env
sudo -u ariapp python3 -m venv /opt/ari/venv
sudo -u ariapp /opt/ari/venv/bin/pip install -r metadata-manager_v2/requirements.txt

# config (secrets server-side only)
cd metadata-manager_v2
sudo -u ariapp cp .env.example .env
sudo -u ariapp nano .env     # client id/secret; APP_BASE_URL=https://editor.example.com; SESSION_SECRET=$(openssl rand -hex 32)
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

sudo cp nginx.conf /etc/nginx/sites-available/ari-mm   # edit server_name
sudo ln -s /etc/nginx/sites-available/ari-mm /etc/nginx/sites-enabled/
sudo nginx -t && sudo systemctl reload nginx
sudo apt install -y certbot python3-certbot-nginx
sudo certbot --nginx -d editor.example.com
```

## 5. Verify
- `https://editor.example.com` loads; `/api/v2/me` shows `github_enabled: true`.
- Sign in, edit a disease, Publish → PR opens on `edit/<you>/<disease-slug>-<ts>`
  against `GITHUB_BASE_BRANCH`, authored by you.
- After a branch update merges, the timer pulls it and the app reflects it within ~10 min
  (or run `deploy/update.sh` to refresh immediately).

## Hardening
- `.env` is `chmod 600`, git-ignored, never web-served (nginx denies dotfiles).
- App bound to `127.0.0.1:8001`; only nginx is public; HTTPS enforced.
- GitHub token is held server-side (session holds only an opaque id); never sent to the browser.
- Set `ALLOWED_LOGINS` to restrict who may publish.
