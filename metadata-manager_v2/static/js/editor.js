// Editing: the global edit toggle, the disease-field editor, the per-category
// item CRUD (add / edit / delete) and the admin version-release dialog.

// ----------------------------------------------------------------- DEF SOURCE ROW HELPER
// Renders one URL + optional-label row for the definition-source structured editor.
function defSrcRowHtml(text = '', url = '') {
  return `<div class="def-src-row">` +
    `<input class="f_defsrc_url" type="text" placeholder="URL or PMID: 12345678" value="${esc(url)}">` +
    `<input class="f_defsrc_text" type="text" placeholder="Label / author (optional)" value="${esc(text)}">` +
    `<button type="button" class="hbtn defsrc-rm-btn" onclick="this.closest('.def-src-row').remove()" title="Remove">&#x2715;</button>` +
    `</div>`;
}
function _collectDefSrcs(listId) {
  const srcs = [];
  document.querySelectorAll(`#${listId} .def-src-row`).forEach(row => {
    const url = (row.querySelector('.f_defsrc_url')?.value || '').trim();
    const txt = (row.querySelector('.f_defsrc_text')?.value || '').trim();
    const s = (txt && url) ? `${txt}; ${url}` : (url || txt);
    if (s) srcs.push(s);
  });
  return srcs;
}

// ----------------------------------------------------------------- EDIT MODE
$('#edit-toggle').addEventListener('click', () => {
  if (!state.detail) return;
  state.editMode = !state.editMode;
  $('#edit-toggle').classList.toggle('active', state.editMode);
  $('#edit-toggle').innerHTML = state.editMode ? '✓ Done' : '✎ Edit';
  closeRightPanel();
  renderDetail(state.detail);
});

function fieldText(id, label, value){
  return `<div class="field"><label>${label}</label><input id="${id}" value="${esc(value)}"></div>`;
}
function fieldArea(id, label, value){
  return `<div class="field"><label>${label}</label><textarea id="${id}">${esc(value)}</textarea></div>`;
}

