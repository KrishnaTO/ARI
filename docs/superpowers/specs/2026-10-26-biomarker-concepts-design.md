# Biomarker concepts — design

Date: 2026-10-26. Branch: `biomarker-concepts-design`. Project 2 of
[the ontology modules design](2026-10-18-ontology-modules-design.md); Project 1 (the split) is live.

## Intent

Today each disease carries its own autoantibody, antigen and clinical biomarker entries as
free-text labels: 358 autoantibody entries (~266 distinct names), 327 antigen entries (~257) and
18 clinical biomarker entries (17). Nothing ties "Anti-GAD65 autoantibodies" on Type 1 diabetes
to "GADA" on another disease, an antibody to the antigen it targets, or any marker to the outside
world.

The user wants three things:

1. **Each biomarker linked to an external ontology that knows more about it** — Gene Ontology or a
   biomarker-specific ontology — ideally one related to the ontologies ARI already uses.
2. **A curator can see a biomarker's relatives, direct and indirect**, especially markers that are
   also associated with other diseases.
3. **A curator can link a biomarker to the body parts it is expressed in and to symptoms.**

The modules design already decided the shape: shared ARIB concept classes in
`ari_biomarkers.owl`, each per-disease entry pointing at its concept through `sharedConcept`,
exactly as symptoms do with ARIS.

## Decisions made by the user

1. **Relations between concepts are authored in Protégé or by script, in the OWL file** — not in
   the editor. ("Protégé should be fine, since [it] need[s] to be done in code or owl file.")
2. **Biomarker → disease stays where it is.** The disease file's `hasAntibody` / `involvesAntigen`
   / `hasBiomarker` links, with their per-disease values, are the only record of which disease has
   which marker. The biomarker file does not repeat them; it is reached through `sharedConcept`.
   ("If it is already listed, keep it that way.")
3. **Relatives are shown in the editor**, by expanding the row in place on the disease page
   (mockup option A, below), not on a separate biomarker page.
4. **Both direct and indirect relatives** are shown.
5. **External releases are downloaded** into `data/2-databases`; the build reads only local copies.
6. **Review is done on pull requests** to this repo, organised around each per-disease
   association and the external ontology term proposed for its concept, **with a table to accept
   or reject the changes line by line**.
7. **Variants nest.** An isotype-specific antibody ("Anti-CNTN1 IgG4") is its own concept, a
   subclass of the general one ("Anti-CNTN1 antibody"). A family ("Sperm surface antigens
   (SP-10, YLP-12, Izumo1)") is a parent concept, with each member it names as a child concept.
8. **Every antigen an antibody names gets a concept**, with its protein and gene links, even when
   no disease lists it as an antigen entry (Anti-LGI1 → LGI1, Anti-CASPR2 → CASPR2), so every such
   antibody has a target.

## Goals

- One ARIB class per distinct marker, with its variant names as `skos:altLabel`.
- Every concept that has a published term carries the link; every one that does not says so.
- Every live (`ARI_Obsolete` false) per-disease antibody, antigen and clinical biomarker entry has
  `sharedConcept` or `ARI_NoConcept`.
- Antibody → target antigen links for every antibody whose name names its antigen — 102 of them
  pair with an existing antigen entry by name today; the rest get a new antigen concept (decision
  8) — plus IEDB-backed proposals the reviewers accept.
- Curators can add antibody → antigen, biomarker → body part and biomarker → symptom links in
  Protégé, and the editor shows them.
- Clicking a biomarker row in the editor shows its concept, external link, direct and indirect
  relatives, the other diseases it appears in, and its body parts and symptoms.

## Non-goals

- Editing concepts or their relations in the editor. The editor reads them.
- Changing any per-disease entry's IRI, fields or values (frequency, diagnostic value, type,
  sensitivity, source). Bundled labels are linked, not split into new entries. (One exception:
  reviewer-accepted fixes to noisy labels, under Per-disease entries.)
- Importing Gene Ontology annotations. GO is reached through the linked protein (UniProt/PR) by
  anyone who follows the link; ARI does not copy GO terms.
- Affected cell/tissue/organ concepts (Project 3).
- A separate biomarker page in the editor (option B, not chosen).

## Anti-goals (failure even if it technically works)

