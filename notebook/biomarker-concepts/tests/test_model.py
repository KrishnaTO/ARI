import pytest

import model
import review_table
from fixtures_owl import (
    ANTIBODY_DISEASES, ANTIBODY_ENTRIES, ARI, ARIB, DISEASE, EXISTING_RO, arib_class, biomarkers_text,
    disease_text,
)
from model import Row


def row(number, action, concept="", value="", entries="", group="confident", depends=""):
    return Row(str(number), group, action, concept, value, "", "", entries, "", depends, "", "", "")


def write(tmp_path, rows, biomarkers=None, disease=None):
    b = tmp_path / "ari_biomarkers.owl"
    d = tmp_path / "ari_disease.owl"
    b.write_text(biomarkers or biomarkers_text(EXISTING_RO), encoding="utf-8")
    d.write_text(disease or disease_text(ANTIBODY_ENTRIES, ANTIBODY_DISEASES), encoding="utf-8")
    keys = model.write_rows(rows, b, d)
    return keys, b.read_text(encoding="utf-8"), d.read_text(encoding="utf-8")


def test_read_entries_reads_kind_diseases_and_decisions():
    entries = {e.iri: e for e in model.read_entries(disease_text(ANTIBODY_ENTRIES, ANTIBODY_DISEASES))}
    assert len(entries) == 14
    gad = entries[ARI + "Ab_1"]
    assert (gad.kind, gad.label, gad.obsolete) == ("antibodies", "Anti-GAD65 autoantibodies", False)
    assert gad.diseases == [(DISEASE + "ARI_0000001", "Disease one")]
    assert entries[ARI + "Ab_5"].shared == [ARIB + "0000005"]
    assert entries[ARI + "Ab_6"].no_concept == "not a biomarker"
    assert entries[ARI + "Ab_7"].obsolete is True


def test_read_concepts_reads_kind_through_parents():
    text = biomarkers_text(EXISTING_RO + arib_class(
        6, ARIB + "0000005", "Anti-Ro IgG",
        f'        <ari-disease:targetsAntigen rdf:resource="{ARIB}0000009"/>\n'
        '        <ari-disease:ARI_NoConcept>no term</ari-disease:ARI_NoConcept>\n'))
    concepts = {c.iri: c for c in model.read_concepts(text)}
    ro, child = concepts[ARIB + "0000005"], concepts[ARIB + "0000006"]
    assert (ro.kind, ro.label, ro.alt_labels) == ("antibodies", "Anti-Ro antibodies", ["Ro antibody"])
    assert ro.matches == {"exactMatch": ["http://purl.obolibrary.org/obo/HP_0000005"]}
    assert (child.kind, child.parents, child.targets) == ("antibodies", [ARIB + "0000005"], [ARIB + "0000009"])
    assert child.no_concept == "no term"


def test_write_rows_allocates_after_the_highest_id_and_applies_each_action(tmp_path):
    rows = [
        row(1, "concept", "new:Anti-GAD65 antibodies", ARI + "Autoantibody"),
        row(2, "concept", "new:Anti-GAD65 IgG", "new:Anti-GAD65 antibodies"),
        row(3, "altLabel", "new:Anti-GAD65 antibodies", "Anti-GAD65 autoantibodies"),
        row(4, "exactMatch", "new:Anti-GAD65 antibodies", "http://purl.obolibrary.org/obo/HP_5000011"),
        row(5, "no_term", "new:Anti-GAD65 IgG"),
        row(6, "link", "new:Anti-GAD65 antibodies", "new:Anti-GAD65 antibodies", "Ab_1 Anti-GAD65 autoantibodies"),
        row(7, "link", ARIB + "0000005", ARIB + "0000005", "Ab_13 Anti-Ro antibodies"),
        row(8, "label_fix", "", "anti-villin", "Ab_12 anti-villin 40"),
        row(9, "not_a_biomarker", "", "", "Ab_11 This antibody is associated with relapse."),
        row(10, "target", ARIB + "0000005", "new:Anti-GAD65 antibodies"),
    ]
    keys, biomarkers, disease = write(tmp_path, rows)
    assert keys == {"new:Anti-GAD65 antibodies": ARIB + "0000006", "new:Anti-GAD65 IgG": ARIB + "0000007"}
    concepts = {c.iri: c for c in model.read_concepts(biomarkers)}
    gad, igg = concepts[ARIB + "0000006"], concepts[ARIB + "0000007"]
    assert (gad.label, gad.parents, gad.alt_labels) == (
        "Anti-GAD65 antibodies", [ARI + "Autoantibody"], ["Anti-GAD65 autoantibodies"])
    assert gad.matches == {"exactMatch": ["http://purl.obolibrary.org/obo/HP_5000011"]}
    assert (igg.parents, igg.no_concept, igg.kind) == ([ARIB + "0000006"], "no term", "antibodies")
    assert concepts[ARIB + "0000005"].targets == [ARIB + "0000006"]
    assert "<oboInOwl:id>ARIB:0000006</oboInOwl:id>" in biomarkers
    entries = {e.iri: e for e in model.read_entries(disease)}
    assert entries[ARI + "Ab_1"].shared == [ARIB + "0000006"]
    assert entries[ARI + "Ab_13"].shared == [ARIB + "0000005"]
    assert entries[ARI + "Ab_12"].label == "anti-villin"
    assert entries[ARI + "Ab_11"].no_concept == "not a biomarker"


