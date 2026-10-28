import xml.etree.ElementTree as ET

import model
import propose
import sources
from fixtures_owl import (
    ANTIBODY_DISEASES, ANTIBODY_ENTRIES, ARI, ARIB, EXISTING_RO, arib_class, biomarkers_text, disease,
    disease_text, entry,
)

RDF_ABOUT = "{http://www.w3.org/1999/02/22-rdf-syntax-ns#}about"
HP = "http://purl.obolibrary.org/obo/HP_"


def hp_term(number, label, synonyms=()):
    return sources.Term(f"HP:{number}", label, list(synonyms), [], "")


HPO = {t.id: t for t in [
    hp_term("5000011", "Anti-GAD65 antibody positivity"),
    hp_term("0020151", "Anti-dsDNA antibody positivity"),
    hp_term("0033342", "Anti-MOG antibody positivity in serum"),
]}


def antibody_rows():
    return propose.propose(
        "antibodies",
        disease_text(ANTIBODY_ENTRIES, ANTIBODY_DISEASES),
        biomarkers_text(EXISTING_RO),
        propose.Sources(hp=HPO),
    )


def by(rows, action, concept=None):
    return [r for r in rows if r.action == action and (concept is None or r.concept == concept)]


def entry_ids(r):
    return [item.split()[0] for item in r.entries.split(" | ")] if r.entries else []


def write(tmp_path, rows, biomarkers, disease):
    b = tmp_path / "ari_biomarkers.owl"
    d = tmp_path / "ari_disease.owl"
    b.write_text(biomarkers, encoding="utf-8")
    d.write_text(disease, encoding="utf-8")
    keys = model.write_rows(rows, b, d)
    return keys, b.read_text(encoding="utf-8"), d.read_text(encoding="utf-8")


def element(text, iri):
    return next(el for el in ET.fromstring(text) if el.get(RDF_ABOUT) == iri)


def test_existing_concepts_are_never_rewritten(tmp_path):
    before = biomarkers_text(EXISTING_RO)
    _, after, _ = write(tmp_path, antibody_rows(), before,
                        disease_text(ANTIBODY_ENTRIES, ANTIBODY_DISEASES))
    old = element(before, ARIB + "0000005")
    new = element(after, ARIB + "0000005")
    assert ET.tostring(new) == ET.tostring(old)


def test_decided_entries_are_skipped():
    rows = antibody_rows()
    mentioned = {e for r in rows for e in entry_ids(r) if r.action in ("link", "label_fix", "not_a_biomarker")}
    assert not mentioned & {"Ab_5", "Ab_6", "Ab_7"}
    assert {"Ab_1", "Ab_2", "Ab_3", "Ab_4", "Ab_8", "Ab_11", "Ab_12", "Ab_13"} <= mentioned


def test_judgement_rows_come_first():
    rows = antibody_rows()
    groups = [r.group for r in rows]
    assert set(groups) == {"judgement", "confident"}
    assert groups == sorted(groups, key=lambda g: g != "judgement")
    assert [r.row for r in rows] == [str(n) for n in range(1, len(rows) + 1)]
    # the judgement calls the fixture holds
    judged = {(r.action, r.value) for r in rows if r.group == "judgement"}
    assert ("altLabel", "Type VII Colagen") in judged
    assert ("label_fix", "anti-villin") in judged
    assert any(a == "not_a_biomarker" for a, _ in judged)


def test_an_existing_label_links_to_its_concept():
    [link] = [r for r in by(antibody_rows(), "link") if entry_ids(r) == ["Ab_13"]]
    assert (link.value, link.group, link.depends) == (ARIB + "0000005", "confident", "")


def test_a_fuzzy_merge_is_a_judgement_and_its_link_depends_on_it():
    rows = antibody_rows()
    [alt] = [r for r in by(rows, "altLabel") if r.value == "Type VII Colagen"]
    assert (alt.concept, alt.group) == ("new:Type VII collagen", "judgement")
    [link] = [r for r in by(rows, "link") if entry_ids(r) == ["Ab_8"]]
    assert alt.row in link.depends.split(";")
    # a different roman numeral is a different molecule
    assert by(rows, "concept", "new:Type VI collagen")


