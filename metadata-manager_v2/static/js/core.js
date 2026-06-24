// Core utilities, shared state, constants, and the API helper.
// Loaded first; everything below lives in global scope and is used by the
// other js/*.js modules at runtime.

const $ = s => document.querySelector(s);
const esc = s => String(s ?? '').replace(/[&<>"']/g, c => ({'&':'&','<':'<','>':'>','"':'"',"'":'&#39;'}[c]));
const first = a => (Array.isArray(a) ? a[0] : a) ?? '';

// Base path for when the app is served under a subpath (e.g. /ari-editor).
// Auto-detected from the page URL: if the first path segment matches a known
// prefix, we use it. Falls back to empty string when served at root.
// To set a custom prefix, put <script>window.BASE_PATH='/my-prefix'</script>
// in the HTML <head> before loading core.js.
const BASE_PATH = (() => {
  if (typeof window.BASE_PATH !== 'undefined') return window.BASE_PATH;
  const m = window.location.pathname.match(/^\/([^/]+)/);
  const knownPrefixes = ['ari-editor'];
  return m && knownPrefixes.includes(m[1]) ? '/' + m[1] : '';
})();

let state = { activeIri: null, activeTab: 'alphabetical', activeBox: null, editMode: false, detail: null, schema: {}, editor: 'curator', githubName: null };

// --------------------------------------------------------------- markdown
// Minimal, HTML-safe markdown renderer (escapes first, then formats). Used for
// disease definition and definition sources.
function mdInline(t){
  t = String(t == null ? '' : t);
  t = t.replace(/`([^`]+)`/g, '<code>$1</code>');
  t = t.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>');
  t = t.replace(/(^|[^*])\*([^*\n]+)\*/g, '$1<em>$2</em>');
  t = t.replace(/\[([^\]]+)\]\((https?:\/\/[^\s)]+)\)/g, '<a href="$2" target="_blank" rel="noopener">$1</a>');
  t = t.replace(/(^|[\s(])(https?:\/\/[^\s<)]+)/g, function(m,p,u){ return p + '<a href="' + u + '" target="_blank" rel="noopener">' + u + '</a>'; });
  t = t.replace(/PMID:?\s*(\d+)/gi, '<a href="https://pubmed.ncbi.nlm.nih.gov/$1/" target="_blank" rel="noopener">PMID: $1</a>');
  return t;
}
function mdToHtml(src){
  var lines = esc(src == null ? '' : String(src)).split(/\r?\n/);
  var html = '', list = null, para = [];
  function flushPara(){ if (para.length){ html += '<p>' + mdInline(para.join('<br>')) + '</p>'; para = []; } }
  function flushList(){ if (list){ html += '</' + list + '>'; list = null; } }
  for (var i = 0; i < lines.length; i++){
    var line = lines[i].trim(), m;
    if (!line){ flushPara(); flushList(); continue; }
    if (m = line.match(/^(#{1,6})\s+(.*)$/)){ flushPara(); flushList(); var lv = m[1].length; html += '<h' + lv + '>' + mdInline(m[2]) + '</h' + lv + '>'; continue; }
    if (m = line.match(/^[-*+]\s+(.*)$/)){ flushPara(); if (list !== 'ul'){ flushList(); html += '<ul>'; list = 'ul'; } html += '<li>' + mdInline(m[1]) + '</li>'; continue; }
    if (m = line.match(/^\d+\.\s+(.*)$/)){ flushPara(); if (list !== 'ol'){ flushList(); html += '<ol>'; list = 'ol'; } html += '<li>' + mdInline(m[1]) + '</li>'; continue; }
    if (m = line.match(/^>\s?(.*)$/)){ flushPara(); flushList(); html += '<blockquote>' + mdInline(m[1]) + '</blockquote>'; continue; }
    flushList(); para.push(line);
  }
  flushPara(); flushList();
  return html;
}

// Resolve the editor identity for changelog entries: ORCID (from Settings) wins,
// else the signed-in GitHub name, else a generic default.
function resolveEditor(){
  var orcid = (localStorage.getItem('ari_editor_orcid') || '').trim();
  state.editor = orcid || state.githubName || 'curator';
  return state.editor;
}


// disease-detail array key for each editable category
const DETAIL_KEY = {
  symptoms:'symptoms', environmental:'environmental_factors', antibodies:'antibodies',
  genetic:'genetic', treatments:'treatments', etiology:'etiology', biomarkers:'biomarkers',
  pathophysiology:'pathway', cytokines:'cytokines', tcells:'tcells', apcs:'apcs',
  transcription:'transcription_factors', innate:'innate_components', complement:'complement',
  receptors:'receptors', netosis:'netosis', inflammasome:'inflammasome',
  apr:'acute_phase_reactants', antigens:'antigens',
};

// Disease data items arranged as a narrative: triggers -> etiology -> pathophysiology
// (genetic + biochemical signals + other components) -> biomarkers & treatments -> prevalence.
// Keys within a step are ordered so boxes cluster by their aspect category (BOX_META).
const STORY_GROUPS = [
  { num:1, title:'Triggers & onset', hint:'Environmental exposures and the symptoms they produce',
    keys:['environmental','symptoms'] },
  { num:2, title:'Etiology', hint:'Suspected and known origins of the disease',
    keys:['etiology'] },
  { num:3, title:'Pathophysiology', hint:'Mechanism — genetic and biochemical signals (TFs) and the other immune components',
    aspectGroups:true,
    keys:['genetic','pathophysiology','innate','complement','netosis','inflammasome','apr','antibodies','antigens','tcells','apcs','cytokines','transcription','receptors'] },
  { num:4, title:'Biomarkers & treatments', hint:'Diagnosis and management',
    keys:['biomarkers','treatments'] },
  { num:5, title:'Prevalence', hint:'Epidemiology and disease burden',
    keys:['prevalence'] },
  { num:null, title:'Record', hint:'Edit and release history, and curator feedback',
    keys:['changelog','feedback'] },
];

// Aspect category + concept description for each box, derived from the
// Immunological Data Model (v3). Boxes are grouped by `aspect` within a story
// step; `desc` is shown as the box subtitle.
const BOX_META = {
  symptoms:       { aspect:'Clinical profile',         desc:'Patient-reported subjective experiences; core presenting symptoms.' },
  environmental:  { aspect:'Etiology',                 desc:'Environmental, infectious, chemical, or hormonal catalysts known to initiate or exacerbate disease.' },
  etiology:       { aspect:'Etiology',                 desc:'Suspected and known origins of disease — genetic, external, or idiopathic.' },
  genetic:        { aspect:'Genetics',                 desc:'Susceptibility loci, HLA alleles, and gene polymorphisms implicated via GWAS / linkage.' },
  pathophysiology:{ aspect:'Pathophysiology',          desc:'Mechanistic cascade and the cells, tissues, and organs targeted by the autoimmune process.' },
  innate:         { aspect:'Innate immune component',  desc:'Pattern-recognition receptors (TLRs, NLRs, CLRs, cGAS-STING) activated or dysregulated in the disease.' },
  complement:     { aspect:'Innate immune component',  desc:'Complement pathway components involved; whether activated, consumed, or deficient.' },
  apr:            { aspect:'Innate immune component',  desc:'Acute-phase proteins that are elevated or depressed during active disease.' },
  netosis:        { aspect:'Innate immune component',  desc:'Role and evidence for Neutrophil Extracellular Trap (NET) formation in pathogenesis.' },
  inflammasome:   { aspect:'Innate immune component',  desc:'Inflammasome complexes activated, their triggers, and downstream effectors (IL-1β, IL-18).' },
  antibodies:     { aspect:'Adaptive immunity',        desc:'Disease-specific or -associated autoantibodies, including diagnostic and pathogenic relevance.' },
  antigens:       { aspect:'Adaptive immunity',        desc:'Self-antigens targeted by the autoimmune response.' },
  tcells:         { aspect:'Adaptive immunity',        desc:'T-cell subsets implicated (Th1, Th2, Th17, Tfh, Treg) and their pro- or anti-inflammatory roles.' },
  apcs:           { aspect:'Adaptive immunity',        desc:'Professional APCs involved (dendritic cells, macrophages, B-cells) and their specific dysfunction.' },
  cytokines:      { aspect:'Signaling & molecular',    desc:'Key signalling proteins driving inflammation, organ damage, or immune dysregulation.' },
  transcription:  { aspect:'Signaling & molecular',    desc:'Intracellular master regulators of immune gene expression altered in disease.' },
  receptors:      { aspect:'Signaling & molecular',    desc:'Surface or intracellular receptors with altered expression or function contributing to pathogenesis.' },
  biomarkers:     { aspect:'Biomarkers',               desc:'Measurable serum biomarkers (autoantibodies, proteins, complement levels) used for diagnosis or monitoring.' },
  treatments:     { aspect:'Management',               desc:'Known treatments from medically recognised sources and clinical studies.' },
  prevalence:     { aspect:'Epidemiology',             desc:'Total number of cases per defined population; varies by geography and ethnicity.' },
  changelog:      { aspect:'Record',                   desc:'Edit and release history for this disease record.' },
  feedback:       { aspect:'Record',                   desc:'Leave comments about this term. Feedback is cleared at the next version release unless marked “keep after release”.' },
};

// ----------------------------------------------------------------- DEF SOURCE PARSER
// Parse a stored def-source string ("Author Year; URL; Author2; URL2") into
// an array of {text, url} citation objects.  Handles PMID: references,
// full URLs, and plain text-only entries.  Used by both display and edit form.
function _defSrcIsUrl(s) { return /^https?:\/\//i.test(s); }
function _defSrcIsPmid(s) { return /^PMID:?\s*\d+/i.test(s); }
function _defSrcResolve(s) {
  if (_defSrcIsUrl(s)) return s;
  const m = s.match(/PMID:?\s*(\d+)/i);
  return m ? `https://pubmed.ncbi.nlm.nih.gov/${m[1]}/` : s;
}
function parseDefSrc(str) {
  const parts = String(str || '').split(/\s*;\s*/).map(p => p.trim()).filter(Boolean);
  const cites = [];
  let i = 0;
  while (i < parts.length) {
    const cur = parts[i];
    if (_defSrcIsUrl(cur) || _defSrcIsPmid(cur)) {
      cites.push({ text: '', url: _defSrcResolve(cur) });
      i++;
    } else if (i + 1 < parts.length && (_defSrcIsUrl(parts[i + 1]) || _defSrcIsPmid(parts[i + 1]))) {
      cites.push({ text: cur, url: _defSrcResolve(parts[i + 1]) });
      i += 2;
    } else {
      cites.push({ text: cur, url: '' });
      i++;
    }
  }
  return cites;
}

function toast(msg){
  const t = document.createElement('div'); t.className = 'toast'; t.textContent = msg;
  document.body.appendChild(t); setTimeout(() => t.remove(), 2600);
}
function showLoading(sel){ $(sel).innerHTML = '<div class="loading">Loading...</div>'; }

// Concept description (from the data model) shown under a deep-dive panel title.
function panelDescHTML(key){
  const m = BOX_META[key];
  return m && m.desc ? `<div class="panel-desc">${esc(m.desc)}</div>` : '';
}

// ----------------------------------------------------------------- API
async function api(path, opts={}){
  // Prepend BASE_PATH so API calls work when app is served under a subpath
  const fullPath = path.startsWith('/') ? BASE_PATH + path : path;
  if (opts.body){ opts.headers = {'content-type':'application/json'}; opts.body = JSON.stringify(opts.body); }
  const res = await fetch(fullPath, opts);
  if (!res.ok){ const d = await res.json().catch(()=>({})); throw new Error(d?.detail || res.statusText); }
  return await res.json();
}

// ----------------------------------------------------------------- cross-ref linkouts
function xrefLink(kind, id){
  if (!id) return '#';
  const num = String(id).replace(/^[A-Za-z]+:/, '');
  switch(kind){
    case 'icd10': return `https://www.icd10data.com/search?s=${encodeURIComponent(id)}`;
    case 'snomed': return `https://browser.ihtsdotools.org/?perspective=full&conceptId1=${num}&edition=MAIN`;
    case 'doid': return `https://disease-ontology.org/?id=DOID:${num}`;
    case 'umls': return `https://uts.nlm.nih.gov/uts/umls/concept/${id}`;
    case 'mondo': return `https://www.ebi.ac.uk/ols4/ontologies/mondo/classes?short_form=MONDO_${num}`;
    case 'mesh': return `https://meshb.nlm.nih.gov/record/ui?ui=${num}`;
    case 'nci': return `https://ncithesaurus.nci.nih.gov/ncitbrowser/ConceptReport.jsp?dictionary=NCI_Thesaurus&code=${num}`;
    case 'omop': return `https://athena.ohdsi.org/search-terms/terms/${num}`;
    default: return '#';
  }
}
