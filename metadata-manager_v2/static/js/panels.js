// Right panel: opening a category's deep-dive (read views) and the renderers
// for each category. The graph renderer lives in graph.js; the item editors
// live in editor.js.

function openBoxDetail(d, key){
  $('#layout').classList.add('split');
  $('#right-col').classList.add('open');
  const panel = $('#right-panel-content');
  if (state.editMode && state.schema[key]){ renderItemEditor(d, key, panel); return; }
  renderReadView(d, key, panel);
}

function renderReadView(d, key, panel){
  const handlers = {
    prevalence: renderPrevalence, symptoms: renderSymptoms, environmental: renderEnvironmental,
    antibodies: renderAntibodies, treatments: renderTreatments, etiology: renderEtiology,
    genetic: renderGenetic, biomarkers: renderBiomarkers, pathophysiology: renderPathophysiology,
    changelog: renderChangelog,
  };
  try {
    if (handlers[key]) handlers[key](d, panel);
    else renderImmuneList(d, panel, key);
  } catch (err){
    console.error('render', key, err);
  }
  const h2 = panel.querySelector('h2');
  if (h2){
    // Concept description under the title.
    if (!panel.querySelector('.panel-desc')) h2.insertAdjacentHTML('afterend', panelDescHTML(key));
    // Make item editing reachable directly from any editable category's deep-dive.
    if (state.schema[key] && !h2.querySelector('.edit-items-btn')){
      h2.insertAdjacentHTML('beforeend', ` <button class="hbtn edit-items-btn">✎ Edit items</button>`);
      h2.querySelector('.edit-items-btn').addEventListener('click', () => renderItemEditor(d, key, panel));
    }
  }
}

function closeRightPanel(){
  state.activeBox = null;
  $('#right-col').classList.remove('open');
  $('#layout').classList.remove('split');
  $('#detail-pane')?.querySelectorAll('.box').forEach(b => b.classList.remove('active'));
}
window.closeRightPanel = closeRightPanel;

const closeHeader = title => `<button class="close-btn" onclick="closeRightPanel()">✕ Close</button><h2>${title}</h2>`;

function renderPrevalence(d, panel){
  let html = closeHeader('📊 Prevalence &amp; Epidemiology');
  const p100k = first(d.prevalence_per_100k) || 0;
  const pVal = first(d.prevalence_value) || 0;
  html += `<div class="prev-stats">
    <div class="stat-card"><div class="value">${p100k}</div><div class="lbl">Per 100,000</div></div>
    <div class="stat-card"><div class="value">${Number(pVal).toLocaleString()}</div><div class="lbl">US Cases</div></div>
    <div class="stat-card"><div class="value">${esc(first(d.incidence_rate) || 'N/A')}</div><div class="lbl">Incidence</div></div>
  </div>`;
  html += `<div class="chart-container"><canvas id="prevChart"></canvas></div>`;

  // Table view of prevalence metrics + sources
  html += `<table class="data-table"><thead><tr><th>Metric</th><th>Value</th></tr></thead><tbody>`;
  const rows = [
    ['Prevalence (per 100k)', p100k || '—'],
    ['Estimated US cases', pVal ? Number(pVal).toLocaleString() : '—'],
    ['Incidence rate', esc(first(d.incidence_rate) || '—')],
    ['Demographic bias', esc(first(d.demographic_bias) || '—')],
    ['Age range', esc(first(d.age_range) || '—')],
    ['Description', esc(first(d.prevalence_desc) || '—')],
  ];
  for (const [k,v] of rows) html += `<tr><td><strong>${k}</strong></td><td>${v}</td></tr>`;
  html += `</tbody></table>`;
  if (d.pubmed?.length || d.def_source?.length){
    html += `<div class="card src" style="margin-top:8px">Sources: ${
      (d.def_source||[]).map(s=>esc(s)).join('; ')}${(d.pubmed||[]).map(p=>` <a href="${esc(p)}" target="_blank">PubMed</a>`).join('')}</div>`;
  }
  panel.innerHTML = html;

  const ctx = document.getElementById('prevChart');
  if (ctx && p100k > 0){
    new Chart(ctx, {
      type: 'bar',
      data: { labels: ['Per 100k', 'US cases (÷1000)'],
        datasets: [{ label: 'Prevalence', data: [p100k, pVal/1000], backgroundColor: ['#2563eb','#0891b2'], borderRadius: 4 }] },
      options: { responsive: true, maintainAspectRatio: false, plugins: { legend: { display: false } } }
    });
  }
}

