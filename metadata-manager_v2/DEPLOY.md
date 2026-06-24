# Deploying the ARI Metadata Manager on AWS Lightsail

FastAPI app (uvicorn) behind nginx with **Cloudflare Free SSL**, served at `https://aurint.ca/ari-editor`.
Editors sign in with their own GitHub account; edits open PRs under their identity.

**HTTPS cost: $0** — Cloudflare's free plan handles SSL/TLS.
Domain registration (`aurint.ca`) is the only cost.

## Architecture
```
Browser ──HTTPS──→ Cloudflare (TLS termination) ──HTTPS──→ Lightsail nginx ──HTTP──→ uvicorn :8001
  aurint.ca/ari-editor         ↑                                     ↑
                     Free SSL (Full Strict)             Origin Certificate (free, from Cloudflare)
```

Nginx strips the `/ari-editor` prefix so FastAPI sees root-relative paths (`/api/v2/...`).
The frontend JS auto-detects the prefix from the URL and prepends it to API calls.

## 1. Cloudflare setup
1. Sign up for a free Cloudflare account at https://dash.cloudflare.com
2. Add your domain (`aurint.ca`) → Cloudflare scans existing DNS records
3. In DNS settings, create an **A record** pointing `@` and `www` to your Lightsail static IP
   - Proxy status: **Proxied** (orange cloud) — required for SSL
4. In **SSL/TLS → Overview**: set to **Full (Strict)**
5. In **SSL/TLS → Origin Server**: click **Create Certificate**
   - Leave default (RSA 2048, 15 years)
   - Copy the **Origin Certificate** → save to `/etc/ssl/certs/aurint.ca.pem`
   - Copy the **Private Key** → save to `/etc/ssl/private/aurint.ca.key`
   - These files go on your Lightsail instance (step 4 below)

## 2. GitHub OAuth App
GitHub → Settings → Developer settings → OAuth Apps → New OAuth App.
- Homepage URL: `https://aurint.ca/ari-editor`
- Authorization callback URL: `https://aurint.ca/ari-editor/auth/github/callback`
Note the Client ID + secret.

## 3. Lightsail instance
- Create an Ubuntu 22.04 instance; attach a static IP; open ports 80 and 443.
- Update Cloudflare DNS to point `aurint.ca` at the static IP.

## 4. Install + deploy
```bash
sudo apt update && sudo apt install -y nginx git python3-venv
sudo useradd --system --create-home --home-dir /opt/ari ariapp

# Install the Cloudflare Origin Certificate (paste the cert + key you saved in step 1.5)
sudo tee /etc/ssl/certs/aurint.ca.pem << 'EOF'
# Paste the -----BEGIN CERTIFICATE----- content here
EOF

sudo tee /etc/ssl/private/aurint.ca.key << 'EOF'
# Paste the -----BEGIN RSA PRIVATE KEY----- content here
EOF

sudo chmod 644 /etc/ssl/certs/aurint.ca.pem
sudo chmod 600 /etc/ssl/private/aurint.ca.key

# clone the repo and check out the tracked branch
sudo -u ariapp git clone https://github.com/KrishnaTO/ARI.git /opt/ari/repo
cd /opt/ari/repo && sudo -u ariapp git checkout feature/metadata-manager_v2/ARI

# python env (may need swapfile for owlready2 build — see Troubleshooting)
sudo -u ariapp python3 -m venv /opt/ari/venv
sudo -u ariapp /opt/ari/venv/bin/pip install --no-cache-dir -r metadata-manager_v2/requirements.txt

# config (secrets server-side only)
cd metadata-manager_v2
sudo -u ariapp cp .env.example .env
sudo -u ariapp nano .env     # fill in GITHUB_CLIENT_ID, GITHUB_CLIENT_SECRET, SESSION_SECRET
# APP_BASE_URL is already set to https://aurint.ca/ari-editor
sudo chmod 600 .env
```

## 5. Service + auto-update
```bash
cd /opt/ari/repo/metadata-manager_v2/deploy
sudo cp ari-mm.service ari-mm-update.service ari-mm-update.timer /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now ari-mm           # runs uvicorn on 127.0.0.1:8001
sudo systemctl enable --now ari-mm-update.timer   # pulls the branch every 10 min

# allow the app user to restart the service from update.sh
echo 'ariapp ALL=(root) NOPASSWD: /bin/systemctl restart ari-mm' | sudo tee /etc/sudoers.d/ari-mm
```