// Disease-level field editor (opens in the right panel, like the item editors)
function openDiseaseFieldEditor(d){
  state.activeBox = '__fields__';
  $('#layout').classList.add('split');
  $('#right-col').classList.add('open');
  $('#detail-pane').querySelectorAll('.box').forEach(b => b.classList.remove('active'));
  let html = `<button class="close-btn" onclick="closeRightPanel()">✕ Close</button>
    <div class="edit-form" style="padding:0"><h2>Edit fields: ${esc(d.name)}</h2>
    <p style="font-size:12px;color:var(--muted);margin:0 0 12px">IRI / ARI local id is fixed. Saving appends a changelog entry and writes the OWL file.</p>`;
  html += fieldText('f_name', 'Label', d.name);
  html += fieldArea('f_definition', 'Definition (markdown)', d.definition);
  html += fieldArea('f_synonyms', 'Synonyms (comma separated)', (d.synonyms||[]).join(', '));
  html += fieldArea('f_clinical_subtypes', 'Clinical subtypes (comma separated)', (d.clinical_subtypes||[]).join(', '));
  html += '<div class="field-grid">';
  html += fieldText('f_disease_category', 'Category', first(d.disease_category));
  html += fieldText('f_evidence_quality', 'Evidence quality', first(d.evidence_quality));
  html += fieldText('f_icd10', 'ICD-10 (comma separated)', (d.icd10||[]).join(', '));
  html += fieldText('f_snomed', 'SNOMED (comma separated)', (d.snomed||[]).join(', '));
  html += fieldText('f_omop', 'OMOP (comma separated)', (d.omop||[]).join(', '));
  html += fieldText('f_doid', 'DOID (comma separated)', (d.doid||[]).join(', '));
  html += fieldText('f_umls', 'UMLS (comma separated)', (d.umls||[]).join(', '));
  html += fieldText('f_mondo', 'MONDO (comma separated)', (d.mondo||[]).join(', '));
  html += fieldText('f_mesh', 'MeSH (comma separated)', (d.mesh||[]).join(', '));
  html += fieldText('f_nci', 'NCI (comma separated)', (d.nci||[]).join(', '));
  html += fieldText('f_prevalence_per_100k', 'Prevalence /100k', first(d.prevalence_per_100k));
  html += fieldText('f_prevalence_value', 'Estimated cases', first(d.prevalence_value));
  html += fieldText('f_incidence_rate', 'Incidence rate', first(d.incidence_rate));
  html += '</div>';
  html += fieldText('f_demographic_bias', 'Demographic bias', first(d.demographic_bias));
  html += fieldText('f_age_range', 'Age range', first(d.age_range));
  html += fieldArea('f_prevalence_desc', 'Prevalence description', first(d.prevalence_desc));
  // Structured def-source editor: parse existing citations into URL + label rows
  const _dsCites = [];
  for (const s of (d.def_source || [])) for (const c of parseDefSrc(String(s))) _dsCites.push(c);
  const _dsShown = new Set(_dsCites.map(c => c.url).filter(Boolean));
  for (const p of (d.pubmed || [])) { const u = String(p||'').trim(); if (u && !_dsShown.has(u)) _dsCites.push({text:'',url:u}); }
  if (!_dsCites.length) _dsCites.push({text:'',url:''});
  html += `<div class="field"><label>Definition sources <span style="font-weight:400;text-transform:none;font-size:11px;color:var(--muted)">(URL required for each; label optional)</span></label>` +
    `<div id="f_defsrc_list">${_dsCites.map(c => defSrcRowHtml(c.text, c.url)).join('')}</div>` +
    `<button type="button" class="hbtn" id="f_defsrc_add" style="font-size:11px;margin-top:3px">&#xFF0B; Add source</button></div>`;
  html += `<div class="field field-row"><input type="checkbox" id="f_obsolete" ${d.obsolete?'checked':''}><label style="margin:0">Mark as obsolete</label></div>`;
  html += `<div class="field"><label>Editor name</label><input id="f_editor" value="${esc(state.editor)}"></div>`;
  html += `<div class="edit-actions"><button class="hbtn primary" id="save-btn">💾 Save changes</button>
    <button class="hbtn" onclick="closeRightPanel()">Cancel</button></div></div>`;
  $('#right-panel-content').innerHTML = html;
  $('#save-btn').addEventListener('click', saveEdits);
  $('#f_defsrc_add')?.addEventListener('click', () =>
    $('#f_defsrc_list').insertAdjacentHTML('beforeend', defSrcRowHtml('', '')));
}

async function saveEdits(){
  const v = id => $('#'+id)?.value ?? '';
  const changes = {
    name: v('f_name'), definition: v('f_definition'),
    synonyms: v('f_synonyms'), clinical_subtypes: v('f_clinical_subtypes'),
    disease_category: v('f_disease_category'),
    evidence_quality: v('f_evidence_quality'), icd10: v('f_icd10'), snomed: v('f_snomed'),
    doid: v('f_doid'), umls: v('f_umls'), mondo: v('f_mondo'),
    omop: v('f_omop'), mesh: v('f_mesh'), nci: v('f_nci'),
    prevalence_per_100k: v('f_prevalence_per_100k'), prevalence_value: v('f_prevalence_value'),
    incidence_rate: v('f_incidence_rate'), demographic_bias: v('f_demographic_bias'),
    age_range: v('f_age_range'), prevalence_desc: v('f_prevalence_desc'),
    def_source: _collectDefSrcs('f_defsrc_list'),
    obsolete: $('#f_obsolete').checked ? 'true' : 'false',
  };
  state.editor = v('f_editor') || 'curator';
  try {
    $('#save-btn').disabled = true; $('#save-btn').textContent = 'Saving...';
    const updated = await api(`/api/v2/disease/${encodeURIComponent(state.activeIri)}`, {
      method: 'PUT', body: { changes, editor: state.editor }
    });
    state.detail = updated;
    closeRightPanel();
    renderDetail(updated);
    renderTab();
    init();
    toast('Saved ✓ changelog updated');
  } catch (err){
    toast('Save failed: ' + err.message);
    $('#save-btn').disabled = false; $('#save-btn').textContent = '💾 Save changes';
  }
}

