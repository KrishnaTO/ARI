// Middle panel: selecting a disease, rendering the ontology detail header and
// the narrative "disease story" of selectable category boxes.

async function selectDisease(iri){
  state.activeIri = iri;
  state.editMode = false;
  closeRightPanel();
  $('#tree-pane').querySelectorAll('.selected').forEach(el => el.classList.remove('selected'));
  $('#tree-pane').querySelectorAll(`[data-iri="${CSS.escape(iri)}"]`).forEach(el => el.classList.add('selected'));
  const d = await api(`/api/v2/disease/${encodeURIComponent(iri)}`);
  state.detail = d;
  $('#edit-toggle').disabled = false;
  renderDetail(d);
}

// Linkify "PMID: 12345" references inside a source string.
function linkifySource(text){
  return esc(text).replace(/PMID:?\s*(\d+)/gi, (m, id) =>
    `<a href="https://pubmed.ncbi.nlm.nih.gov/${id}/" target="_blank" rel="noopener">PMID: ${id}</a>`);
}

function renderDetail(d){
  const obs = d.obsolete;
  let html = `<div class="detail${obs ? ' obsolete' : ''}">
    <h1>${esc(d.name)}${obs ? ' <span class="obsolete-tag">(obsolete)</span>' : ''}</h1>
    <div class="iri">${esc(d.iri)}</div>`;
  if (d.ari_id?.length) html += `<div class="ari-id">ARI ID: ${esc(d.ari_id[0])}</div>`;

  if (state.editMode){
    html += `<div class="edit-banner">&#9998; <strong>Editing mode</strong> &mdash; edit the disease fields, or click a category below to add / edit / delete its data items.
      <button class="hbtn" id="edit-fields-btn">Edit disease fields</button></div>`;
  }

  if (d.parent_disease?.length){
    html += `<div style="font-size:12px;margin-bottom:8px">Subtype of <a href="#" class="parent-link" data-iri="${esc(d.parent_disease[0].iri)}">${esc(d.parent_disease[0].name)}</a></div>`;
  }
  if (d.subtypes?.length){
    html += `<div style="font-size:12px;margin-bottom:8px">Subtypes: ${d.subtypes.map(s => `<a href="#" class="parent-link" data-iri="${esc(s.iri)}">${esc(s.name)}</a>`).join(', ')}</div>`;
  }

  if (d.definition) html += `<div class="definition">${mdToHtml(d.definition)}</div>`;
  // Definition source(s) — parsed as "Author Year; URL" pairs, rendered as
  // hyperlinks.  Pubmed URLs already embedded in def_source are not shown twice.
  if (d.def_source?.length || d.pubmed?.length) {
    const shownUrls = new Set();
    const cites = [];
    for (const s of (d.def_source || [])) {
      for (const c of parseDefSrc(String(s))) {
        if (c.url) shownUrls.add(c.url);
        cites.push(c);
      }
    }
    for (const p of (d.pubmed || [])) {
      const u = String(p || '').trim();
      if (u && !shownUrls.has(u)) cites.push({ text: '', url: u });
    }
    if (cites.length) {
      html += `<div class="def-sources">`;
      for (const c of cites) {
        if (c.url) {
          html += `<div class="def-source-item"><a href="${esc(c.url)}" target="_blank" rel="noopener">${c.text ? esc(c.text) : 'Source'} &#8599;</a></div>`;
        } else if (c.text) {
          html += `<div class="def-source-item"><span class="src-label">Source</span> ${esc(c.text)}</div>`;
        }
      }
      html += `</div>`;
    }
  }

  html += '<div class="meta">';
  if (d.disease_category?.length) html += `<span class="tag">${esc(d.disease_category[0])}</span>`;
  if (d.evidence_quality?.length) html += `<span class="tag">Evidence: ${esc(d.evidence_quality[0])}</span>`;
  if (d.version?.length) html += `<span class="tag">v${esc(d.version[0])}</span>`;
  html += '</div>';

  // Database cross-references as linkouts
  const xrefs = [
    ['icd10','ICD-10', d.icd10], ['snomed','SNOMED', d.snomed], ['doid','DOID', d.doid],
    ['umls','UMLS', d.umls], ['mondo','MONDO', d.mondo], ['mesh','MeSH', d.mesh],
    ['nci','NCI', d.nci], ['omop','OMOP', d.omop],
  ].filter(x => x[2]?.length);
  if (xrefs.length){
    html += '<div class="section-label">Database cross-references</div><div class="xref-row">';
    for (const [kind, lbl, vals] of xrefs){
      for (const v of vals){
        html += `<a class="xref" href="${esc(xrefLink(kind, v))}" target="_blank" rel="noopener"><b>${lbl}</b> <code>${esc(v)}</code> &#8599;</a>`;
      }
    }
    html += '</div>';
  }

  if (d.synonyms?.length){
    html += `<div class="section-label">Synonyms</div><div class="synonyms">${d.synonyms.map(s => `<span>${esc(s)}</span>`).join('')}</div>`;
  }

  if (d.tissue_targets?.length){
    html += `<div class="section-label">Target tissue</div><div style="font-size:12px;margin-bottom:4px">${d.tissue_targets.map(t => `<span class="tissue-chip">${esc(t.name)}</span>`).join('')}</div>`;
  }

  // Clinical subtypes / variants (from the report Subtypes sheet): "name - description"
  if (d.clinical_subtypes?.length){
    html += `<div class="section-label">Clinical subtypes</div><ul class="subtype-list">`;
    for (const sub of d.clinical_subtypes){
      const [name, ...rest] = String(sub).split(' - ');
      const desc = rest.join(' - ');
      const btn = state.editMode
        ? ` <button class="hbtn subtype-new-btn" data-subtype-name="${esc(name)}" title="Create this subtype as a new disease (child of this disease)">&#xFF0B; New disease</button>`
        : '';
      html += `<li><strong>${esc(name)}</strong>${desc ? ' &mdash; ' + esc(desc) : ''}${btn}</li>`;
    }
    html += `</ul>`;
  }

  // External reference links (Cleveland Clinic, Mayo, Healthline, registries, ...)
  if (d.ref_links?.length){
    html += `<div class="section-label">External references</div><div class="ref-links">`;
    for (const ref of d.ref_links){
      const idx = String(ref).lastIndexOf(' | ');
      const text = idx >= 0 ? ref.slice(0, idx) : ref;
      const url = idx >= 0 ? ref.slice(idx + 3) : ref;
      html += `<a class="ref-link" href="${esc(url)}" target="_blank" rel="noopener">${esc(text)} &#8599;</a>`;
    }
    html += `</div>`;
  }

  // Profile authorship / byline
  if (d.authors?.length){
    const [who, link] = String(d.authors[0]).split(' | ');
    const date = d.author_date?.length ? ` (${esc(d.author_date[0])})` : '';
    const whoHtml = link ? `<a href="${esc(link)}" target="_blank" rel="noopener">${esc(who)}</a>` : esc(who);
    html += `<div class="byline">Profile by ${whoHtml}${date}</div>`;
  }

  // Disease data organized as a narrative story; boxes grouped by aspect category
  // (per the immunological data model) with each concept's description as a subtitle.
  const boxByKey = {};
  for (const b of boxDefs(d)) boxByKey[b.key] = b;
  const boxNote = b => b.count > 0 ? b.count + ' items' : (state.editMode && state.schema[b.key] ? '+ add' : (b.note || ''));
  const boxHtml = b => `<div class="box" data-box="${b.key}"><div class="icon">${b.icon}</div><div class="label">${esc(b.label)}</div><div class="count">${boxNote(b)}</div></div>`;
  html += `<div class="section-label">Disease story</div><div class="story">`;
  for (const grp of STORY_GROUPS){
    const keys = grp.keys.filter(k => { const b = boxByKey[k]; return b && (b.show || (state.editMode && state.schema[k])); });
    if (!keys.length) continue;
    html += `<div class="story-step"><div class="story-head"><span class="story-num${grp.num ? '' : ' muted'}">${grp.num ?? '•'}</span>`+
      `<span class="story-title">${esc(grp.title)}</span><span class="story-hint">${esc(grp.hint)}</span></div>`;
    if (grp.aspectGroups){
      // sub-group the boxes under their aspect category (only this step)
      const aspects = [], byAspect = {};
      for (const k of keys){
        const asp = (BOX_META[k] && BOX_META[k].aspect) || 'Other';
        if (!byAspect[asp]){ byAspect[asp] = []; aspects.push(asp); }
        byAspect[asp].push(k);
      }
      for (const asp of aspects){
        html += `<div class="aspect"><div class="aspect-name">${esc(asp)}</div><div class="box-grid">`;
        for (const k of byAspect[asp]) html += boxHtml(boxByKey[k]);
        html += `</div></div>`;
      }
    } else {
      html += `<div class="box-grid">`;
      for (const k of keys) html += boxHtml(boxByKey[k]);
      html += `</div>`;
    }
    html += `</div>`;
  }
  html += '</div></div>';

  $('#detail-pane').innerHTML = html;

  $('#detail-pane').querySelectorAll('.parent-link').forEach(a =>
    a.addEventListener('click', ev => { ev.preventDefault(); selectDisease(a.dataset.iri); }));

  $('#detail-pane').querySelectorAll('.subtype-new-btn').forEach(btn =>
    btn.addEventListener('click', () =>
      openNewDiseaseModal({ label: btn.dataset.subtypeName, parent_iri: d.iri })));

  const efb = $('#edit-fields-btn');
  if (efb) efb.addEventListener('click', () => openDiseaseFieldEditor(state.detail));

  $('#detail-pane').querySelectorAll('.box').forEach(box => {
    box.addEventListener('click', () => {
      const key = box.dataset.box;
      if (state.activeBox === key){ closeRightPanel(); return; }
      state.activeBox = key;
      $('#detail-pane').querySelectorAll('.box').forEach(b => b.classList.remove('active'));
      box.classList.add('active');
      openBoxDetail(d, key);
    });
  });
}