def test_a_qualified_antibody_nests_under_its_unqualified_concept():
    rows = antibody_rows()
    [child] = by(rows, "concept", "new:Anti-MOG IgG")
    [parent] = by(rows, "concept", "new:Anti-MOG antibody")
    assert child.value == "new:Anti-MOG antibody"
    assert parent.value == ARI + "Autoantibody"
    assert parent.row in child.depends.split(";")
    # the parent matched HPO, so the child needs no term of its own
    assert by(rows, "exactMatch", "new:Anti-MOG antibody") or by(rows, "closeMatch", "new:Anti-MOG antibody")
    assert not by(rows, "no_term", "new:Anti-MOG IgG")


def test_a_bundle_gets_one_link_per_marker():
    links = [r for r in by(antibody_rows(), "link") if entry_ids(r) == ["Ab_4"]]
    assert sorted(r.value for r in links) == ["new:ANA", "new:anti-Sm", "new:anti-dsDNA"]
    assert {r.group for r in links} == {"judgement"}


def test_external_matches_and_no_term():
    rows = antibody_rows()
    [gad] = by(rows, "exactMatch", "new:Anti-GAD65 autoantibodies") or by(rows, "exactMatch", "new:Anti-GAD65 antibodies")
    assert (gad.value, gad.group) == (HP + "5000011", "confident")
    assert by(rows, "no_term", "new:anti-Sm")[0].group == "confident"


def test_an_antibody_naming_an_unknown_antigen_creates_it(tmp_path):
    biomarkers = biomarkers_text(
        arib_class(1, ARI + "Autoantibody", "Anti-LGI1 antibodies")
        + arib_class(2, ARI + "Autoantibody", "Anti-AQP4 antibodies")
        + arib_class(3, ARIB + "0000002", "Anti-AQP4 IgG"))
    diseases = disease_text(
        [entry("Antigen_1", "Antigen", "Aquaporin-4"),
         entry("Ab_1", "Autoantibody", "Anti-LGI1 antibodies", f'<sharedConcept rdf:resource="{ARIB}0000001"/>')],
        [disease("ARI_0000001", "Disease one", [("involvesAntigen", "Antigen_1"), ("hasAntibody", "Ab_1")])])
    srcs = propose.Sources(
        hgnc={"HGNC:6572": sources.Gene("HGNC:6572", "LGI1", "leucine rich glioma inactivated 1", [], ["O95970"]),
              "HGNC:637": sources.Gene("HGNC:637", "AQP4", "aquaporin 4", ["MIWC"], ["P55087"])},
        pr={"PR:O95970": sources.Term("PR:O95970", "leucine-rich glioma-inactivated protein 1", [], [], ""),
            "PR:P55087": sources.Term("PR:P55087", "aquaporin-4", [], [], "")},
    )
    rows = propose.propose("antigens", diseases, biomarkers, srcs)

    [lgi1] = by(rows, "concept", "new:LGI1")
    assert lgi1.value == ARI + "Antigen"
    [pr] = by(rows, "exactMatch", "new:LGI1")
    assert pr.value == "http://purl.obolibrary.org/obo/PR_O95970"
    [hgnc] = by(rows, "relatedMatch", "new:LGI1")
    assert hgnc.value == "http://identifiers.org/hgnc/6572"
    [target] = by(rows, "target", ARIB + "0000001")
    assert (target.value, target.group) == ("new:LGI1", "confident")
    assert lgi1.row in target.depends.split(";")
    assert "Disease one" in target.diseases

    # Anti-AQP4 targets the antigen entry's concept; its child inherits the target, stated once
    [aqp4] = by(rows, "target", ARIB + "0000002")
    assert aqp4.value == "new:Aquaporin-4"
    assert not by(rows, "target", ARIB + "0000003")

    keys, after, _ = write(tmp_path, rows, biomarkers, diseases)
    antibody = {c.iri: c for c in model.read_concepts(after)}[ARIB + "0000001"]
    assert antibody.targets == [keys["new:LGI1"]]


def test_the_antibodies_kind_adds_nothing_to_existing_classes():
    rows = antibody_rows()
    assert not [r for r in rows if r.concept.startswith(ARIB) and r.action not in ("link", "target")]
    assert not by(rows, "target")