def test_write_rows_starts_at_one_in_an_empty_module(tmp_path):
    keys, _, _ = write(tmp_path, [row(1, "concept", "new:X", ARI + "Antigen")], biomarkers=biomarkers_text())
    assert keys == {"new:X": ARIB + "0000001"}


def test_write_rows_is_deterministic_and_keeps_the_header(tmp_path):
    rows = [row(1, "concept", "new:Anti-GAD65 antibodies", ARI + "Autoantibody"),
            row(2, "link", "new:Anti-GAD65 antibodies", "new:Anti-GAD65 antibodies", "Ab_1 x")]
    first = write(tmp_path, rows)
    second = write(tmp_path, rows)
    assert first == second
    _, biomarkers, disease = first
    for text in (biomarkers, disease):
        assert 'xml:base="http://www.aurint.org/ontologies/' in text
        assert 'xmlns:dc="http://purl.org/dc/elements/1.1/"' in text
        assert 'xmlns:ari-disease="http://www.aurint.org/ontologies/ari-disease#"' in text
    assert '<ARI_Obsolete>false</ARI_Obsolete>' in disease  # default namespace kept
    assert 'xmlns="http://www.aurint.org/ontologies/ari_biomarkers#"' in biomarkers
    assert "<rdfs:comment>Shared ARI biomarker concepts.</rdfs:comment>" in biomarkers


def test_write_rows_refuses_a_key_with_no_concept_row(tmp_path):
    with pytest.raises(ValueError, match="new:Missing"):
        write(tmp_path, [row(1, "link", "new:Missing", "new:Missing", "Ab_1 x")])


def test_write_rows_refuses_an_unknown_entry(tmp_path):
    with pytest.raises(ValueError, match="Ab_99"):
        write(tmp_path, [row(1, "not_a_biomarker", "", "", "Ab_99 x")])


def test_review_table_round_trips(tmp_path):
    rows = [row(1, "altLabel", "new:A", 'Quoted "name", with comma'),
            row(2, "link", "new:A", "new:A", "Ab_1 Anti-A | Ab_2 A", depends="1")]
    path = tmp_path / "antibodies.tsv"
    review_table.write(path, rows)
    assert path.read_text(encoding="utf-8").splitlines()[0].split("\t") == review_table.COLUMNS
    assert review_table.read(path) == rows


def test_review_table_survives_a_spreadsheet_round_trip(tmp_path):
    # A spreadsheet saving tab-delimited UTF-8 adds a byte-order mark and quotes a cell holding a
    # comma or a double quote; the rows read back the same.
    rows = [row(1, "altLabel", "new:A", 'Quoted "name", with comma'),
            row(2, "link", "new:A", "new:A", "Ab_1 Anti-A, B | Ab_2 A", depends="1;3"),
            row(3, "concept", "new:A", ARI + "Autoantibody")]
    path = tmp_path / "antibodies.tsv"
    review_table.write(path, rows)
    assert not path.read_bytes().startswith(b"\xef\xbb\xbf")
    assert review_table.read(path) == rows

    def cell(value):
        return '"' + value.replace('"', '""') + '"' if any(c in value for c in ',"') else value

    table = [review_table.COLUMNS, *([getattr(r, c) for c in review_table.COLUMNS] for r in rows)]
    text = "".join("\t".join(map(cell, values)) + "\r\n" for values in table)
    path.write_bytes(b"\xef\xbb\xbf" + text.encode("utf-8"))
    assert '"Ab_1 Anti-A, B | Ab_2 A"' in text and '"Quoted ""name"", with comma"' in text
    assert review_table.read(path) == rows


def test_review_table_refuses_a_tab_in_a_value(tmp_path):
    with pytest.raises(ValueError, match="tab"):
        review_table.write(tmp_path / "x.tsv", [row(1, "altLabel", "new:A", "a\tb")])