function boxDefs(d){
  return [
    { key:'prevalence', icon:'📊', label:'Prevalence', count: 0, note:'data', show: (d.prevalence_per_100k?.length || d.prevalence_desc?.length) },
    { key:'symptoms', icon:'🤒', label:'Symptoms', count: d.symptoms?.length||0, show: d.symptoms?.length },
    { key:'environmental', icon:'🌍', label:'Environmental', count: d.environmental_factors?.length||0, show: d.environmental_factors?.length },
    { key:'antibodies', icon:'🧬', label:'Antibodies', count: d.antibodies?.length||0, show: d.antibodies?.length },
    { key:'treatments', icon:'💊', label:'Treatments', count: d.treatments?.length||0, show: d.treatments?.length },
    { key:'etiology', icon:'🔬', label:'Etiology', count: d.etiology?.length||0, show: d.etiology?.length },
    { key:'genetic', icon:'🧬', label:'Genetics', count: d.genetic?.length||0, show: d.genetic?.length },
    { key:'biomarkers', icon:'🩸', label:'Biomarkers', count: d.biomarkers?.length||0, show: d.biomarkers?.length },
    { key:'pathophysiology', icon:'🗺️', label:'Pathophysiology', count: d.pathway?.length||0, show: d.pathway?.length },
    { key:'cytokines', icon:'💉', label:'Cytokines', count: d.cytokines?.length||0, show: d.cytokines?.length },
    { key:'tcells', icon:'🔴', label:'T-Cells', count: d.tcells?.length||0, show: d.tcells?.length },
    { key:'apcs', icon:'🟡', label:'APCs', count: d.apcs?.length||0, show: d.apcs?.length },
    { key:'transcription', icon:'📝', label:'Transcription Factors', count: d.transcription_factors?.length||0, show: d.transcription_factors?.length },
    { key:'innate', icon:'🛡️', label:'Innate Immunity', count: d.innate_components?.length||0, show: d.innate_components?.length },
    { key:'complement', icon:'🔗', label:'Complement', count: d.complement?.length||0, show: d.complement?.length },
    { key:'receptors', icon:'📡', label:'Receptors', count: d.receptors?.length||0, show: d.receptors?.length },
    { key:'netosis', icon:'🕸️', label:'NETosis', count: d.netosis?.length||0, show: d.netosis?.length },
    { key:'inflammasome', icon:'🔥', label:'Inflammasome', count: d.inflammasome?.length||0, show: d.inflammasome?.length },
    { key:'apr', icon:'⚡', label:'Acute Phase Reactants', count: d.acute_phase_reactants?.length||0, show: d.acute_phase_reactants?.length },
    { key:'antigens', icon:'🎯', label:'Antigens', count: d.antigens?.length||0, show: d.antigens?.length },
    { key:'changelog', icon:'📋', label:'Change Log', count: d.changelog?.length||0, show: true, note:'history' },
    { key:'feedback', icon:'💬', label:'Feedback', count: 0, show: true, note:'comment' },
  ];
}
