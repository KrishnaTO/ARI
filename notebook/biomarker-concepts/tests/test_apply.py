import dataclasses
import subprocess

import apply_review
import model
import propose
import pytest
import review_table
from fixtures_owl import ANTIBODY_DISEASES, ANTIBODY_ENTRIES, ARIB, EXISTING_RO, biomarkers_text, disease_text
from test_propose import HPO

ARO = ARIB + "0000005"  # the fixture's hand-made concept, with an exact match
EXISTING = "preview, to be replaced"


def row(number, action, concept="", value="", entries="", depends="", decision="accept", correction=""):
    return model.Row(str(number), "confident", action, concept, value, value, "", entries, "", depends,
                     decision, correction, "")


def ids(rows):
    return [r.row for r in rows]


def texts():
    return biomarkers_text(EXISTING_RO), disease_text(ANTIBODY_ENTRIES, ANTIBODY_DISEASES)


def proposed():
    biomarkers, disease = texts()
    return propose.propose("antibodies", disease, biomarkers, propose.Sources(hp=HPO))


# --- decide -------------------------------------------------------------


def test_a_blank_decision_refuses_to_apply():
    rows = [row(1, "concept", "new:A", "kind", decision=""),
            row(2, "no_term", "new:A", decision="maybe"),
            row(3, "no_term", "new:B", decision="correct", correction=""),
            row(4, "no_term", "new:C", depends="99")]
    with pytest.raises(ValueError) as error:
        apply_review.decide(rows)
    message = str(error.value)
    for needle in ("row 1", "row 2", "'maybe'", "row 3", "correction", "99"):
        assert needle in message


def test_rejecting_a_concept_skips_its_dependents():
    rows = [row(1, "concept", "new:A", "k", decision="reject"),
            row(2, "exactMatch", "new:A", "http://x/1", depends="1"),
            row(3, "concept", "new:B", "k"),
            row(4, "link", "new:B", "new:B", "Ab_1 x", depends="3")]
    written, skipped = apply_review.decide(rows)
    assert ids(written) == ["3", "4"]
    assert ids(skipped) == ["2"]
    assert "1" in skipped[0].reason and "rejected" in skipped[0].reason


def test_a_dependency_can_point_forward_and_skipping_is_transitive():
    # Row 1 depends on the later row 3, and 3 <- 4 <- 5: rejecting row 5 skips 4, then 3, then 1.
    rows = [row(1, "concept", "new:Child", "new:Parent", depends="3"),
            row(2, "concept", "new:Other", "k"),
            row(3, "concept", "new:Parent", "k", depends="4"),
            row(4, "exactMatch", "new:Parent", "http://x/1", depends="5"),
            row(5, "altLabel", "new:Parent", "lbl", decision="reject")]
    written, skipped = apply_review.decide(rows)
    assert ids(written) == ["2"]
    assert ids(skipped) == ["1", "3", "4"]
    assert skipped[0].reason == "depends on row 3, which was skipped"


def test_correct_replaces_the_value():
    rows = [row(1, "exactMatch", "new:A", "http://x/1", decision="correct", correction="http://x/2")]
    written, skipped = apply_review.decide(rows)
    assert skipped == [] and written[0].value == "http://x/2"
    assert dataclasses.replace(written[0], value="http://x/1") == rows[0]  # nothing else changed


def test_a_rejected_label_fix_keeps_the_noisy_label_as_an_alt_label():
    rows = [row(1, "concept", "new:V", "k"),
            row(2, "label_fix", "new:V", "anti-villin", "Ab_12 anything", decision="reject"),
            row(3, "link", "new:V", "new:V", "Ab_12 anything", "1")]
    written, skipped = apply_review.decide(rows, {"Ab_12": "anti-villin 40"})
    alt = [r for r in written if r.action == "altLabel"]
    assert [(r.concept, r.value, r.decision) for r in alt] == [("new:V", "anti-villin 40", "accept")]
    assert [r.action for r in written] == ["concept", "altLabel", "link"]  # in the rejected row's place
    assert skipped == []


def test_a_rejected_label_fix_adds_the_alt_label_to_an_existing_concept_too():
    rows = [row(1, "label_fix", "", "Anti-Ro", "Ab_13 x", decision="reject"),
            row(2, "link", ARO, ARO, "Ab_13 x")]
    written, _ = apply_review.decide(rows, {"Ab_13": "Anti-Ro 12"})
    assert [(r.action, r.concept, r.value) for r in written] == [("altLabel", ARO, "Anti-Ro 12"), ("link", ARO, ARO)]