## 6. Nginx
```bash
cd /opt/ari/repo/metadata-manager_v2/deploy
sudo cp nginx.conf /etc/nginx/sites-available/ari-mm
sudo ln -s /etc/nginx/sites-available/ari-mm /etc/nginx/sites-enabled/
# Remove the default site if it conflicts
sudo rm -f /etc/nginx/sites-enabled/default
sudo nginx -t && sudo systemctl reload nginx
```

## 7. Change nameservers
In Cloudflare dashboard, note the nameservers Cloudflare assigned (e.g., `dahlia.ns.cloudflare.com`, `tegan.ns.cloudflare.com`).
At your domain registrar, change the nameservers to Cloudflare's.
Propagation takes a few minutes to a couple hours.

## 8. Restart app
```bash
sudo systemctl restart ari-mm
```

## 9. Verify
- `https://aurint.ca/ari-editor` loads with a valid Cloudflare-issued SSL certificate ✅
- `/api/v2/me` shows `github_enabled: true`
- Sign in, edit a disease, Publish → PR opens on `edit/<you>/<disease-slug>-<ts>`
  against `GITHUB_BASE_BRANCH`, authored by you.
- After a branch update merges, the timer pulls it and the app reflects it within ~10 min
  (or run `deploy/update.sh` to refresh immediately).

## How the subpath works
- **nginx** (`deploy/nginx.conf`): the `location /ari-editor/` block strips the prefix via
  `rewrite ^/ari-editor(/.*)$ $1 break;` and sets `X-Script-Name: /ari-editor`.
- **Frontend JS** (`static/js/core.js`): `BASE_PATH` auto-detects the `/ari-editor` prefix
  from the page URL and prepends it to all API calls via the `api()` function.
- **GitHub OAuth redirect** (`static/js/github.js`): Sign-in link uses `BASE_PATH + '/auth/github'`.
- **`.env`**: `APP_BASE_URL` includes the subpath so the OAuth callback URI is correct.

## Troubleshooting

### `git config --global --add safe.directory '*'` (or /opt/ari/repo)
If git complains "dubious ownership", the repo is owned by a different user.
```bash
sudo git config --global --add safe.directory /opt/ari/repo
```

### Permission errors
```bash
sudo chown -R ariapp:ariapp /opt/ari
```

### owlready2 pip build is OOM-killed
```bash
sudo fallocate -l 2G /swapfile && sudo chmod 600 /swapfile && sudo mkswap /swapfile && sudo swapon /swapfile
echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
```
Then re-run `pip install --no-cache-dir -r metadata-manager_v2/requirements.txt`

### .git lock files / corruption
Close other git clients (GitHub Desktop, VS Code) that may be holding locks on the
shared Windows mount. If corrupt, from the repo root:
```bash
rm -f .git/index.lock .git/HEAD.lock
git reset --hard HEAD
```

### 502 Bad Gateway
The uvicorn process may not be running. Check with:
```bash
sudo systemctl status ari-mm
sudo journalctl -u ari-mm -n 20
```

### Cloudflare "SSL is not working on this site"
- Wait for DNS propagation (can take hours)
- Verify Origin Certificate is correctly installed on Lightsail
- Check nginx config syntax: `sudo nginx -t`

### App loads but API calls fail (404)
If the frontend loads but data doesn't appear, check the browser's developer tools
network tab:
- API calls should go to `https://aurint.ca/ari-editor/api/v2/...`
- If they go to `https://aurint.ca/api/v2/...`, `BASE_PATH` is not being detected.
  You can set it explicitly by adding this to `static/index.html` before `core.js`:
  `<script>window.BASE_PATH='/ari-editor';</script>`

## Security
- `.env` is `chmod 600`, git-ignored, never web-served (nginx denies dotfiles).
- App bound to `127.0.0.1:8001`; only nginx is public; HTTPS via Cloudflare.
- GitHub token is held server-side (session holds only an opaque id); never sent to the browser.
- Set `ALLOWED_LOGINS` to restrict who may publish.