function symBadge(lik){
  const l = (lik||'').toLowerCase();
  if (l.includes('very common') || l.includes('common')) return 'badge-common';
  if (l.includes('rare') || l.includes('weak')) return 'badge-rare';
  return 'badge-moderate';
}

function renderSymptoms(d, panel){
  let html = closeHeader('🤒 Symptoms');
  if (!d.symptoms?.length){ panel.innerHTML = html + '<div class="empty-state">No symptoms data.</div>'; return; }
  html += `<table class="data-table"><thead><tr><th>Symptom</th><th>Likelihood</th><th>Description</th><th>Ref</th></tr></thead><tbody>`;
  for (const s of d.symptoms){
    const hpo = first(s.seeAlso);
    const hpoLink = hpo ? `<a href="https://hpo.jax.org/app/browse/term/${esc(hpo)}" target="_blank">${esc(hpo)}</a>` : '';
    const src = (s.source||[]).map(x => `<a href="${esc(x)}" target="_blank">PubMed</a>`).join(' ');
    html += `<tr class="${s.obsolete?'obsolete':''}"><td><strong>${esc(s.name)}</strong>${s.obsolete?' <span class="obsolete-tag">(obsolete)</span>':''}</td>`+
      `<td><span class="badge ${symBadge(first(s.likelihood))}">${esc(first(s.likelihood))}</span></td>`+
      `<td>${esc(first(s.description))}</td><td class="src">${hpoLink} ${src}</td></tr>`;
  }
  html += `</tbody></table>`;
  html += `<div class="section-label">Symptom word cloud</div><div class="chart-container" id="wordcloud-container"><svg class="wordcloud" id="wordcloud"></svg></div>`;
  panel.innerHTML = html;

  const words = d.symptoms.filter(s=>!s.obsolete).map(s => {
    const l = (first(s.likelihood)||'').toLowerCase();
    let size = 18; if (l.includes('common')) size = 28; if (l.includes('very common')) size = 40; if (l.includes('moderate')) size = 22;
    return { text: s.name, size };
  });
  const svg = d3.select('#wordcloud');
  if (svg.node() && words.length){
    const width = $('#wordcloud-container').clientWidth || 400, height = 220;
    svg.attr('viewBox', `0 0 ${width} ${height}`);
    d3.layout.cloud().size([width, height]).words(words).padding(4).rotate(0)
      .font('system-ui').fontSize(d => d.size)
      .on('end', ws => {
        svg.selectAll('*').remove();
        svg.append('g').attr('transform', `translate(${width/2},${height/2})`)
          .selectAll('text').data(ws).enter().append('text')
          .style('font-family','system-ui').style('font-size', d => d.size+'px')
          .style('fill', () => d3.schemeCategory10[Math.floor(Math.random()*10)])
          .attr('text-anchor','middle').attr('transform', d => `translate(${d.x},${d.y})`)
          .text(d => d.text);
      }).start();
  }
}

function renderEnvironmental(d, panel){
  let html = closeHeader('🌍 Environmental Triggers');
  if (!d.environmental_factors?.length){ panel.innerHTML = html + '<div class="empty-state">No environmental triggers.</div>'; return; }
  for (const f of d.environmental_factors){
    html += `<div class="card${f.obsolete?' obsolete':''}"><h3>${esc(f.name)} <span class="badge badge-weak">${esc(first(f.likelihood))}</span></h3>`+
      `<div class="desc">${esc(first(f.description))}</div>`+
      `<div class="src">${(f.source||[]).map(s => `<a href="${esc(s)}" target="_blank">${esc(s)}</a>`).join('<br>')}</div></div>`;
  }
  panel.innerHTML = html;
}