// ----------------------------------------------------------------- ITEM CRUD (data items)
function itemSecondary(category, it){
  const map = {
    symptoms:'likelihood', environmental:'likelihood', antibodies:'frequency',
    genetic:'risk_effect', treatments:'type', etiology:'origin_type',
    biomarkers:'diagnostic_use', pathophysiology:'category',
  };
  return first(it[map[category] || 'relevance']);
}

function renderItemEditor(d, category, panel){
  const spec = state.schema[category];
  const items = d[DETAIL_KEY[category]] || [];
  let html = `<button class="close-btn" onclick="closeRightPanel()">✕ Close</button><h2>Manage ${esc(spec.label)} items</h2>`;
  html += panelDescHTML(category);
  html += `<div style="display:flex;gap:8px;margin-bottom:10px">`+
    `<button class="hbtn primary" id="item-add">＋ Add ${esc(spec.label)}</button>`+
    `<button class="hbtn" id="item-view">← Back to details</button></div>`;
  if (!items.length){
    html += '<div class="empty-state">No items yet — use “Add”.</div>';
  } else {
    html += `<table class="data-table"><thead><tr><th>${esc(spec.label)}</th><th style="width:74px"></th></tr></thead><tbody>`;
    items.forEach((it, i) => {
      const sec = itemSecondary(category, it);
      html += `<tr class="${it.obsolete?'obsolete':''}"><td><strong>${esc(it.name)}</strong>${it.obsolete?' <span class="obsolete-tag">(obsolete)</span>':''}`+
        (sec ? `<div style="font-size:11px;color:var(--muted)">${esc(sec)}</div>` : '')+
        `</td><td style="white-space:nowrap"><button class="icon-btn" data-edit="${i}" title="Edit">✎</button> <button class="icon-btn danger" data-del="${i}" title="Delete">🗑</button></td></tr>`;
    });
    html += `</tbody></table>`;
  }
  panel.innerHTML = html;
  $('#item-add').addEventListener('click', () => openItemModal(category, null));
  $('#item-view').addEventListener('click', () => renderReadView(d, category, panel));
  panel.querySelectorAll('[data-edit]').forEach(b => b.addEventListener('click', () => openItemModal(category, items[+b.dataset.edit])));
  panel.querySelectorAll('[data-del]').forEach(b => b.addEventListener('click', () => deleteItem(category, items[+b.dataset.del])));
}

function openItemModal(category, item){
  const spec = state.schema[category];
  const isEdit = !!item;
  let fields = '';
  for (const f of spec.fields){
    const cur = item ? first(item[f.read]) : '';
    const fid = 'itf_' + f.key;
    if (f.type === 'checkbox'){
      fields += `<div class="field field-row"><input type="checkbox" id="${fid}" ${item && item.obsolete ? 'checked':''}><label style="margin:0">${esc(f.label)}</label></div>`;
    } else if (f.type === 'select'){
      const opts = (f.options||[]).map(o => `<option ${String(cur)===o?'selected':''}>${esc(o)}</option>`).join('');
      fields += `<div class="field"><label>${esc(f.label)}</label><select id="${fid}"><option value=""></option>${opts}</select></div>`;
    } else if (f.type === 'area'){
      fields += `<div class="field"><label>${esc(f.label)}</label><textarea id="${fid}">${esc(cur)}</textarea></div>`;
    } else {
      const t = f.type === 'number' ? 'number' : 'text';
      fields += `<div class="field"><label>${esc(f.label)}</label><input type="${t}" id="${fid}" value="${esc(cur)}"></div>`;
    }
  }
  const html = `<div class="modal-overlay" id="item-overlay"><div class="modal">
    <div class="modal-head"><h2>${isEdit?'Edit':'Add'} ${esc(spec.label)}</h2><button class="hbtn" id="item-cancel">✕</button></div>
    <div class="modal-body">${fields}
      <div class="field"><label>Editor name</label><input id="itf_editor" value="${esc(state.editor)}"></div>
      <div class="edit-actions"><button class="hbtn primary" id="item-save">💾 Save</button>
        <button class="hbtn" id="item-cancel2">Cancel</button></div>
    </div></div></div>`;
  document.body.insertAdjacentHTML('beforeend', html);
  const close = () => $('#item-overlay')?.remove();
  $('#item-cancel').addEventListener('click', close);
  $('#item-cancel2').addEventListener('click', close);
  $('#item-overlay').addEventListener('click', e => { if (e.target.id === 'item-overlay') close(); });
  $('#item-save').addEventListener('click', () => saveItem(category, item));
}