def test_write_rows_round_trips(tmp_path):
    rows = antibody_rows()
    keys, biomarkers, disease_out = write(tmp_path, rows, biomarkers_text(EXISTING_RO),
                                          disease_text(ANTIBODY_ENTRIES, ANTIBODY_DISEASES))
    concepts = {c.iri: c for c in model.read_concepts(biomarkers)}
    for r in by(rows, "concept"):
        assert concepts[keys[r.concept]].label == r.concept.removeprefix("new:")
    for r in by(rows, "altLabel"):
        assert r.value in concepts[keys[r.concept]].alt_labels
    for action in ("exactMatch", "closeMatch"):
        for r in by(rows, action):
            assert r.value in concepts[keys[r.concept]].matches[action]
    entries = {e.iri.removeprefix(ARI): e for e in model.read_entries(disease_out)}
    for r in by(rows, "link"):
        [local] = entry_ids(r)
        assert keys.get(r.value, r.value) in entries[local].shared
    assert len(entries["Ab_4"].shared) == 3


def test_labels_sharing_a_name_merge_as_a_judgement():
    entries = [entry("Ab_1", "Autoantibody", "Anti-GAD65 autoantibodies"),
               entry("Ab_2", "Autoantibody", "Anti-GAD65 autoantibodies"),
               entry("Ab_3", "Autoantibody", "Anti-GAD65 (GADA)"),
               entry("Ab_4", "Autoantibody", "Anti-GAD65 IgG")]
    rows = propose.propose(
        "antibodies",
        disease_text(entries, [disease("ARI_0000001", "Disease one", [("hasAntibody", f"Ab_{n}") for n in (1, 2, 3, 4)])]),
        biomarkers_text(), propose.Sources(hp=HPO))
    [alt] = [r for r in by(rows, "altLabel") if r.value == "Anti-GAD65 (GADA)"]
    assert (alt.concept, alt.group) == ("new:Anti-GAD65 autoantibodies", "judgement")
    # the IgG child nests under the merged concept and inherits its HPO term
    [child] = by(rows, "concept", "new:Anti-GAD65 IgG")
    assert child.value == "new:Anti-GAD65 autoantibodies"
    assert not [r for r in rows if r.concept == "new:Anti-GAD65 IgG" and r.action in ("exactMatch", "closeMatch", "no_term")]


def test_a_family_nests_its_members():
    entries = [entry("Antigen_1", "Antigen", "Sperm surface antigens (SP-10, YLP-12, Izumo1)"),
               entry("Antigen_2", "Antigen", "Izumo1")]
    rows = propose.propose(
        "antigens",
        disease_text(entries, [disease("ARI_0000001", "Disease one", [("involvesAntigen", "Antigen_1"),
                                                                      ("involvesAntigen", "Antigen_2")])]),
        biomarkers_text(), propose.Sources())
    family = "new:Sperm surface antigens (SP-10, YLP-12, Izumo1)"
    for member in ("SP-10", "YLP-12", "Izumo1"):
        [row] = by(rows, "concept", "new:" + member)
        assert (row.value, row.group) == (family, "judgement")
    # members are not aliases of the family
    assert not by(rows, "altLabel")


def test_a_gene_without_a_pr_term_gets_hgnc_and_no_term_as_judgements():
    entries = [entry("Antigen_1", "Antigen", "NALP5")]
    rows = propose.propose(
        "antigens",
        disease_text(entries, [disease("ARI_0000001", "Disease one", [("involvesAntigen", "Antigen_1")])]),
        biomarkers_text(),
        propose.Sources(hgnc={"HGNC:21269": sources.Gene("HGNC:21269", "NLRP5", "NLR family pyrin domain containing 5",
                                                         ["NALP5"], ["P59047"])}))
    [hgnc] = by(rows, "relatedMatch", "new:NALP5")
    [no_term] = by(rows, "no_term", "new:NALP5")
    assert hgnc.value == "http://identifiers.org/hgnc/21269"
    assert (hgnc.group, no_term.group) == ("judgement", "judgement")
    assert not by(rows, "exactMatch")