function renderAntibodies(d, panel){
  let html = closeHeader('🧬 Autoantibodies');
  if (!d.antibodies?.length){ panel.innerHTML = html + '<div class="empty-state">No antibody data.</div>'; return; }
  html += `<p style="font-size:12px;color:var(--muted);margin:0 0 8px">Autoantibodies are produced at the <span class="ab-highlight">autoantibody production</span> step of the pathophysiology map. Select a row for details.</p>`;
  html += pathographHTML(d, { compact: true });
  html += `<div class="section-label">Autoantibody panel</div>`;
  html += `<table class="data-table"><thead><tr><th>Antibody</th><th>Frequency</th><th>Diagnostic value</th></tr></thead><tbody>`;
  d.antibodies.forEach((ab, i) => {
    html += `<tr class="clickable ${ab.obsolete?'obsolete':''}" data-ab="${i}"><td><strong>${esc(ab.name)}</strong>${ab.obsolete?' <span class="obsolete-tag">(obsolete)</span>':''}</td>`+
      `<td>${esc(first(ab.frequency))}</td><td>${esc(first(ab.diagnostic_value))}</td></tr>`;
  });
  html += `</tbody></table><div id="ab-detail"></div>`;
  panel.innerHTML = html;
  panel.querySelectorAll('tr[data-ab]').forEach(tr => tr.addEventListener('click', () => {
    const ab = d.antibodies[+tr.dataset.ab];
    $('#ab-detail').innerHTML = `<div class="card"><h3>${esc(ab.name)}</h3>`+
      `<div class="desc"><strong>Frequency:</strong> ${esc(first(ab.frequency))}<br><strong>Diagnostic value:</strong> ${esc(first(ab.diagnostic_value))}</div>`+
      `<div class="src">${(ab.source||[]).map(s => `<a href="${esc(s)}" target="_blank">${esc(s)}</a>`).join('<br>')}</div>`+
      `<div style="font-size:11px;color:var(--muted);margin-top:6px">IRI: ${esc(ab.iri)}</div></div>`;
  }));
}

function renderTreatments(d, panel){
  let html = closeHeader('💊 Treatments');
  if (!d.treatments?.length){ panel.innerHTML = html + '<div class="empty-state">No treatment data.</div>'; return; }
  for (const t of d.treatments){
    html += `<div class="card${t.obsolete?' obsolete':''}"><h3>${esc(t.name)} <span style="font-size:11px;color:var(--muted);font-weight:400">${esc((t.type||[]).join(', '))}</span></h3>`+
      `<div class="desc">${esc(first(t.description))}</div>`+
      `<div style="margin:4px 0"><span class="badge" style="background:var(--success);color:#fff">${esc(first(t.fda_status))}</span></div>`+
      `<div class="src">${(t.source||[]).map(s => `<a href="${esc(s)}" target="_blank">${esc(s)}</a>`).join('<br>')}</div></div>`;
  }
  panel.innerHTML = html;
}

function renderEtiology(d, panel){
  let html = closeHeader('🔬 Etiology');
  if (!d.etiology?.length){ panel.innerHTML = html + '<div class="empty-state">No etiology data.</div>'; return; }
  for (const e of d.etiology){
    const origin = first(e.origin_type);
    const oc = origin.toLowerCase();
    const badge = oc.includes('genetic') ? 'badge-genetic' : oc.includes('external') ? 'badge-external' : 'badge-idiopathic';
    html += `<div class="card${e.obsolete?' obsolete':''}"><h3>${esc(e.name)} <span class="badge ${badge}">${esc(origin||'Unclassified')}</span></h3>`+
      `<div class="desc">${esc(first(e.description))}</div>`+
      (first(e.excerpt) ? `<div class="excerpt">${esc(first(e.excerpt))}</div>` : '')+
      `<div class="src">${(e.source||[]).map(s => `<a href="${esc(s)}" target="_blank">${esc(s)}</a>`).join('<br>')}</div></div>`;
  }
  panel.innerHTML = html;
}

function renderGenetic(d, panel){
  let html = closeHeader('🧬 Genetic Associations');
  if (!d.genetic?.length){ panel.innerHTML = html + '<div class="empty-state">No genetic data.</div>'; return; }
  html += `<table class="data-table"><thead><tr><th>Gene / HLA</th><th>Locus</th><th>Product</th><th>Effect</th><th>OR</th><th>Source</th></tr></thead><tbody>`;
  for (const g of d.genetic){
    const src = (g.source||[]).map(s => `<a href="${esc(s)}" target="_blank">PubMed</a>`).join(', ');
    html += `<tr class="${g.obsolete?'obsolete':''}"><td><strong>${esc(g.name)}</strong></td><td>${esc(first(g.locus))}</td><td>${esc(first(g.product))}</td>`+
      `<td>${esc(first(g.risk_effect) || first(g.hla_effect))}</td><td>${esc(first(g.odds_ratio))}</td><td class="src">${src || '—'}</td></tr>`;
    if (g.hla_mechanism?.length){
      html += `<tr><td colspan="6" style="font-size:11px;color:var(--muted);background:#f8fafc">↳ ${esc(first(g.hla_mechanism))}</td></tr>`;
    }
  }
  html += `</tbody></table>`;
  panel.innerHTML = html;
}

