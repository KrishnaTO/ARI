// Reference-review page: table of all diseases x database cross-references, a
// side panel that loads the target site for review, inline editing to add an
// alternate id, and a Publish-to-GitHub (PR) action. Self-contained — talks to
// the same backend over same-origin cookies.
(function () {
  const esc = s => String(s == null ? '' : s).replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
  const num = id => String(id).replace(/^[A-Za-z]+:/, '');
  const apiUrl = p => new URL('../api/v2/' + p, location.href).href;
  async function api(p, opts = {}) {
    if (opts.body) { opts.headers = { 'content-type': 'application/json' }; opts.body = JSON.stringify(opts.body); }
    const r = await fetch(apiUrl(p), opts);
    if (!r.ok) { const d = await r.json().catch(() => ({})); throw new Error(d.detail || r.statusText); }
    return r.json();
  }

  const DBS = [
    { key: 'snomed', label: 'SNOMED', link: id => `https://browser.ihtsdotools.org/?perspective=full&conceptId1=${num(id)}&edition=MAIN` },
    { key: 'omop',   label: 'OMOP',   link: id => `https://athena.ohdsi.org/search-terms/terms/${num(id)}` },
    { key: 'doid',   label: 'DOID',   link: id => `https://disease-ontology.org/?id=DOID:${num(id)}` },
    { key: 'umls',   label: 'UMLS',   link: id => `https://uts.nlm.nih.gov/uts/umls/concept/${id}` },
    { key: 'mondo',  label: 'MONDO',  link: id => `https://www.ebi.ac.uk/ols4/ontologies/mondo/classes?short_form=MONDO_${num(id)}` },
    { key: 'icd10',  label: 'ICD-10', link: id => `https://www.icd10data.com/search?s=${encodeURIComponent(id)}` },
    { key: 'mesh',   label: 'MeSH',   link: id => `https://meshb.nlm.nih.gov/record/ui?ui=${num(id)}` },
    { key: 'nci',    label: 'NCI',    link: id => `https://ncithesaurus.nci.nih.gov/ncitbrowser/ConceptReport.jsp?dictionary=NCI_Thesaurus&code=${num(id)}` },
  ];
  const DBMAP = Object.fromEntries(DBS.map(d => [d.key, d]));

  let ROWS = [], me = null, reviewed = {}, edited = {}, active = null;
  const $ = s => document.querySelector(s);

  function counts() {
    const ok = Object.values(reviewed).filter(v => v === 'ok').length;
    const bad = Object.values(reviewed).filter(v => v === 'bad').length;
    const ed = Object.keys(edited).length;
    $('#counts').textContent = `reviewed ${ok} · flagged ${bad} · edited ${ed}`;
    $('#publish').disabled = !(me && me.authenticated && ed > 0);
  }

  function renderTable(filter) {
    const q = (filter || '').trim().toLowerCase();
    const rows = ROWS.filter(r => !q || (r.name || '').toLowerCase().includes(q) ||
      DBS.some(db => (r[db.key] || []).some(id => String(id).toLowerCase().includes(q))));
    let h = '<table><thead><tr><th>Disease</th>' + DBS.map(d => `<th>${d.label}</th>`).join('') + '</tr></thead><tbody>';
    for (const r of rows) {
      h += `<tr><td class="dz">${esc(r.name)}</td>`;
      for (const db of DBS) {
        const ids = r[db.key] || [];
        const cellKey = r.iri + '|' + db.key;
        const cls = reviewed[cellKey] === 'ok' ? 'ok' : reviewed[cellKey] === 'bad' ? 'bad' : '';
        const edm = edited[cellKey] ? ' edited' : '';
        const chips = ids.length
          ? ids.map(id => `<span class="xid" data-iri="${esc(r.iri)}" data-db="${db.key}" data-id="${esc(id)}">${esc(id)}</span>`).join(' ')
          : `<span class="add" data-iri="${esc(r.iri)}" data-db="${db.key}">+ add</span>`;
        h += `<td class="cell ${cls}${edm}">${chips}</td>`;
      }
      h += '</tr>';
    }
    h += '</tbody></table>';
    $('#table-wrap').innerHTML = h;
    $('#table-wrap').querySelectorAll('.xid').forEach(c => c.addEventListener('click', () => openPanel(c.dataset.iri, c.dataset.db, c.dataset.id)));
    $('#table-wrap').querySelectorAll('.add').forEach(c => c.addEventListener('click', () => openPanel(c.dataset.iri, c.dataset.db, null)));
  }

  function openPanel(iri, dbkey, id) {
    active = { iri, dbkey };
    const r = ROWS.find(x => x.iri === iri);
    const db = DBMAP[dbkey];
    const ids = r[dbkey] || [];
    const cellKey = iri + '|' + dbkey;
    const target = id || ids[0];
    const links = ids.map(x => `<a href="${esc(db.link(x))}" target="_blank" rel="noopener">${esc(x)} ↗</a>`).join(' · ') || '<span class="muted">none yet</span>';
    $('#panel').innerHTML = `
      <div class="p-head"><strong>${esc(r.name)}</strong> · ${db.label}
        <button class="btn" id="p-close" style="float:right">✕</button></div>
      <div class="p-q">Is this ${db.label} reference correct?
        <button class="btn ok ${reviewed[cellKey] === 'ok' ? 'on' : ''}" id="p-ok">✓ Correct</button>
        <button class="btn bad ${reviewed[cellKey] === 'bad' ? 'on' : ''}" id="p-bad">✗ Needs change</button></div>
      <div class="p-edit">
        <label>${db.label} id(s) — comma separated (add an alternate id here)</label>
        <input id="p-ids" value="${esc(ids.join(', '))}">
        <button class="btn primary" id="p-save">Save</button>
      </div>
      <div class="p-links">Open: ${links}</div>
      <div class="p-note muted">If the page below is blank, the source site blocks embedding — use the "↗" link to open it in a new tab.</div>
      <iframe id="p-frame" ${target ? `src="${esc(db.link(target))}"` : ''}></iframe>`;
    $('#side').classList.add('open');
    $('#p-close').addEventListener('click', () => $('#side').classList.remove('open'));
    $('#p-ok').addEventListener('click', () => { reviewed[cellKey] = reviewed[cellKey] === 'ok' ? null : 'ok'; renderTable($('#filter').value); counts(); openPanel(iri, dbkey, id); });
    $('#p-bad').addEventListener('click', () => { reviewed[cellKey] = reviewed[cellKey] === 'bad' ? null : 'bad'; renderTable($('#filter').value); counts(); openPanel(iri, dbkey, id); });
    $('#p-save').addEventListener('click', () => save(iri, dbkey));
  }

  async function save(iri, dbkey) {
    if (!me || !me.authenticated) { alert('Sign in with GitHub first.'); return; }
    const val = $('#p-ids').value.trim();
    $('#p-save').disabled = true; $('#p-save').textContent = 'Saving…';
    try {
      const updated = await api('disease/' + encodeURIComponent(iri), { method: 'PUT', body: { changes: { [dbkey]: val } } });
      const r = ROWS.find(x => x.iri === iri);
      r[dbkey] = updated[dbkey] || [];
      edited[iri + '|' + dbkey] = true;
      renderTable($('#filter').value); counts(); openPanel(iri, dbkey, null);
    } catch (e) { alert('Save failed: ' + e.message); $('#p-save').disabled = false; $('#p-save').textContent = 'Save'; }
  }

  async function publish() {
    const comment = window.prompt('Optional comment for the pull request (what you reviewed/changed):', 'Cross-reference review');
    if (comment === null) return;
    $('#publish').disabled = true; $('#publish').textContent = 'Publishing…';
    try {
      const r = await api('publish', { method: 'POST', body: { disease: 'Cross-reference review', message: 'Cross-reference review', comment } });
      $('#publish').textContent = 'Open PR #' + r.pr_number;
      $('#publish').onclick = () => window.open(r.pr_url, '_blank');
      $('#publish').disabled = false;
    } catch (e) { alert('Publish failed: ' + e.message); $('#publish').textContent = 'Publish review (PR)'; counts(); }
  }

  async function init() {
    try { me = await api('me'); } catch (e) { me = { github_enabled: false, authenticated: false }; }
    if (!me.authenticated) {
      $('#auth').innerHTML = me.github_enabled
        ? `<a class="btn" href="${new URL('../auth/github', location.href).href}">Sign in with GitHub</a>`
        : '<span class="muted">GitHub integration off — review only</span>';
    } else {
      $('#auth').innerHTML = `<span class="muted">@${esc(me.login)}</span>`;
    }
    try { ROWS = await api('xrefs'); } catch (e) { $('#table-wrap').innerHTML = '<p class="muted">Failed to load: ' + esc(e.message) + '</p>'; return; }
    renderTable(''); counts();
    $('#filter').addEventListener('input', e => renderTable(e.target.value));
    $('#publish').addEventListener('click', publish);
  }
  document.addEventListener('DOMContentLoaded', init);
})();
