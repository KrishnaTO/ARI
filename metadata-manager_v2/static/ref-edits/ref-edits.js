// Reference-review page: table of all diseases x database cross-references.
// Click an id to review it in a resizable side panel; mark correct/needs-change,
// add an alternate id and Save; for empty cells, link out to the target repo's
// search page. Confirmed (correct) cross-references are written to SSSOM +
// equivalency files in the published pull request.
(function () {
  const esc = s => String(s == null ? '' : s).replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
  const num = id => String(id).replace(/^[A-Za-z]+:/, '');
  const enc = encodeURIComponent;
  const apiUrl = p => new URL('../api/v2/' + p, location.href).href;
  async function api(p, opts = {}) {
    if (opts.body) { opts.headers = { 'content-type': 'application/json' }; opts.body = JSON.stringify(opts.body); }
    const r = await fetch(apiUrl(p), opts);
    if (!r.ok) { const d = await r.json().catch(() => ({})); throw new Error(d.detail || r.statusText); }
    return r.json();
  }

  const DBS = [
    { key: 'snomed', label: 'SNOMED', link: id => `https://browser.ihtsdotools.org/?perspective=full&conceptId1=${num(id)}&edition=MAIN`, search: n => `https://browser.ihtsdotools.org/?perspective=full&edition=MAIN&languages=en&searchText=${enc(n)}` },
    { key: 'omop',   label: 'OMOP', noframe: true,   link: id => `https://athena.ohdsi.org/search-terms/terms/${num(id)}`, search: n => `https://athena.ohdsi.org/search-terms/terms?query=${enc(n)}` },
    { key: 'doid',   label: 'DOID',   link: id => `https://disease-ontology.org/?id=DOID:${num(id)}`, search: n => `https://www.disease-ontology.org/?q=${enc(n)}` },
    { key: 'umls',   label: 'UMLS', noframe: true,   link: id => `https://uts.nlm.nih.gov/uts/umls/concept/${id}`, search: n => `https://uts.nlm.nih.gov/uts/umls/searchResults?searchString=${enc(n)}` },
    { key: 'mondo',  label: 'MONDO',  link: id => `https://www.ebi.ac.uk/ols4/ontologies/mondo/classes?short_form=MONDO_${num(id)}`, search: n => `https://www.ebi.ac.uk/ols4/search?q=${enc(n)}&ontology=mondo` },
    { key: 'icd10',  label: 'ICD-10', link: id => `https://www.icd10data.com/search?s=${enc(id)}`, search: n => `https://www.icd10data.com/search?s=${enc(n)}` },
    { key: 'mesh',   label: 'MeSH', noframe: true,   link: id => `https://meshb.nlm.nih.gov/record/ui?ui=${num(id)}`, search: n => `https://www.ncbi.nlm.nih.gov/mesh/?term=${enc(n)}` },
    { key: 'nci',    label: 'NCI',    link: id => `https://ncithesaurus.nci.nih.gov/ncitbrowser/ConceptReport.jsp?dictionary=NCI_Thesaurus&code=${num(id)}`, search: n => `https://www.ebi.ac.uk/ols4/search?q=${enc(n)}&ontology=ncit` },
  ];
  const DBMAP = Object.fromEntries(DBS.map(d => [d.key, d]));

  // database key -> object-curie prefix (mirrors app/sssom_service.py PREFIX), so
  // stored mappings can be matched back to the cell they came from.
  const PREFIX = {
    snomed: 'SNOMEDCT', omop: 'omop', doid: 'DOID', umls: 'umls',
    mondo: 'MONDO', icd10: 'icd10cm', mesh: 'mesh', nci: 'ncit',
  };

  let ROWS = [], me = null, reviewed = {}, edited = {}, active = null, sessionBranch = null, _tissues = null;
  // Pre-existing curated judgments keyed `${ari_id}|${prefix}|${id}` -> 'positive'|'negative'.
  let mappings = {};

  // Has this (disease, db) cell been judged positive/negative in an earlier
  // session (per the stored mappings)? Returns 'pos' | 'neg' | null. A positive
  // on any id in the cell wins over a negative.
  function preJudgment(r, dbkey) {
    const ari = r.ari_id, prefix = PREFIX[dbkey];
    if (!ari || !prefix) return null;
    let neg = false;
    for (const id of (r[dbkey] || [])) {
      const j = mappings[ari + '|' + prefix + '|' + id];
      if (j === 'positive') return 'pos';
      if (j === 'negative') neg = true;
    }
    return neg ? 'neg' : null;
  }
  const $ = s => document.querySelector(s);
  const cellEl = (iri, db) => document.querySelector(`[data-cell="${CSS.escape(iri + '|' + db)}"]`);

  function reviewMessage() {
    const iris = new Set();
    Object.keys(edited).forEach(k => iris.add(k.split('|')[0]));
    for (const [k, v] of Object.entries(reviewed)) if (v === 'ok') iris.add(k.split('|')[0]);
    const ari = [...iris].map(i => (ROWS.find(x => x.iri === i) || {}).ari_id).filter(Boolean).sort();
    let lab = ari.slice(0, 6).join(', ');
    if (ari.length > 6) lab += ', +' + (ari.length - 6) + ' more';
    return '[' + (lab || 'cross-references') + '] - mappings review';
  }

  // Collect this session's reviewed cells of a given verdict ('ok' positives /
  // 'bad' negatives) into the {ari_id, iri, name, db, ids} shape publish wants.
  function reviewedCells(verdict) {
    const out = [];
    for (const [k, v] of Object.entries(reviewed)) {
      if (v !== verdict) continue;
      const [iri, db] = k.split('|');
      const r = ROWS.find(x => x.iri === iri);
      const ids = (r && r[db]) || [];
      if (ids.length) out.push({ ari_id: r.ari_id, iri, name: r.name, db, ids });
    }
    return out;
  }
  const confirmedList = () => reviewedCells('ok');
  const flaggedList = () => reviewedCells('bad');

  function counts() {
    const ok = Object.values(reviewed).filter(v => v === 'ok').length;
    const bad = Object.values(reviewed).filter(v => v === 'bad').length;
    const ed = Object.keys(edited).length;
    const conf = confirmedList().length, flag = flaggedList().length;
    $('#counts').textContent = `confirmed ${ok} · flagged ${bad} · edited ${ed}`;
    $('#publish').disabled = !(me && me.authenticated && (ed > 0 || conf > 0 || flag > 0));
  }

  function setCellClass(iri, db) {
    const el = cellEl(iri, db); if (!el) return;
    const key = iri + '|' + db;
    const r = ROWS.find(x => x.iri === iri);
    const pre = r ? preJudgment(r, db) : null;
    el.classList.toggle('ok', reviewed[key] === 'ok');
    el.classList.toggle('bad', reviewed[key] === 'bad');
    el.classList.toggle('edited', !!edited[key]);
    // Pre-highlight only shows through when the curator hasn't judged it yet.
    el.classList.toggle('prepos', !reviewed[key] && pre === 'pos');
    el.classList.toggle('preneg', !reviewed[key] && pre === 'neg');
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
        const key = r.iri + '|' + db.key;
        const pre = preJudgment(r, db.key);
        const cls = (reviewed[key] === 'ok' ? ' ok' : reviewed[key] === 'bad' ? ' bad'
                    : pre === 'pos' ? ' prepos' : pre === 'neg' ? ' preneg' : '')
                    + (edited[key] ? ' edited' : '');
        const chips = ids.length
          ? ids.map(id => `<span class="xid" data-iri="${esc(r.iri)}" data-db="${db.key}" data-id="${esc(id)}">${esc(id)}</span>`).join(' ')
          : `<span class="add" data-iri="${esc(r.iri)}" data-db="${db.key}">+ add</span>`;
        const title = !reviewed[key] && pre ? ` title="Previously ${pre === 'pos' ? 'confirmed' : 'flagged'} in the curated mappings"` : '';
        h += `<td class="cell${cls}" data-cell="${esc(key)}"${title}>${chips}</td>`;
      }
      h += '</tr>';
    }
    h += '</tbody></table>';
    $('#table-wrap').innerHTML = h;
    $('#table-wrap').querySelectorAll('.xid').forEach(c => c.addEventListener('click', () => openPanel(c.dataset.iri, c.dataset.db, c.dataset.id)));
    $('#table-wrap').querySelectorAll('.add').forEach(c => c.addEventListener('click', () => openPanel(c.dataset.iri, c.dataset.db, null)));
  }

  function setReview(iri, db, v) {
    const key = iri + '|' + db;
    reviewed[key] = reviewed[key] === v ? null : v;
    setCellClass(iri, db); counts();
    // update panel buttons in place (no reload)
    const ok = $('#p-ok'), bad = $('#p-bad');
    if (ok) ok.classList.toggle('on', reviewed[key] === 'ok');
    if (bad) bad.classList.toggle('on', reviewed[key] === 'bad');
  }

  function openPanel(iri, dbkey, id) {
    active = { iri, dbkey };
    const r = ROWS.find(x => x.iri === iri);
    const db = DBMAP[dbkey];
    const ids = r[dbkey] || [];
    const key = iri + '|' + dbkey;
    let frameSrc = '', linksHtml;
    if (ids.length) {
      const target = id || ids[0];
      frameSrc = db.link(target);
      linksHtml = 'Open: ' + ids.map(x => `<a href="${esc(db.link(x))}" target="_blank" rel="noopener">${esc(x)} ↗</a>`).join(' · ');
    } else {
      frameSrc = db.search(r.name);
      linksHtml = `No ${db.label} id yet — <a href="${esc(db.search(r.name))}" target="_blank" rel="noopener">search ${db.label} for "${esc(r.name)}" ↗</a>, then paste the id below.`;
    }
    $('#panel').innerHTML = `
      <div class="p-head"><strong>${esc(r.name)}</strong> · ${db.label}
        <button class="btn" id="p-close" style="float:right">✕</button></div>
      <div class="p-q">Is this ${db.label} reference correct?
        <button class="btn ok ${reviewed[key] === 'ok' ? 'on' : ''}" id="p-ok">✓ Correct</button>
        <button class="btn bad ${reviewed[key] === 'bad' ? 'on' : ''}" id="p-bad">✗ Needs change</button></div>
      <div class="p-sub"><span class="muted">Distinct variant of this disease?</span>
        <button class="btn" id="p-subtype">＋ New subtype</button></div>
      <div class="p-edit">
        <label>${db.label} id(s) — comma separated (add an alternate id here)</label>
        <input id="p-ids" value="${esc(ids.join(', '))}" placeholder="e.g. 12345, 67890">
        <button class="btn primary" id="p-save">Save</button>
      </div>
      <div class="p-links">${linksHtml}</div>
      ${db.noframe
        ? `<div class="p-note muted" style="padding:16px">${db.label} can't be previewed here (it blocks embedding${dbkey === 'umls' ? ' and requires login' : ''}). Use the "↗" link${ids.length ? 's' : ''} above to open it in a new tab.</div>`
        : `<div class="p-note muted">If the page below is blank, the source site blocks embedding — use the "↗" link to open it in a new tab.</div><iframe id="p-frame" src="${esc(frameSrc)}"></iframe>`}`;
    $('#side').classList.add('open');
    $('#divider').classList.add('show');
    $('#p-close').addEventListener('click', closePanel);
    $('#p-ok').addEventListener('click', () => setReview(iri, dbkey, 'ok'));
    $('#p-bad').addEventListener('click', () => setReview(iri, dbkey, 'bad'));
    $('#p-save').addEventListener('click', () => save(iri, dbkey));
    $('#p-subtype').addEventListener('click', () => openSubtypeOverlay(iri));
  }

  function closePanel() { closeSubtypeOverlay(); $('#side').classList.remove('open'); $('#divider').classList.remove('show'); }

  // -------------------------------------------------- NEW-SUBTYPE OVERLAY
  // Covers only the table (left) area so the reference info in the right panel
  // stays visible while a curator fills in a new child disease.
  async function loadTissues() {
    if (!_tissues) _tissues = await api('tissues');
    return _tissues;
  }

  function closeSubtypeOverlay() { $('#subtype-overlay').classList.remove('open'); }

  async function openSubtypeOverlay(parentIri) {
    const r = ROWS.find(x => x.iri === parentIri);
    if (!r) return;
    const ov = $('#subtype-overlay');
    ov.style.width = $('#table-wrap').getBoundingClientRect().width + 'px';
    ov.innerHTML = `
      <div class="so-head"><strong>＋ New subtype</strong><span style="flex:1"></span>
        <button class="btn" id="so-close">✕</button></div>
      <div class="so-body">
        <div class="so-parent-info">Parent disease: <strong>${esc(r.name)}</strong><br>
          Created as a child (subtype) of this disease. Use the reference info on the right to fill the cross-reference ids below.</div>
        <div class="so-field" id="so-existing-wrap" style="display:none"><label>Start from an existing clinical subtype</label>
          <select id="so-existing"><option value="">— blank —</option></select></div>
        <div class="so-field"><label>Label <span class="so-req">*</span></label>
          <input id="so-label" placeholder="e.g. Juvenile-onset ${esc(r.name)}"></div>
        <div class="so-field"><label>Definition <span class="so-req">*</span></label>
          <textarea id="so-definition" placeholder="A subtype of ${esc(r.name)} characterized by…"></textarea></div>
        <div class="so-field"><label>Definition source <span class="so-req">*</span></label>
          <input id="so-defsrc" placeholder="URL or PMID: 12345678"></div>
        <div class="so-field"><label>Target tissue <span class="so-req">*</span></label>
          <div class="so-tissue-grid" id="so-tissues"><span class="muted">Loading…</span></div></div>
        <div class="so-field"><label>Synonyms (comma separated)</label>
          <input id="so-synonyms" placeholder="Synonym 1, Synonym 2"></div>
        <div class="so-field"><label>Disease category</label><input id="so-category"></div>
        <div class="so-field"><label>Clinical subtypes (comma separated)</label>
          <input id="so-clinical" placeholder="Name - description, …"></div>
        <div class="so-field"><label>Editor name</label>
          <input id="so-editor" value="${esc((me && me.login) || '')}"></div>
      </div>
      <div class="so-actions">
        <button class="btn primary" id="so-save">＋ Create subtype</button>
        <button class="btn" id="so-cancel">Cancel</button></div>`;
    ov.classList.add('open');
    $('#so-close').addEventListener('click', closeSubtypeOverlay);
    $('#so-cancel').addEventListener('click', closeSubtypeOverlay);
    $('#so-save').addEventListener('click', () => submitSubtype(parentIri));
    // Offer the parent's existing clinical subtypes (not in the xref row) as a
    // starting point: picking one seeds the new child's label + definition.
    api('disease/' + enc(parentIri)).then(det => {
      const subs = (det && det.clinical_subtypes) || [];
      if (!subs.length) return;
      const sel = $('#so-existing');
      if (!sel) return;
      sel.innerHTML = '<option value="">— blank —</option>' +
        subs.map((s, i) => `<option value="${i}">${esc(String(s).split(' - ')[0])}</option>`).join('');
      sel.addEventListener('change', () => {
        if (sel.value === '') return;
        const raw = String(subs[sel.value]), dash = raw.indexOf(' - ');
        $('#so-label').value = dash >= 0 ? raw.slice(0, dash) : raw;
        if (dash >= 0) $('#so-definition').value = raw.slice(dash + 3);
      });
      $('#so-existing-wrap').style.display = '';
    }).catch(() => {});   // existing-subtype picker is optional; ignore failures
    try {
      const tissues = await loadTissues();
      $('#so-tissues').innerHTML = tissues.length
        ? tissues.map(t => `<label class="so-tissue-check"><input type="checkbox" value="${esc(t.iri)}"> ${esc(t.name)}</label>`).join('')
        : '<span class="muted">No tissues available</span>';
    } catch (e) { $('#so-tissues').innerHTML = '<span class="muted">Failed to load tissues: ' + esc(e.message) + '</span>'; }
  }

  async function submitSubtype(parentIri) {
    if (!me || !me.authenticated) { alert('Sign in with GitHub first.'); return; }
    const val = id => ($('#' + id)?.value || '').trim();
    const label = val('so-label'), definition = val('so-definition'), defsrc = val('so-defsrc');
    const tissue_iris = [...document.querySelectorAll('#so-tissues input:checked')].map(c => c.value);
    if (!label)             { alert('Label is required'); return; }
    if (!definition)        { alert('Definition is required'); return; }
    if (!defsrc)            { alert('Definition source is required'); return; }
    if (!tissue_iris.length){ alert('Select at least one target tissue'); return; }
    const editor = val('so-editor') || (me && me.login) || 'curator';
    const data = {
      label, definition, def_source: [defsrc], tissue_iris, parent_iri: parentIri,
      synonyms: val('so-synonyms'), disease_category: val('so-category'),
      clinical_subtypes: val('so-clinical'),
    };
    const btn = $('#so-save');
    btn.disabled = true; btn.textContent = 'Creating…';
    try {
      const created = await api('disease', { method: 'POST', body: { data, editor } });
      ROWS = await api('xrefs');           // refresh so the new subtype appears in the table
      closeSubtypeOverlay();
      renderTable($('#filter').value); counts();
      alert('Created subtype: ' + created.name);
    } catch (e) {
      alert('Create failed: ' + e.message);
      btn.disabled = false; btn.textContent = '＋ Create subtype';
    }
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
    const comment = window.prompt('Optional comment for the pull request (what you reviewed/changed):', 'Mappings review');
    if (comment === null) return;
    const orcid = (localStorage.getItem('ari_editor_orcid') || '').trim();
    const author = orcid ? ('orcid:' + orcid) : (me && me.login ? ('github:' + me.login) : 'curator');
    const message = reviewMessage();
    $('#publish').disabled = true; $('#publish').textContent = 'Publishing…';
    try {
      const r = await api('publish', { method: 'POST', body: {
        disease: 'mappings review', message, comment,
        confirmed: confirmedList(), flagged: flaggedList(), author,
        branch: sessionBranch, labels: ['edit term', 'sssom'] } });
      sessionBranch = r.branch;                       // subsequent publishes append to the same PR
      const pl = $('#prlink');
      pl.textContent = 'PR #' + r.pr_number + (r.fork ? ' (from your fork) ↗' : ' ↗'); pl.href = r.pr_url; pl.style.display = '';
      $('#publish').textContent = 'Publish more to PR #' + r.pr_number;
      $('#publish').disabled = true;                  // re-enabled by counts() when new changes are made
    } catch (e) { alert('Publish failed: ' + e.message); $('#publish').textContent = sessionBranch ? 'Publish more to PR' : 'Publish review (PR)'; counts(); }
  }

  // Draggable splitter — adjust side-panel width on all screens (mouse + touch).
  function initDivider() {
    const div = $('#divider'), body = document.querySelector('.body'), side = $('#side');
    let dragging = false;
    const move = e => {
      if (!dragging) return;
      const x = (e.touches ? e.touches[0].clientX : e.clientX);
      const rect = body.getBoundingClientRect();
      let w = rect.right - x;
      w = Math.max(260, Math.min(rect.width - 160, w));
      side.style.width = w + 'px';
    };
    const start = e => { dragging = true; document.body.classList.add('dragging'); e.preventDefault(); };
    const end = () => { dragging = false; document.body.classList.remove('dragging'); };
    div.addEventListener('mousedown', start); div.addEventListener('touchstart', start, { passive: false });
    window.addEventListener('mousemove', move); window.addEventListener('touchmove', move, { passive: false });
    window.addEventListener('mouseup', end); window.addEventListener('touchend', end);
  }

  async function init() {
    try { me = await api('me'); } catch (e) { me = { github_enabled: false, authenticated: false }; }
    $('#auth').innerHTML = !me.authenticated
      ? (me.github_enabled ? `<a class="btn" href="${new URL('../auth/github?next=' + encodeURIComponent(location.pathname + location.search), location.href).href}">Sign in with GitHub</a>` : '<span class="muted">GitHub off — review only</span>')
      : `<span class="muted">@${esc(me.login)}</span>`;
    try { ROWS = await api('xrefs'); } catch (e) { $('#table-wrap').innerHTML = '<p class="muted" style="padding:16px">Failed to load: ' + esc(e.message) + '</p>'; return; }
    // Pre-existing curated judgments pre-highlight cells; failure is non-fatal.
    try {
      mappings = {};
      for (const m of await api('mappings')) mappings[m.ari_id + '|' + m.prefix + '|' + m.id] = m.judgment;
    } catch (e) { mappings = {}; }
    renderTable(''); counts(); initDivider();
    $('#filter').addEventListener('input', e => renderTable(e.target.value));
    $('#publish').addEventListener('click', publish);
  }
  document.addEventListener('DOMContentLoaded', init);
})();