function renderBiomarkers(d, panel){
  let html = closeHeader('🩸 Biochemical Markers');
  if (!d.biomarkers?.length){ panel.innerHTML = html + '<div class="empty-state">No biomarker data.</div>'; return; }
  html += `<table class="data-table"><thead><tr><th>Marker</th><th>Description</th><th>Diagnostic use</th><th>Source</th></tr></thead><tbody>`;
  for (const m of d.biomarkers){
    html += `<tr class="${m.obsolete?'obsolete':''}"><td><strong>${esc(m.name)}</strong></td><td>${esc(m.description)}</td>`+
      `<td>${esc(first(m.diagnostic_use))}</td><td class="src">${(m.source||[]).map(s => `<a href="${esc(s)}" target="_blank">PubMed</a>`).join(', ')}</td></tr>`;
  }
  html += `</tbody></table>`;
  panel.innerHTML = html;
}

// Reusable compact pathograph (vertical flow) — used by the antibodies panel.
function pathographHTML(d, opts={}){
  if (!d.pathway?.length) return '<div class="empty-state">No pathophysiology pathway.</div>';
  let h = '<div class="patho-map">';
  d.pathway.forEach((p, i) => {
    const cat = (p.category||'').toLowerCase();
    const isAb = cat === 'antibody';
    const nameHtml = isAb ? `<span class="ab-highlight">${esc(p.name)}</span>` : esc(p.name);
    h += `<div class="patho-step cat-${cat}${isAb?' antibody':''}" data-step="${i}">`+
      `<div class="ord">${esc(p.order)}</div>`+
      `<div><h4>${nameHtml} <span class="cat-pill">${esc(p.category)}</span></h4>`+
      (opts.compact ? '' : `<p>${esc(p.description)}</p>`)+
      `</div></div>`;
    if (i < d.pathway.length - 1) h += `<div class="patho-arrow">↓</div>`;
  });
  h += '</div>';
  return h;
}

function renderImmuneList(d, panel, key){
  const map = {
    cytokines: { title:'💉 Cytokines', data: d.cytokines },
    tcells: { title:'🔴 T-Cell Subsets', data: d.tcells },
    apcs: { title:'🟡 Antigen Presenting Cells', data: d.apcs },
    transcription: { title:'📝 Transcription Factors', data: d.transcription_factors },
    innate: { title:'🛡️ Innate Immune Components', data: d.innate_components },
    complement: { title:'🔗 Complement Components', data: d.complement },
    receptors: { title:'📡 Receptors', data: d.receptors },
    netosis: { title:'🕸️ NETosis', data: d.netosis },
    inflammasome: { title:'🔥 Inflammasome', data: d.inflammasome },
    apr: { title:'⚡ Acute Phase Reactants', data: d.acute_phase_reactants },
    antigens: { title:'🎯 Antigens', data: d.antigens },
  };
  const info = map[key];
  let html = closeHeader(info ? info.title : 'Details');
  const data = info?.data || [];
  if (!data.length){ panel.innerHTML = html + '<div class="empty-state">No data.</div>'; return; }
  html += `<table class="data-table"><thead><tr><th>Name</th><th>Details</th><th>Relevance</th><th>Source</th></tr></thead><tbody>`;
  for (const item of data){
    const src = (item.source||[]).map(s => `<a href="${esc(s)}" target="_blank">PubMed</a>`).join(', ');
    html += `<tr class="${item.obsolete?'obsolete':''}"><td><strong>${esc(item.name)}</strong></td>`+
      `<td style="font-size:12px">${esc(first(item.description))}</td>`+
      `<td><span class="badge badge-moderate">${esc(first(item.relevance))}</span></td>`+
      `<td class="src">${src || '—'}</td></tr>`;
  }
  html += `</tbody></table>`;
  panel.innerHTML = html;
}

function renderChangelog(d, panel){
  let html = closeHeader('📋 Change Log');
  if (!d.changelog?.length){ panel.innerHTML = html + '<div class="empty-state">No changelog entries.</div>'; return; }
  for (const c of [...d.changelog].reverse()){
    html += `<div class="card"><div class="desc">${esc(c)}</div></div>`;
  }
  panel.innerHTML = html;
}