async function saveItem(category, item){
  const spec = state.schema[category];
  const values = {};
  for (const f of spec.fields){
    const el = $('#itf_' + f.key);
    if (!el) continue;
    values[f.key] = f.type === 'checkbox' ? el.checked : el.value;
  }
  state.editor = $('#itf_editor')?.value || 'curator';
  try {
    $('#item-save').disabled = true; $('#item-save').textContent = 'Saving...';
    let updated;
    if (item){
      updated = await api(`/api/v2/item/${encodeURIComponent(item.iri)}`, {
        method:'PUT', body:{ category, changes: values, disease: state.activeIri, editor: state.editor }});
    } else {
      updated = await api(`/api/v2/disease/${encodeURIComponent(state.activeIri)}/item`, {
        method:'POST', body:{ category, values, editor: state.editor }});
    }
    $('#item-overlay')?.remove();
    afterItemChange(updated, category);
    toast(item ? 'Item updated ✓' : 'Item added ✓');
  } catch (err){
    toast('Save failed: ' + err.message);
    $('#item-save').disabled = false; $('#item-save').textContent = '💾 Save';
  }
}

// ----------------------------------------------------------------- NEW DISEASE

let _ndTissueCache = null;
let _ndDiseaseCache = null;

async function _ndTissues() {
  if (!_ndTissueCache) _ndTissueCache = await api('/api/v2/tissues');
  return _ndTissueCache;
}
async function _ndDiseases() {
  if (!_ndDiseaseCache) _ndDiseaseCache = await api('/api/v2/diseases');
  return _ndDiseaseCache;
}

