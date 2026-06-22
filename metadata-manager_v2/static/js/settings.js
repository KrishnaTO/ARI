// Settings panel: fetch latest from the source branch (with discard follow-up),
// switch the source branch (any edit/* branch or the working branch), and pick
// which branch edits are PR'd into. Also exports the current data to Excel.
// Talks only to the backend; no secrets here.
(function () {
  function opts(list, sel) {
    return list.map(b => `<option ${b === sel ? 'selected' : ''}>${esc(b)}</option>`).join('');
  }

  async function open() {
    let s;
    try { s = await api('/api/v2/settings'); } catch (e) { return toast('Settings unavailable: ' + e.message); }
    const authed = s.authenticated;
    const note = !s.github_enabled
      ? '<p style="font-size:13px;color:#9b1c1c">GitHub integration is off — set the GitHub env vars to enable fetch/switch/PR.</p>'
      : (!authed ? '<p style="font-size:13px;color:#9b1c1c">Sign in with GitHub to fetch, switch branch, or change the PR target.</p>' : '');
    const dis = (s.github_enabled && authed) ? '' : 'disabled';
    const dirty = s.dirty ? '<span class="fb-pill" style="background:#fce4d6;color:#9b1c1c">unpublished local edits</span>' : '<span class="fb-pill">in sync</span>';

    const html = `<div class="modal-overlay" id="set-overlay"><div class="modal">
      <div class="modal-head"><h2>&#9881; Settings</h2><button class="hbtn" id="set-close">✕</button></div>
      <div class="modal-body">
        <div class="section-label">Data source</div>
        <p style="font-size:13px;margin:0 0 8px">Populating from <strong>${esc(s.source_branch)}</strong> ${dirty}</p>
        <div class="field"><label>Source branch (populate from)</label>
          <select id="set-source" ${dis}>${opts(s.branches, s.source_branch)}</select></div>
        <div class="edit-actions" style="gap:8px;margin:4px 0 14px">
          <button class="hbtn" id="set-fetch" ${dis}>&#8635; Fetch changes now</button>
          <button class="hbtn primary" id="set-switch" ${dis}>Switch &amp; fetch</button>
        </div>

        <div class="section-label">Pull-request target</div>
        <p style="font-size:13px;margin:0 0 14px">Edits open PRs into <strong>${esc(s.pr_base)}</strong> — the PR target always matches the source branch above.</p>

        <div class="section-label">Identity</div>
        <p style="font-size:13px;margin:0 0 8px">Edits are attributed to your GitHub name, or to your <strong>ORCID iD</strong> if set below.</p>
        <div class="field"><label>ORCID iD (optional)</label>
          <input id="set-orcid" placeholder="0000-0000-0000-0000"></div>
        <div class="edit-actions" style="margin:4px 0 14px"><button class="hbtn" id="set-orcid-save">Save ORCID</button></div>

        <div class="section-label">Reference review</div>
        <div class="edit-actions" style="margin:4px 0 14px"><a class="hbtn" href="ref-edits/" target="_blank">&#128279; Open cross-reference review page</a></div>

        <div class="section-label">Export</div>
        <div class="edit-actions" style="margin-top:4px"><button class="hbtn" id="set-export">&#128202; Export current data to Excel</button></div>
        ${note}
      </div></div></div>`;
    document.body.insertAdjacentHTML('beforeend', html);
    const close = () => $('#set-overlay').remove();
    $('#set-close').addEventListener('click', close);
    $('#set-overlay').addEventListener('click', e => { if (e.target.id === 'set-overlay') close(); });

    $('#set-fetch')?.addEventListener('click', () => doFetch('/api/v2/fetch', {}));
    $('#set-switch')?.addEventListener('click', () => doFetch('/api/v2/source', { branch: $('#set-source').value }));
    $('#set-export').addEventListener('click', () => { window.location = BASE_PATH + '/api/v2/export'; });
    $('#set-orcid').value = (localStorage.getItem('ari_editor_orcid') || '');
    $('#set-orcid-save').addEventListener('click', () => {
      const v = $('#set-orcid').value.trim();
      if (v && !/^\d{4}-\d{4}-\d{4}-\d{3}[\dX]$/.test(v)) { toast('ORCID should look like 0000-0000-0000-0000'); return; }
      if (v) localStorage.setItem('ari_editor_orcid', v); else localStorage.removeItem('ari_editor_orcid');
      if (typeof resolveEditor === 'function') resolveEditor();
      toast(v ? ('Edits will be attributed to ORCID ' + v) : 'ORCID cleared — using GitHub name');
    });
  }

  async function doFetch(url, body) {
    try {
      let r = await api(url, { method: 'POST', body });
      if (r.needs_confirm) {
        if (!window.confirm(r.detail + '\n\nDiscard local edits and continue?')) return;
        r = await api(url, { method: 'POST', body: { ...body, discard: true } });
      }
      toast('Loaded ' + (r.source_branch || 'branch') + ' — reloading…');
      setTimeout(() => location.reload(), 700);
    } catch (e) { toast('Failed: ' + e.message); }
  }

  function bind() {
    const btn = document.getElementById('settings-btn');
    if (btn) btn.addEventListener('click', open);
  }
  if (document.readyState !== 'loading') bind();
  else document.addEventListener('DOMContentLoaded', bind);
})();