def test_a_match_found_only_through_a_judged_label_is_a_judgement_on_it():
    entries = [entry("Ab_1", "Autoantibody", "Perinuclear ANCA"),
               entry("Ab_2", "Autoantibody", "Perinuclear ANCA"),
               entry("Ab_3", "Autoantibody", "Perinuclear ANCA (anti-MPO)")]
    rows = propose.propose(
        "antibodies",
        disease_text(entries, [disease("ARI_0000001", "Disease one", [("hasAntibody", f"Ab_{n}") for n in (1, 2, 3)])]),
        biomarkers_text(), propose.Sources(hp={"HP:0033559": hp_term("0033559", "Anti-MPO antibody positivity")}))
    [alt] = [r for r in by(rows, "altLabel") if r.value == "Perinuclear ANCA (anti-MPO)"]
    assert alt.group == "judgement"
    [match] = by(rows, "exactMatch", "new:Perinuclear ANCA")
    assert match.group == "judgement"
    assert alt.row in match.depends.split(";")


def test_a_target_found_only_through_a_judged_label_is_a_judgement_on_it():
    entries = [entry("Antigen_1", "Antigen", "BP230"), entry("Antigen_2", "Antigen", "BP230"),
               entry("Antigen_3", "Antigen", "BP230 (dystonin)")]
    rows = propose.propose(
        "antigens",
        disease_text(entries, [disease("ARI_0000001", "Disease one", [("involvesAntigen", f"Antigen_{n}") for n in (1, 2, 3)])]),
        biomarkers_text(arib_class(1, ARI + "Autoantibody", "Anti-BP230 (dystonin) antibodies")),
        propose.Sources())
    [alt] = [r for r in by(rows, "altLabel") if r.value == "BP230 (dystonin)"]
    [target] = by(rows, "target", ARIB + "0000001")
    assert (target.value, target.group) == ("new:BP230", "judgement")
    assert alt.row in target.depends.split(";")


def test_a_whole_label_names_the_concept_before_a_bundle_part():
    entries = [entry("Ab_1", "Autoantibody", "Anti MOG"),
               entry("Ab_2", "Autoantibody", "high-affinity autoantibodies to MBP and MOG")]
    rows = propose.propose(
        "antibodies",
        disease_text(entries, [disease("ARI_0000001", "Disease one", [("hasAntibody", "Ab_1"), ("hasAntibody", "Ab_2")])]),
        biomarkers_text(), propose.Sources())
    assert by(rows, "concept", "new:Anti MOG")
    assert not by(rows, "concept", "new:MOG")


def test_created_concepts_carry_the_entries_they_were_made_for():
    rows = antibody_rows()
    [parent] = by(rows, "concept", "new:Anti-MOG antibody")
    assert entry_ids(parent) == ["Ab_3"]
    assert parent.diseases == "ARI_0000001 Disease one"
    [match] = by(rows, "exactMatch", "new:Anti-MOG antibody")
    assert entry_ids(match) == ["Ab_3"]


def test_a_target_on_an_unlinked_parent_shows_its_childs_entries():
    biomarkers = biomarkers_text(arib_class(1, ARI + "Autoantibody", "Anti-LGI1 antibody")
                                 + arib_class(2, ARIB + "0000001", "Anti-LGI1 IgG"))
    diseases = disease_text(
        [entry("Ab_1", "Autoantibody", "Anti-LGI1 IgG", f'<sharedConcept rdf:resource="{ARIB}0000002"/>')],
        [disease("ARI_0000001", "Disease one", [("hasAntibody", "Ab_1")])])
    srcs = propose.Sources(
        hgnc={"HGNC:6572": sources.Gene("HGNC:6572", "LGI1", "leucine rich glioma inactivated 1", [], ["O95970"])},
        pr={"PR:O95970": sources.Term("PR:O95970", "leucine-rich glioma-inactivated protein 1", [], [], "")})
    rows = propose.propose("antigens", diseases, biomarkers, srcs)
    [target] = by(rows, "target", ARIB + "0000001")
    [created] = by(rows, "concept", "new:LGI1")
    assert entry_ids(target) == entry_ids(created) == ["Ab_1"]
    assert target.diseases == created.diseases == "ARI_0000001 Disease one"