def test_no_alt_label_when_the_link_was_rejected_or_skipped_and_the_summary_says_so():
    rows = [row(1, "concept", "new:X", "k", decision="reject"),
            row(2, "label_fix", "", "Anti-X", "Ab_1 a", decision="reject"),
            row(3, "link", "new:X", "new:X", "Ab_1 a", "1"),  # skipped: row 1 is rejected
            row(4, "label_fix", "", "Anti-Y", "Ab_2 a", decision="reject"),
            row(5, "link", "new:Y", "new:Y", "Ab_2 a", decision="reject")]
    written, skipped = apply_review.decide(rows, {"Ab_1": "Anti-X 1", "Ab_2": "Anti-Y 2"})
    assert written == []
    assert {r.row: r.reason for r in skipped if r.action == "label_fix"} == {
        "2": "label_fix rejected; no altLabel, its link row 3 was skipped",
        "4": "label_fix rejected; no altLabel, its link row 5 was rejected",
    }


def test_a_rejected_label_fix_without_one_link_row_adds_no_alt_label():
    written, skipped = apply_review.decide([row(1, "label_fix", "", "x", "Ab_1 a", decision="reject")],
                                           {"Ab_1": "x 1"})
    assert written == [] and "no link row" in skipped[0].reason


def test_a_rejected_label_fix_needs_the_original_label():
    rows = [row(1, "label_fix", "", "x", "Ab_1 a", decision="reject"), row(2, "link", "new:X", "new:X", "Ab_1 a")]
    with pytest.raises(ValueError, match="Ab_1"):
        apply_review.decide(rows)


def test_correcting_a_concept_out_of_a_rejected_family_writes_it_under_the_new_parent():
    # The GAD65 un-nest: the family is rejected and the member corrected to the core class.
    rows = [row(1, "concept", "new:Organ-specific autoantibodies", "k", decision="reject"),
            row(2, "concept", "new:Anti-GAD65", "new:Organ-specific autoantibodies", depends="1",
                decision="correct", correction=model.KIND_CLASSES["antibodies"]),
            row(3, "exactMatch", "new:Anti-GAD65", "http://x/1", depends="2"),
            row(4, "link", "new:Anti-GAD65", "new:Anti-GAD65", "Ab_1 x", depends="2")]
    written, skipped = apply_review.decide(rows)
    assert ids(written) == ["2", "3", "4"] and skipped == []
    assert written[0].value == model.KIND_CLASSES["antibodies"]


def test_a_corrected_concept_depends_on_its_new_parent():
    rows = [row(1, "concept", "new:P", "k"),
            row(2, "concept", "new:Q", "k", decision="reject"),
            row(3, "concept", "new:C", "k", depends="2", decision="correct", correction="new:P")]
    written, skipped = apply_review.decide(rows)
    assert ids(written) == ["1", "3"] and skipped == []
    assert apply_review.effective_depends(rows)["3"] == ["1"]


def test_a_correction_to_a_new_key_that_is_not_written_is_refused():
    rows = [row(1, "concept", "new:P", "k", decision="reject"),
            row(2, "concept", "new:C", "k", decision="correct", correction="new:P"),
            row(3, "target", ARO, "new:A", decision="correct", correction="new:Nowhere")]
    with pytest.raises(ValueError) as error:
        apply_review.decide(rows)
    message = str(error.value)
    assert "row 2: corrected to new:P" in message and "row 3: corrected to new:Nowhere" in message


def test_a_corrected_link_is_refused():
    rows = [row(1, "concept", "new:A", "k"),
            row(2, "link", "new:A", "new:A", "Ab_1 x", "1", decision="correct", correction="new:A")]
    with pytest.raises(ValueError, match="row 2: a link cannot be corrected. Reject it"):
        apply_review.decide(rows)


def test_a_corrected_label_fix_lands_as_an_alt_label():
    rows = [row(1, "concept", "new:V", "k"),
            row(2, "label_fix", "new:V", "anti-villin", "Ab_12 a", decision="correct", correction="Anti-villin"),
            row(3, "link", "new:V", "new:V", "Ab_12 a", "1"),
            row(4, "label_fix", "", "Anti-Y", "Ab_2 a", decision="correct", correction="Anti Y"),
            row(5, "link", "new:Y", "new:Y", "Ab_2 a", decision="reject")]
    written, skipped = apply_review.decide(rows)
    assert [(r.row, r.action, r.concept, r.value) for r in written] == [
        ("1", "concept", "new:V", "k"), ("2", "label_fix", "new:V", "Anti-villin"),
        ("2-alt", "altLabel", "new:V", "Anti-villin"), ("3", "link", "new:V", "new:V"),
        ("4", "label_fix", "", "Anti Y")]
    assert [(r.row, r.action, r.value, r.reason) for r in skipped] == [
        ("4-alt", "altLabel", "Anti Y", "label_fix 4 corrected; no altLabel, its link row 5 was rejected")]


def test_a_corrected_cycle_of_new_keys_is_left_undecided_not_hung():
    rows = [row(1, "concept", "new:A", "new:B"), row(2, "concept", "new:B", "new:A")]
    assert apply_review.undecided(rows, {}) == ["new:A", "new:B"]