- A Protégé edit to `ari_biomarkers.owl` overwritten by a script re-run.
- Disease ↔ biomarker associations recorded a second time in the biomarker file.
- A proposal landing on `main` that no reviewer accepted.
- The build reaching out to an online service for matching.
- A curator save in the editor dropping an entry's `sharedConcept` or `ARI_NoConcept` (the
  Project 1 bug class, Task 8).

## The concepts

**Classes.** `ari-biomarkers#ARIB_nnnnnnn` (seven digits), each a subclass of the core's
`Autoantibody`, `Antigen` or `ClinicalBiomarker`. `rdfs:label` is the preferred name; every other
name used by a per-disease entry for the same marker is a `skos:altLabel`. Ids are allocated by
the scripts in sequence and never reused.

**Grouping.** Names that mean the same marker are one concept: case, spelling and punctuation
variants ("Type VII Colagen" / "Type VII collagen"), abbreviation and expansion ("GADA" /
"Anti-GAD65 autoantibodies"), and an antibody named either way ("Anti-X", "X antibodies"). An
antibody and its antigen are always **two** concepts, linked by the target relation below, never
merged.

**Nesting** (decision 7). ARIB concepts may be subclasses of other ARIB concepts:

- An isotype or functional qualifier that a name states ("IgG4", "IgA", "neutralizing IgG") makes
  a child of the unqualified antibody concept, which is created if no entry names it. "Anti-MOG
  IgG" under "Anti-MOG antibody"; "Anti-CNTN1 IgG4" under "Anti-CNTN1 antibody".
- A family name makes a parent concept; each member it names ("SP-10", "YLP-12", "Izumo1") is a
  child. A family that names no members ("Endothelial cell antigens") is one concept.
- A child links to its own external term where one exists, otherwise inherits nothing and carries
  `ARI_NoConcept "no term"` only if its parent has no term either. *My call:* a child without its
  own term is still considered decided when its parent has one.
- Children inherit their parent's `targetsAntigen` implicitly; it is stated only on the parent.

**Antigens named only by an antibody** (decision 8). When an antibody's name names an antigen
that has no concept, the proposal script creates the antigen concept (with its PR / HGNC or ChEBI
link) and the `targetsAntigen` link. These concepts have no per-disease entry; they exist to be
targets.

**External links**, by kind (written as SKOS mappings on the concept class):

| Concept | `skos:exactMatch` (or `broadMatch` / `closeMatch` when not exact) | Also |
| --- | --- | --- |
| Autoantibody | the HPO antibody-positivity term where one exists (~380 in HPO, e.g. `HP:5000011` Anti-GAD65 antibody positivity, `HP:0003493` ANA positivity) | its target antigen (below) |
| Antigen, protein | Protein Ontology term for the protein (UniProt-based, e.g. `PR:Q05329`) | `skos:relatedMatch` to the HGNC gene (e.g. `HGNC:4093` GAD2) |
| Antigen, not a protein (lipid, nucleic acid, drug, small molecule) | ChEBI term | — |
| Clinical biomarker | LOINC code where the test has one | — |

A concept with no published term carries `ARI_NoConcept "no term"` on the class, so "decided
none" never looks like "not reviewed". Antigens from other organisms (molecular mimicry) match the
PR or ChEBI term for that organism's molecule. Many clinical biomarkers are imaging or clinical
findings ("Aortic imaging") with no LOINC code; those get `no term`.

**Slices.** Following the modules naming rule, each external source with terms referenced from
`ari_biomarkers.owl` gets a generated import slice holding those terms with their labels (and
`is_a` ancestors where the source has a hierarchy): `ari_pr.owl`, `ari_chebi.owl`,
`ari_hgnc.owl`, `ari_loinc.owl`. LOINC and HGNC have no OWL release, so their slices declare the
referenced IRIs with label only; `ari_loinc.owl` carries LOINC's required licence notice. HPO
terms are referenced directly with no slice, as `ari_symptoms.owl` already does for its 762 HP
references. `ari_biomarkers.owl` imports core and the slices; the catalog lists them.

## Relations between concepts

Three new annotation properties, declared once in `ari_core.owl` (the only file that declares
properties), each with a class as its value, like `sharedConcept`. *My call* on annotation rather
than OWL restrictions — it matches `sharedConcept`, owlready2 and the validator read it directly,
and Protégé edits it in the Annotations pane — and on the names:

