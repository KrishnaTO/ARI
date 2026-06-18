// Per-user GitHub publish control. Talks to the backend (which holds the OAuth
// secret and the user's token server-side); no secrets are exposed here.
// Injects a sign-in / "Publish to GitHub" control into the header and publishes
// the current ontology as a PR on a branch named after the disease.
(function () {
  let ghUser = null;

  function el(html) { const t = document.createElement('template'); t.innerHTML = html.trim(); return t.content.firstChild; }

  async function refresh() {
    let me;
    try { me = await api('/api/v2/me'); } catch (e) { return; }
    if (!me.github_enabled) return;          // feature off -> show nothing
    ghUser = me.authenticated ? me : null;
    render();
  }

  function render() {
    document.getElementById('gh-ctrl')?.remove();
    const header = document.querySelector('header');
    if (!header) return;
    const wrap = el('<div id="gh-ctrl" style="display:flex;align-items:center;gap:8px;margin-left:8px"></div>');
    if (ghUser) {
      wrap.appendChild(el(`<span style="font-size:12px;color:var(--muted,#6b7280)">@${esc(ghUser.login)}</span>`));
      const pub = el('<button class="hbtn" title="Commit current ontology to GitHub as a pull request">&#11014; Publish to GitHub</button>');
      pub.addEventListener('click', publish);
      wrap.appendChild(pub);
      const out = el('<button class="hbtn">Sign out</button>');
      out.addEventListener('click', async () => { await api('/api/v2/logout', { method: 'POST' }); ghUser = null; render(); });
      wrap.appendChild(out);
    } else {
      const login = el('<button class="hbtn">Sign in with GitHub</button>');
      login.addEventListener('click', () => (location.href = BASE_PATH + '/auth/github'));
      wrap.appendChild(login);
    }
    header.appendChild(wrap);
  }

  async function publish() {
    const disease = state.detail?.name || '';
    const def = disease ? `Update ${disease}` : 'Update ontology';
    const msg = window.prompt('Commit message for the pull request:', def);
    if (msg === null) return;
    try {
      toast('Publishing to GitHub…');
      const r = await api('/api/v2/publish', { method: 'POST', body: { disease, message: msg } });
      const link = el(`<div class="toast" style="cursor:pointer">PR #${r.pr_number} opened on branch ${esc(r.branch)} — click to open</div>`);
      link.addEventListener('click', () => window.open(r.pr_url, '_blank'));
      document.body.appendChild(link); setTimeout(() => link.remove(), 8000);
    } catch (e) {
      toast('Publish failed: ' + e.message);
    }
  }

  if (document.readyState !== 'loading') refresh();
  else document.addEventListener('DOMContentLoaded', refresh);
})();