def test_concepts_left_undecided_are_listed_never_filled_in():
    concepts = {c.iri: c for c in model.read_concepts(biomarkers_text(EXISTING_RO))}
    rows = [row(1, "concept", "new:Bare", "k"),
            row(2, "concept", "new:Termed", "k"),
            row(3, "closeMatch", "new:Termed", "http://x/1"),
            row(4, "concept", "new:Child", "new:Termed"),  # decided through its parent
            row(5, "concept", "new:NoTerm", "k"),
            row(6, "no_term", "new:NoTerm"),
            row(7, "concept", "new:Related", "k"),
            row(8, "relatedMatch", "new:Related", "http://x/2"),  # does not decide
            row(9, "concept", "new:UnderRo", ARO)]  # Ro has an exact match
    assert apply_review.undecided(rows, concepts) == ["new:Bare", "new:Related"]
    assert apply_review.undecided([rows[0], rows[2]], {}) == ["new:Bare"]  # a match alone makes no concept


# --- the whole pipeline --------------------------------------------------


def write_pair(tmp_path, name):
    folder = tmp_path / name
    folder.mkdir()
    biomarkers, disease = texts()
    (folder / "b.owl").write_text(biomarkers, encoding="utf-8", newline="\n")
    (folder / "d.owl").write_text(disease, encoding="utf-8", newline="\n")
    return folder / "b.owl", folder / "d.owl"


def test_accept_all_writes_what_propose_wrote(tmp_path):
    rows = proposed()
    preview = write_pair(tmp_path, "preview")  # what propose.py does
    model.write_rows(rows, *preview)

    table = tmp_path / "table.tsv"
    review_table.write(table, [dataclasses.replace(r, decision="accept") for r in rows])
    labels = {e.iri.removeprefix(model.ARI): e.label for e in model.read_entries(texts()[1])}
    written, skipped = apply_review.decide(review_table.read(table), labels)
    assert skipped == [] and len(written) == len(rows)
    applied = write_pair(tmp_path, "applied")
    model.write_rows(written, *applied)

    assert preview[0].read_bytes() == applied[0].read_bytes()
    assert preview[1].read_bytes() == applied[1].read_bytes()


def git(root, *args):
    command = ["git", "-C", str(root), "-c", "user.name=t", "-c", "user.email=t@t", *args]
    return subprocess.run(command, check=True, capture_output=True, text=True).stdout


@pytest.fixture
def repo(tmp_path):
    """A git repo whose commit holds the two module files, with the working copies since replaced."""
    root = tmp_path / "repo"
    (root / "ontologies").mkdir(parents=True)
    biomarkers, disease = texts()
    (root / "ontologies" / "ari_biomarkers.owl").write_bytes(biomarkers.encode())
    (root / "ontologies" / "ari_disease.owl").write_bytes(disease.encode())
    git(root, "init", "-q")
    git(root, "add", ".")
    git(root, "commit", "-qm", "base")
    for name in ("ari_biomarkers.owl", "ari_disease.owl"):
        (root / "ontologies" / name).write_text(EXISTING, encoding="utf-8")
    return root


def reviewed(root, decisions):
    """The proposed table with every row accepted except those in `decisions` (row id -> decision)."""
    rows = [dataclasses.replace(r, decision=decisions.get(r.row, "accept")) for r in proposed()]
    table = root / "review" / "antibodies.tsv"
    table.parent.mkdir()
    review_table.write(table, rows)
    return table


def test_apply_restores_the_base_files_writes_the_decided_rows_and_deletes_the_table(repo):
    fix = next(r.row for r in proposed() if r.action == "label_fix")  # Ab_12 "anti-villin 40"
    table = reviewed(repo, {fix: "reject"})
    summary = apply_review.apply(repo, "review/antibodies.tsv", "HEAD")

    assert not table.exists()
    biomarkers = (repo / "ontologies" / "ari_biomarkers.owl").read_text(encoding="utf-8")
    disease = (repo / "ontologies" / "ari_disease.owl").read_text(encoding="utf-8")
    assert EXISTING not in biomarkers + disease
    villin = next(c for c in model.read_concepts(biomarkers) if c.label == "anti-villin")
    assert villin.alt_labels == ["anti-villin 40"]
    ab12 = next(e for e in model.read_entries(disease) if e.iri.endswith("#Ab_12"))
    assert ab12.label == "anti-villin 40" and ab12.shared == [villin.iri]
    assert "label_fix" in summary and "reject" in summary


def test_apply_refuses_before_touching_any_file(repo):
    table = reviewed(repo, {"1": ""})
    with pytest.raises(ValueError, match="row 1"):
        apply_review.apply(repo, "review/antibodies.tsv", "HEAD")
    assert table.exists()
    for name in ("ari_biomarkers.owl", "ari_disease.owl"):
        assert (repo / "ontologies" / name).read_text() == EXISTING