| Property | From | To |
| --- | --- | --- |
| `targetsAntigen` | an ARIB antibody class | an ARIB antigen class |
| `expressedIn` | any ARIB class | a body part: an `ari_anatomy.owl` class or a `ari_uberon.owl` term (later an ARIA class) |
| `associatedSymptom` | any ARIB class | an ARIS class in `ari_symptoms.owl` |

`skos:relatedMatch` is added to the core's mapping vocabulary for the HGNC link.

Antibody → antigen links are seeded by script (from names, and IEDB proposals) and reviewed like
everything else. Body-part and symptom links start empty; curators add them in Protégé.

## Per-disease entries

- Each live entry gets `sharedConcept` → its ARIB class, found by label lookup (the same rule the
  modules design set: match the entry's label against concept `rdfs:label` and `skos:altLabel`).
- A **bundle** label that names several markers ("ANA, anti-dsDNA and anti-Sm") gets one
  `sharedConcept` value per marker it names; the entry itself is unchanged. *My call*, to keep the
  disease record's fields and values as they are (a non-goal of the modules design).
- A sentence-like label that names no marker gets `ARI_NoConcept "not a biomarker"`. *My call* on
  the value, parallel to `not a symptom`.
- A **noisy** label — a stray value inside the name ("Anti-GAD65  25", "Anti-ACSL5 (…)  <50%") —
  is proposed for a label fix as a judgement-call row (the clean name; nothing moved into other
  fields). Accepted, the clean label is what lookup matches; rejected, the noisy string becomes an
  `altLabel` of its concept. *My call:* a reviewer-gated label fix is the one exception to "entry
  values unchanged", because lookup cannot work on these strings otherwise.
- Obsolete entries are left alone.

**Label lookup holds for every single-concept entry**: its one `sharedConcept` is what its label
looks up to, and the validator checks this as it does for symptoms. An entry with **more than one**
`sharedConcept` is a bundle, recorded as such by having several values; the validator checks only
that each target exists. When a curator renames a bundle in the editor, lookup finds no single
concept, so the app removes its links and the validator warns as for any unlinked entry; the next
proposal run picks it up. *My call* — bundles are rare (~17) and editor renames of them rarer.

## Sources

Downloaded once into the primary checkout's untracked `data/2-databases/` (not version-controlled)
and read only from there; each script takes the paths as arguments:

- Protein Ontology (OWL or OBO), HGNC complete set, ChEBI (OWL or OBO), LOINC table.
  **LOINC needs a free loinc.org account to download** — the user downloads it.
- IEDB: the local `iedb/iedb_public.sql.gz`, or a newer dump if one is available.
- HPO: the local `hp.obo`.

## Proposal and review

**Proposal script** (`notebook/biomarker-concepts/`, run by hand) reads the disease file, the
current `ari_biomarkers.owl` and the local sources, and proposes:

1. the grouping of entry labels into concepts (new classes, `altLabel`s);
2. each concept's external link, or `no term`;
3. antibody → antigen links, from names and from IEDB (IEDB-only links are judgement calls);
4. `sharedConcept` / `ARI_NoConcept` on each live entry.

It only proposes for entries that have neither `sharedConcept` nor `ARI_NoConcept`, and never
rewrites an existing ARIB class, so re-running it cannot overwrite Protégé work.

**Three pull requests, in order:** antibodies, then antigens (which also carries the antibody →
antigen links, since both ends exist by then — *my call* on that placement), then clinical
biomarkers. Each PR changes `ari_biomarkers.owl`, `ari_disease.owl` and the slices, and includes
a **review table**.

**The review table** — `notebook/biomarker-concepts/review/<kind>.tsv`, committed in the PR — has
one row per proposal, **judgement calls first** (fuzzy groupings, `broadMatch`/`closeMatch`,
IEDB-only targets, bundles, `not a biomarker`), then the confident ones. Each row shows the
disease(s) and per-disease label(s) involved, the proposed concept, the proposed external term
with its label and source, and the evidence. Reviewers fill a `decision` column (`accept` /
`reject` / `correct`) and, for `correct`, a corrected value. **A blank decision is not an
accept:** the apply script refuses to run while any row is blank, so nothing lands unreviewed. To
keep the confident rows light, reviewers may fill `accept` down the confident block in one
spreadsheet action — that is still their decision (*my call*). A reviewer is anyone the user asks
to review; one decision per row is enough. An **apply script** then rewrites the
PR's OWL to match: rejected rows are removed, corrections applied, and the table is deleted in the
same commit — it lives on in git history only, and the OWL stays the record (*my call*, following
the modules design's "curated TSVs stop being sources").

The validator and the `OWL format` workflow gate each PR as usual.

## Validator

New checks in `.github/scripts/validate_mappings.py`, scoped by `--since` like the existing ones:

- every `sharedConcept` on an antibody / antigen / clinical biomarker entry points at an existing
  ARIB class of the matching kind, and on a single-concept entry equals its label lookup;
- an ARIB class's `rdfs:subClassOf` parent is its core kind or an ARIB class of the same kind;
- ARIB ids unique; labels and `altLabel`s unique across concepts of the same kind;
- `targetsAntigen` goes antibody → antigen; `expressedIn` targets an anatomy or UBERON class;
  `associatedSymptom` targets an ARIS class;
- every external IRI referenced from `ari_biomarkers.owl` is present in its slice;
- a live biomarker entry with neither `sharedConcept` nor `ARI_NoConcept` is a warning (as for
  symptoms).

## The editor (app repo)

**Linking.** When a curator adds or renames an antibody, antigen or clinical biomarker entry, the
app sets `sharedConcept` by label lookup in `ari_biomarkers.owl`, as it does for symptoms; the
concept index covers both modules. A save that does not change the label keeps the entry's
`sharedConcept` / `ARI_NoConcept` as they are.

**Expanded row (option A).** On a disease page, clicking a row in the Autoantibodies, Antigens or
Clinical biomarkers panel expands it in place, read-only:

```
▾ Anti-GAD65 autoantibodies            70–80%    High
  Anti-GAD65 antibody · HPO HP:5000011 · also called GADA
  Direct      Target antigen: GAD65 → gene GAD2 (UniProt Q05329)
              Other antibodies to GAD65: none recorded
  Indirect    Appears with: IA-2A (3 diseases) · ZnT8A (2) · Anti-TPO (2)
  Also in     Stiff-person syndrome · LADA · Autoimmune cerebellar ataxia
  Body parts / symptoms   Islet of Langerhans, Nervous system · Muscle stiffness
```

- **Direct:** for an antibody, its target antigen with gene and protein; other antibodies that
  target the same antigen. For an antigen, the antibodies that target it. For any concept, its
  parent and child concepts (isotypes, family members).
- **Indirect, computed on the fly:** other concepts that occur in the same diseases as this one,
  ranked by the number of diseases they share.
- **Also in:** the other diseases with an entry linked to the same concept; each name opens that
  disease.
- **Body parts and symptoms** from `expressedIn` / `associatedSymptom`.
- An entry with no concept shows "no shared concept yet"; one with `ARI_NoConcept` shows the
  reason.

## Delivery

One project, three steps, each its own data PR (paired with an app PR where marked):

1. **Foundations.** Core declarations (three relations, `skos:relatedMatch`); the slice
   extractor(s); validator checks; the proposal, review-table and apply scripts. App PR: concept
   index and label-lookup linking across the biomarker module, and the save rule above — merged
   with or before the first review PR so no curator save drops a new link.
2. **The three review PRs** (antibodies, antigens + targets, clinical biomarkers), each merged
   after its table is applied.
3. **Editor view.** App PR: the expanded rows.

Every live step (merges that need a cutover, server changes) is confirmed with the user at the
time, as in Project 1.

## Done

- Every live antibody, antigen and clinical biomarker entry has `sharedConcept` or `ARI_NoConcept`.
- Every ARIB concept has an external link or `ARI_NoConcept "no term"`.
- Every antibody whose name names its antigen has `targetsAntigen` (less any the reviewers
  rejected), the 102 existing-entry pairs among them.
- The expanded rows work on the live editor.

## Left to the builder

- Matching heuristics (normalisation, abbreviation tables, fuzzy thresholds) and how IEDB is
  queried, so long as uncertain results are listed as judgement calls.
- One slice extractor or one per source.
- The review table's exact column names and the apply script's mechanics.
- The editor's API shape and styling of the expanded row.