// prefill keys: label, definition, def_source, parent_iri, tissue_iris (array), synonyms, ...
async function openNewDiseaseModal(prefill = {}) {
  const [tissues, diseases] = await Promise.all([_ndTissues(), _ndDiseases()]);
  const today = new Date().toISOString().slice(0, 7);
  const login = state.githubLogin || '';
  const name = state.githubName || '';
  const authorDefault = name ? (name + (login ? ` | https://github.com/${login}` : '')) : '';
  const preFill = k => esc(prefill[k] || '');

  const tissueBoxes = tissues.map(t =>
    `<label class="tissue-check"><input type="checkbox" value="${esc(t.iri)}" ${(prefill.tissue_iris||[]).includes(t.iri)?'checked':''}> ${esc(t.name)}</label>`
  ).join('');

  const sortedDiseases = [...diseases].sort((a, b) => a.name.localeCompare(b.name));
  const parentOpts = sortedDiseases.map(d =>
    `<option value="${esc(d.iri)}" ${(prefill.parent_iri||'')=== d.iri?'selected':''}>${esc(d.name)}</option>`
  ).join('');

  const html = `<div class="modal-overlay" id="nd-overlay"><div class="modal nd-modal">
    <div class="modal-head"><h2>&#xFF0B; New Disease</h2><button class="hbtn" id="nd-close">&#x2715;</button></div>
    <div class="modal-body">
    <p class="nd-note">Fields marked <span class="nd-req">&#x2a;</span> are required. A provisional IRI (<code>ARI_new_…</code>) is assigned; curators set the final ARI ID after review.</p>

    <div class="nd-section-label">Required</div>
    <div class="field"><label>Label <span class="nd-req">&#x2a;</span></label>
      <input id="nd_label" value="${preFill('label')}" placeholder="e.g. Type 1 Diabetes Mellitus"></div>
    <div class="field"><label>Definition / Description <span class="nd-req">&#x2a;</span></label>
      <textarea id="nd_definition" style="min-height:72px" placeholder="A chronic autoimmune condition in which…">${preFill('definition')}</textarea></div>
    <div class="field"><label>Definition Sources <span class="nd-req">&#x2a;</span> <span style="font-weight:400;text-transform:none;font-size:11px;color:var(--muted)">(URL required; label optional)</span></label>
      <div id="nd_defsrc_list">${(()=>{
        const pr = prefill.def_source ? parseDefSrc(String(prefill.def_source)) : [];
        if (!pr.length) pr.push({text:'',url:''});
        return pr.map(c => defSrcRowHtml(c.text, c.url)).join('');
      })()}</div>
      <button type="button" class="hbtn" id="nd_defsrc_add" style="font-size:11px;margin-top:3px">&#xFF0B; Add source</button></div>
    <div class="field"><label>Target Tissue <span class="nd-req">&#x2a;</span></label>
      <div class="tissue-check-grid" id="nd_tissues">${tissueBoxes}</div></div>

    <div class="nd-section-label" style="margin-top:14px">Profile (auto-filled from GitHub)</div>
    <div class="field-grid">
      <div class="field"><label>Author</label>
        <input id="nd_authors" value="${esc(prefill.authors || authorDefault)}" placeholder="Name | profile URL"></div>
      <div class="field"><label>Author date (YYYY-MM)</label>
        <input id="nd_author_date" value="${esc(prefill.author_date || today)}" placeholder="2025-06"></div>
    </div>

    <div class="nd-section-label" style="margin-top:14px">Recommended</div>
    <div class="field"><label>Parent Disease (optional — sets hierarchy)</label>
      <select id="nd_parent"><option value="">— none —</option>${parentOpts}</select></div>
    <div class="field"><label>Synonyms (comma-separated)</label>
      <input id="nd_synonyms" value="${preFill('synonyms')}" placeholder="Synonym 1, Synonym 2"></div>
    <div class="field-grid">
      <div class="field"><label>Disease Category</label>
        <input id="nd_disease_category" value="${preFill('disease_category')}" placeholder="e.g. Autoimmune"></div>
      <div class="field"><label>Evidence Quality</label>
        <input id="nd_evidence_quality" value="${preFill('evidence_quality')}" placeholder="e.g. High"></div>
    </div>
    <div class="field"><label>Clinical Subtypes (comma-separated, format: Name - description)</label>
      <input id="nd_clinical_subtypes" value="${preFill('clinical_subtypes')}" placeholder="Subtype 1 - description, Subtype 2"></div>

    <details style="margin-top:14px">
      <summary class="nd-section-label" style="cursor:pointer;user-select:none;list-style:none">&#x25B8; Additional fields (optional)</summary>
      <div style="margin-top:8px">
        <div class="field-grid">
          <div class="field"><label>ICD-10 (comma-separated)</label><input id="nd_icd10" value="${preFill('icd10')}"></div>
          <div class="field"><label>SNOMED (comma-separated)</label><input id="nd_snomed" value="${preFill('snomed')}"></div>
          <div class="field"><label>DOID (comma-separated)</label><input id="nd_doid" value="${preFill('doid')}"></div>
          <div class="field"><label>UMLS (comma-separated)</label><input id="nd_umls" value="${preFill('umls')}"></div>
          <div class="field"><label>MONDO (comma-separated)</label><input id="nd_mondo" value="${preFill('mondo')}"></div>
          <div class="field"><label>MeSH (comma-separated)</label><input id="nd_mesh" value="${preFill('mesh')}"></div>
          <div class="field"><label>NCI (comma-separated)</label><input id="nd_nci" value="${preFill('nci')}"></div>
          <div class="field"><label>OMOP (comma-separated)</label><input id="nd_omop" value="${preFill('omop')}"></div>
        </div>
        <div class="field-grid">
          <div class="field"><label>Prevalence /100k</label><input type="number" id="nd_prevalence_per_100k" value="${preFill('prevalence_per_100k')}" step="any"></div>
          <div class="field"><label>Estimated cases</label><input id="nd_prevalence_value" value="${preFill('prevalence_value')}"></div>
          <div class="field"><label>Incidence rate</label><input id="nd_incidence_rate" value="${preFill('incidence_rate')}"></div>
          <div class="field"><label>Demographic bias</label><input id="nd_demographic_bias" value="${preFill('demographic_bias')}"></div>
          <div class="field"><label>Age range</label><input id="nd_age_range" value="${preFill('age_range')}"></div>
        </div>
        <div class="field"><label>Prevalence description</label><textarea id="nd_prevalence_desc">${preFill('prevalence_desc')}</textarea></div>
      </div>
    </details>

    <div class="field" style="margin-top:14px"><label>Editor name</label>
      <input id="nd_editor" value="${esc(state.editor)}"></div>
    <div class="edit-actions">
      <button class="hbtn primary" id="nd-save">&#xFF0B; Create Disease</button>
      <button class="hbtn" id="nd-cancel">Cancel</button>
    </div></div></div></div>`;

  document.body.insertAdjacentHTML('beforeend', html);
  const close = () => { $('#nd-overlay')?.remove(); _ndDiseaseCache = null; };
  $('#nd-close').addEventListener('click', close);
  $('#nd-cancel').addEventListener('click', close);
  $('#nd-overlay').addEventListener('click', e => { if (e.target.id === 'nd-overlay') close(); });
  $('#nd_defsrc_add')?.addEventListener('click', () =>
    $('#nd_defsrc_list').insertAdjacentHTML('beforeend', defSrcRowHtml('', '')));
  $('#nd-save').addEventListener('click', saveNewDisease);
}

async function saveNewDisease() {
  const v = id => ($(id)?.value ?? '').trim();
  const lbl = v('#nd_label');
  const defn = v('#nd_definition');
  const def_source = _collectDefSrcs('nd_defsrc_list');
  const tissue_iris = [...document.querySelectorAll('#nd_tissues input:checked')].map(c => c.value);

  if (!lbl)               { toast('Label is required'); return; }
  if (!defn)              { toast('Definition is required'); return; }
  if (!def_source.length) { toast('At least one definition source is required'); return; }
  if (!tissue_iris.length){ toast('Select at least one target tissue'); return; }

  state.editor = v('#nd_editor') || 'curator';
  const data = {
    label: lbl, definition: defn, def_source, tissue_iris,
    authors:           v('#nd_authors'),
    author_date:       v('#nd_author_date'),
    parent_iri:        v('#nd_parent'),
    synonyms:          v('#nd_synonyms'),
    disease_category:  v('#nd_disease_category'),
    evidence_quality:  v('#nd_evidence_quality'),
    clinical_subtypes: v('#nd_clinical_subtypes'),
    icd10: v('#nd_icd10'), snomed: v('#nd_snomed'), doid: v('#nd_doid'),
    umls: v('#nd_umls'), mondo: v('#nd_mondo'), mesh: v('#nd_mesh'),
    nci: v('#nd_nci'), omop: v('#nd_omop'),
    prevalence_per_100k: v('#nd_prevalence_per_100k'),
    prevalence_value:    v('#nd_prevalence_value'),
    incidence_rate:      v('#nd_incidence_rate'),
    demographic_bias:    v('#nd_demographic_bias'),
    age_range:           v('#nd_age_range'),
    prevalence_desc:     v('#nd_prevalence_desc'),
  };

  const btn = $('#nd-save');
  try {
    btn.disabled = true; btn.textContent = 'Creating…';
    const created = await api('/api/v2/disease', { method: 'POST', body: { data, editor: state.editor } });
    _ndTissueCache = null;
    $('#nd-overlay')?.remove();
    toast(`Created: ${created.name}`);
    await init();
    await selectDisease(created.iri);
  } catch (err) {
    toast('Create failed: ' + err.message);
    btn.disabled = false; btn.textContent = '＋ Create Disease';
  }
}

// Wire the header button (runs after DOM is ready because this file loads last in <body>)
$('#new-disease-btn')?.addEventListener('click', () => openNewDiseaseModal());

async function deleteItem(category, item){
  if (!confirm(`Delete “${item.name}”? This removes it from the ontology.`)) return;
  try {
    const updated = await api(`/api/v2/item/${encodeURIComponent(item.iri)}`, {
      method:'DELETE', body:{ category, disease: state.activeIri, editor: state.editor }});
    afterItemChange(updated, category);
    toast('Item deleted ✓');
  } catch (err){ toast('Delete failed: ' + err.message); }
}

function afterItemChange(updated, category){
  state.detail = updated;
  renderDetail(updated);
  init();
  state.activeBox = category;
  $('#layout').classList.add('split');
  $('#right-col').classList.add('open');
  $('#detail-pane').querySelectorAll('.box').forEach(b => b.classList.toggle('active', b.dataset.box === category));
  renderItemEditor(updated, category, $('#right-panel-content'));
}

