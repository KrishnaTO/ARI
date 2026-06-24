"""Service layer for reading and editing the ARI T1D ontology via owlready2."""
import json
import shutil
import uuid
from datetime import datetime
from pathlib import Path

from owlready2 import World, label, comment, destroy_entity

from .feedback_service import FeedbackStore
from .schema import CATEGORIES, SEEALSO_IRI


def _split_csv(values):
    """Flatten cross-reference annotation values, splitting any that contain
    comma-separated ids into separate entries (e.g. OMOP "12345, 67890").
    Order preserved, duplicates removed."""
    out = []
    for v in (values or []):
        for part in str(v).split(","):
            part = part.strip()
            if part and part not in out:
                out.append(part)
    return out


class OntologyService:
    def __init__(self, path: str):
        self.path = Path(path)
        if not self.path.exists():
            raise FileNotFoundError(f"Ontology file not found: {self.path}")
        self.feedback = FeedbackStore(self.path.parent.parent / "feedback")
        self._load()

    def _load(self):
        # Load via a file object so Windows paths don't break owlready2's
        # file:// URI handling. The ontology's real base IRI is read from the file.
        self.world = World()
        placeholder = self.world.get_ontology("http://ari.local/ontology")
        with open(self.path, "rb") as f:
            self.onto = placeholder.load(fileobj=f)

    @property
    def base(self) -> str:
        return self.onto.base_iri

    # --------------------------------------------------------- helpers
    def _entity(self, iri: str):
        e = self.world[iri]
        if e is None:
            raise KeyError(f"No entity with IRI: {iri}")
        return e

    def _get_label(self, e) -> str:
        vals = label[e] if hasattr(e, 'storid') else []
        return str(vals[0]) if vals else (e.name if hasattr(e, 'name') else str(e))

    def _get_comment(self, e) -> str:
        vals = comment[e] if hasattr(e, 'storid') else []
        return str(vals[0]) if vals else ""

    def _get_annotation(self, e, prop_name: str) -> list:
        prop = self.world[prop_name]
        if prop is None:
            return []
        vals = prop[e] if hasattr(e, 'storid') else []
        return [str(v) for v in vals]

    def _get_data(self, e, prop_name: str) -> list:
        prop = self.world[prop_name]
        if prop is None:
            return []
        vals = prop[e] if hasattr(e, 'storid') else []
        return list(vals)

    def _get_objects(self, e, prop_name: str) -> list:
        prop = self.world[prop_name]
        if prop is None:
            return []
        vals = prop[e] if hasattr(e, 'storid') else []
        return list(vals)

    def _is_obsolete(self, e) -> bool:
        vals = self._get_annotation(e, self.base + "ARI_Obsolete")
        return bool(vals) and str(vals[0]).lower() == "true"

    def _ref(self, e) -> dict:
        return {
            "iri": e.iri,
            "name": self._get_label(e),
            "local_name": e.name,
            "obsolete": self._is_obsolete(e),
        }

    def _disease_class(self):
        return self.world[self.base + "AutoimmuneDisease"]

    def _all_diseases(self) -> list:
        cls = self._disease_class()
        return list(cls.instances(world=self.world)) if cls else []

    # --------------------------------------------------------- READ API
    def overview(self) -> dict:
        return {
            "iri": self.base,
            "file": str(self.path),
            "disease_count": len(self._all_diseases()),
            "individuals": len(list(self.onto.individuals())),
            "classes": len(list(self.onto.classes())),
            "version": self._current_version(),
        }

    def get_diseases_list(self) -> list:
        """Flat list of all disease individuals."""
        results = []
        for ind in self._all_diseases():
            results.append({
                "iri": ind.iri,
                "name": self._get_label(ind),
                "local_name": ind.name,
                "obsolete": self._is_obsolete(ind),
                "synonyms": self._get_annotation(ind, self.base + "ARI_Synonym"),
            })
        return sorted(results, key=lambda x: x["name"])

    def get_alphabetical_tree(self) -> list:
        """Diseases grouped under their parent disease; children expand from parent."""
        base = self.base
        diseases = self._all_diseases()
        # Map each disease -> its parent diseases
        parent_of = {}
        for d in diseases:
            parents = self._get_objects(d, base + "hasParentDisease")
            parent_of[d.iri] = [p.iri for p in parents]
        # children index
        children_idx = {}
        for d in diseases:
            for piri in parent_of[d.iri]:
                children_idx.setdefault(piri, []).append(d)

        def node(d):
            kids = sorted(children_idx.get(d.iri, []), key=lambda x: self._get_label(x))
            return {
                "iri": d.iri,
                "name": self._get_label(d),
                "local_name": d.name,
                "obsolete": self._is_obsolete(d),
                "children": [node(k) for k in kids],
            }

        roots = [d for d in diseases if not parent_of[d.iri]]
        roots = sorted(roots, key=lambda x: self._get_label(x))
        return [node(d) for d in roots]

    def get_tissue_hierarchy(self) -> list:
        """Anatomical-structure (UBERON_0010000) hierarchy with diseases attached
        under each tissue they target."""
        base = self.base
        root = self.world[base + "MulticellularAnatomicalStructure"]
        if root is None:
            return []
        diseases = self._all_diseases()
        # disease -> set of tissue classes it directly targets
        dis_classes = {}
        for d in diseases:
            classes = set()
            for tis in self._get_objects(d, base + "targetsTissue"):
                for c in getattr(tis, "is_a", []):
                    if hasattr(c, "iri"):
                        classes.add(c.iri)
            dis_classes[d.iri] = classes

        def walk(cls):
            diseases_here = [
                self._ref(d) for d in diseases if cls.iri in dis_classes[d.iri]
            ]
            diseases_here.sort(key=lambda x: x["name"])
            children = []
            for sub in sorted(cls.subclasses(), key=lambda c: c.name if hasattr(c, 'name') else ""):
                if hasattr(sub, 'namespace') and sub.namespace == self.onto:
                    children.append(walk(sub))
            ari_id = self._get_annotation(cls, base + "ARI_ID")
            return {
                "iri": cls.iri,
                "name": self._get_label(cls),
                "local_name": cls.name,
                "ari_id": ari_id[0] if ari_id else "",
                "diseases": diseases_here,
                "children": children,
            }

        return [walk(root)]

    def get_symptoms_index(self) -> list:
        """Flat list of all symptom individuals across diseases (symptoms context view)."""
        base = self.base
        cls = self.world[base + "Symptom"]
        if cls is None:
            return []
        # map symptom -> diseases that have it
        diseases = self._all_diseases()
        owner = {}
        for d in diseases:
            for s in self._get_objects(d, base + "hasSymptom"):
                owner.setdefault(s.iri, []).append(self._get_label(d))
        results = []
        for s in cls.instances(world=self.world):
            results.append({
                "iri": s.iri,
                "name": self._get_label(s),
                "likelihood": (self._get_data(s, base + "likelihood") or [""])[0],
                "obsolete": self._is_obsolete(s),
                "diseases": owner.get(s.iri, []),
            })
        return sorted(results, key=lambda x: x["name"])

    def get_disease_detail(self, iri: str) -> dict:
        """Return full detail about a disease individual and all its associations."""
        e = self._entity(iri)
        base = self.base

        d = {
            "iri": e.iri,
            "name": self._get_label(e),
            "local_name": e.name,
            "ari_id": self._get_annotation(e, base + "ARI_ID"),
            "definition": self._get_comment(e),
            "obsolete": self._is_obsolete(e),
            "synonyms": self._get_annotation(e, base + "ARI_Synonym"),
            "snomed": _split_csv(self._get_annotation(e, base + "ARI_SNOMED")),
            "doid": _split_csv(self._get_annotation(e, base + "ARI_DOID")),
            "umls": _split_csv(self._get_annotation(e, base + "ARI_UMLS")),
            "mondo": _split_csv(self._get_annotation(e, base + "ARI_MONDO")),
            "icd10": _split_csv(self._get_annotation(e, base + "ARI_ICD10")),
            "mesh": _split_csv(self._get_annotation(e, base + "ARI_MESH")),
            "nci": _split_csv(self._get_annotation(e, base + "ARI_NCI")),
            "omop": _split_csv(self._get_annotation(e, base + "ARI_OMOP")),
            "dxcode": _split_csv(self._get_annotation(e, base + "ARI_DXCODE")),
            "version": self._get_annotation(e, base + "ARI_Version"),
            "prevalence_desc": self._get_annotation(e, base + "ARI_PrevalenceDesc"),
            "pubmed": self._get_annotation(e, base + "ARI_Pubmed"),
            "def_source": self._get_annotation(e, base + "ARI_DefSource"),
            "ref_links": self._get_annotation(e, base + "ARI_RefLink"),
            "clinical_subtypes": self._get_annotation(e, base + "ARI_ClinicalSubtype"),
            "authors": self._get_annotation(e, base + "ARI_Author"),
            "author_date": self._get_annotation(e, base + "ARI_AuthorDate"),
            "survey_code": self._get_annotation(e, base + "ARI_SurveyCode"),
            "changelog": self._get_annotation(e, base + "ARI_ChangeLog"),
        }

        # Data properties
        d["evidence_quality"] = self._get_data(e, base + "evidenceQuality")
        d["disease_category"] = self._get_data(e, base + "diseaseCategory")
        d["prevalence_per_100k"] = self._get_data(e, base + "prevalencePer100k")
        d["prevalence_value"] = self._get_data(e, base + "prevalenceValue")
        d["incidence_rate"] = self._get_data(e, base + "incidenceRate")
        d["demographic_bias"] = self._get_data(e, base + "demographicBias")
        d["age_range"] = self._get_data(e, base + "ageRange")

        # Object property links
        d["tissue_targets"] = [self._ref(o) for o in self._get_objects(e, base + "targetsTissue")]
        d["parent_categories"] = [self._ref(o) for o in self._get_objects(e, base + "hasParentCategory")]
        d["parent_disease"] = [self._ref(o) for o in self._get_objects(e, base + "hasParentDisease")]

        # Subtypes (diseases that name this one as parent)
        d["subtypes"] = []
        for other in self._all_diseases():
            parents = self._get_objects(other, base + "hasParentDisease")
            if any(p.iri == e.iri for p in parents):
                d["subtypes"].append(self._ref(other))

        # Symptoms
        d["symptoms"] = []
        for o in self._get_objects(e, base + "hasSymptom"):
            d["symptoms"].append({
                "iri": o.iri,
                "name": self._get_label(o),
                "obsolete": self._is_obsolete(o),
                "likelihood": self._get_data(o, base + "likelihood"),
                "description": self._get_data(o, base + "symptomDescription"),
                "seeAlso": self._get_data(o, "http://www.w3.org/2000/01/rdf-schema#seeAlso"),
                "source": self._get_data(o, base + "sourcePMID"),
            })

        # Environmental triggers
        d["environmental_factors"] = []
        for o in self._get_objects(e, base + "hasEnvironmentalTrigger"):
            d["environmental_factors"].append({
                "iri": o.iri,
                "name": self._get_label(o),
                "obsolete": self._is_obsolete(o),
                "description": self._get_data(o, base + "triggerDescription"),
                "likelihood": self._get_data(o, base + "likelihood"),
                "source": self._get_data(o, base + "sourcePMID"),
            })

        # Antibodies
        d["antibodies"] = []
        for o in self._get_objects(e, base + "hasAntibody"):
            d["antibodies"].append({
                "iri": o.iri,
                "name": self._get_label(o),
                "obsolete": self._is_obsolete(o),
                "frequency": self._get_data(o, base + "antibodyFrequency"),
                "diagnostic_value": self._get_data(o, base + "antibodyDiagnosticValue"),
                "source": self._get_data(o, base + "sourcePMID"),
            })

        # Genetic associations
        d["genetic"] = []
        for o in self._get_objects(e, base + "hasGeneticAssociation"):
            d["genetic"].append({
                "iri": o.iri,
                "name": self._get_label(o),
                "obsolete": self._is_obsolete(o),
                "locus": self._get_data(o, base + "chromosomalLocus"),
                "product": self._get_data(o, base + "geneticProduct"),
                "risk_effect": self._get_data(o, base + "geneticRiskEffect"),
                "odds_ratio": self._get_data(o, base + "geneticOddsRatio"),
                "hla_effect": self._get_data(o, base + "hlaEffect"),
                "hla_mechanism": self._get_data(o, base + "hlaMechanism"),
                "source": self._get_data(o, base + "sourcePMID"),
            })

        # Treatments
        d["treatments"] = []
        for o in self._get_objects(e, base + "hasTreatment"):
            d["treatments"].append({
                "iri": o.iri,
                "name": self._get_label(o),
                "obsolete": self._is_obsolete(o),
                "type": self._get_data(o, base + "treatmentType"),
                "description": self._get_data(o, base + "treatmentDescription"),
                "fda_status": self._get_data(o, base + "treatmentFdaStatus"),
                "source": self._get_data(o, base + "sourcePMID"),
            })

        # Etiology
        d["etiology"] = []
        for o in self._get_objects(e, base + "hasEtiologyFactor"):
            d["etiology"].append({
                "iri": o.iri,
                "name": self._get_label(o),
                "obsolete": self._is_obsolete(o),
                "origin_type": self._get_data(o, base + "etiologyOriginType"),
                "description": self._get_data(o, base + "etiologyDescription"),
                "excerpt": self._get_data(o, base + "etiologyExcerpt"),
                "source": self._get_data(o, base + "sourcePMID"),
            })

        # Biochemical markers
        d["biomarkers"] = []
        for o in self._get_objects(e, base + "hasBiomarker"):
            d["biomarkers"].append({
                "iri": o.iri,
                "name": self._get_label(o),
                "obsolete": self._is_obsolete(o),
                "description": self._get_comment(o),
                "diagnostic_use": self._get_data(o, base + "markerDiagnosticUse"),
                "source": self._get_data(o, base + "sourcePMID"),
            })

        # Pathophysiology pathway steps (ordered)
        d["pathway"] = []
        for o in self._get_objects(e, base + "hasPathwayStep"):
            order = self._get_data(o, base + "stepOrder")
            d["pathway"].append({
                "iri": o.iri,
                "name": self._get_label(o),
                "order": order[0] if order else 0,
                "category": (self._get_data(o, base + "stepCategory") or [""])[0],
                "description": (self._get_data(o, base + "stepDescription") or [""])[0],
                "source": self._get_data(o, base + "sourcePMID"),
            })
        d["pathway"].sort(key=lambda x: x["order"])

        # Immune / molecular components
        def component_list(prop, desc_key="mediatorDescription"):
            out = []
            for o in self._get_objects(e, base + prop):
                out.append({
                    "iri": o.iri,
                    "name": self._get_label(o),
                    "obsolete": self._is_obsolete(o),
                    "description": self._get_data(o, base + desc_key),
                    "relevance": self._get_data(o, base + "componentRelevance"),
                    "source": self._get_data(o, base + "sourcePMID"),
                })
            return out

        d["cytokines"] = component_list("involvesCytokine")
        d["tcells"] = component_list("involvesTCell", desc_key="tCellRole")
        d["apcs"] = component_list("involvesAPC")
        d["transcription_factors"] = component_list("involvesTranscriptionFactor")
        d["innate_components"] = component_list("involvesInnateComponent")
        d["complement"] = component_list("involvesComplement")
        d["receptors"] = component_list("involvesReceptor")
        d["netosis"] = component_list("involvesNETosis")
        d["inflammasome"] = component_list("involvesInflammasome")
        d["acute_phase_reactants"] = component_list("involvesAcutePhaseReactant")
        d["antigens"] = component_list("involvesAntigen")

        return d

    def get_tissues(self) -> list:
        """All tissue-target individuals available for new-disease creation."""
        base = self.base
        root = self.world[base + "MulticellularAnatomicalStructure"]
        if root is None:
            return []
        tissue_classes = set()

        def _collect(cls):
            tissue_classes.add(cls)
            for sub in cls.subclasses(world=self.world):
                _collect(sub)

        _collect(root)
        results, seen = [], set()
        for ind in self.onto.individuals():
            if ind.iri in seen:
                continue
            for cls in getattr(ind, "is_a", []):
                if hasattr(cls, "iri") and cls in tissue_classes:
                    seen.add(ind.iri)
                    results.append({
                        "iri": ind.iri,
                        "name": self._get_label(ind),
                        "local_name": ind.name if hasattr(ind, "name") else "",
                    })
                    break
        return sorted(results, key=lambda x: x["name"])

    def search(self, query: str) -> list:
        q = query.lower()
        base = self.base
        diseases = self._all_diseases()
        disease_iris = {d.iri for d in diseases}
        results = []
        seen = set()

        def add(ind, is_disease, match):
            if ind.iri in seen:
                return
            seen.add(ind.iri)
            results.append({
                "iri": ind.iri,
                "name": self._get_label(ind),
                "local_name": ind.name,
                "obsolete": self._is_obsolete(ind),
                "is_disease": is_disease,
                "match": match,
            })

        def matches(text):
            return text and q in text.lower()

        # Diseases: match on label / local name, then synonyms, then target tissue.
        for d in diseases:
            if matches(self._get_label(d)) or (hasattr(d, "name") and matches(d.name)):
                add(d, True, "name")
                continue
            syn = next((s for s in self._get_annotation(d, base + "ARI_Synonym") if matches(s)), None)
            if syn:
                add(d, True, f"synonym: {syn}")
                continue
            tis = next((self._get_label(t) for t in self._get_objects(d, base + "targetsTissue")
                        if matches(self._get_label(t))), None)
            if tis:
                add(d, True, f"tissue: {tis}")

        # Other individuals: match on label / local name.
        for ind in self.onto.individuals():
            if ind.iri in disease_iris:
                continue
            if matches(self._get_label(ind)) or (hasattr(ind, "name") and matches(ind.name)):
                add(ind, False, "name")

        # diseases first, then by name
        results.sort(key=lambda r: (not r["is_disease"], r["name"].lower()))
        return results[:100]

    # --------------------------------------------------------- WRITE API
    # Editable disease fields -> (kind, property-iri-suffix, caster)
    EDITABLE = {
        "name":              ("label", None, str),
        "definition":        ("comment", None, str),
        "synonyms":          ("multi_ann", "ARI_Synonym", str),
        "clinical_subtypes": ("multi_ann", "ARI_ClinicalSubtype", str),
        "snomed":            ("multi_ann", "ARI_SNOMED", str),
        "doid":              ("multi_ann", "ARI_DOID", str),
        "umls":              ("multi_ann", "ARI_UMLS", str),
        "mondo":             ("multi_ann", "ARI_MONDO", str),
        "icd10":             ("multi_ann", "ARI_ICD10", str),
        "mesh":              ("multi_ann", "ARI_MESH", str),
        "nci":               ("multi_ann", "ARI_NCI", str),
        "omop":              ("multi_ann", "ARI_OMOP", str),
        "dxcode":            ("multi_ann", "ARI_DXCODE", str),
        "def_source":        ("multi_ann", "ARI_DefSource", str),
        "pubmed":            ("ann", "ARI_Pubmed", str),
        "prevalence_desc":   ("ann", "ARI_PrevalenceDesc", str),
        "obsolete":          ("ann", "ARI_Obsolete", str),
        "evidence_quality":  ("data", "evidenceQuality", str),
        "disease_category":  ("data", "diseaseCategory", str),
        "incidence_rate":    ("data", "incidenceRate", str),
        "demographic_bias":  ("data", "demographicBias", str),
        "age_range":         ("data", "ageRange", str),
        "prevalence_per_100k": ("data", "prevalencePer100k", float),
        "prevalence_value":  ("data", "prevalenceValue", float),
    }

    def update_disease(self, iri: str, changes: dict, editor: str = "user") -> dict:
        e = self._entity(iri)
        base = self.base
        changed = []

        for key, raw in changes.items():
            spec = self.EDITABLE.get(key)
            if not spec:
                continue
            kind, suffix, caster = spec

            if kind == "label":
                label[e] = [str(raw)] if str(raw).strip() else []
            elif kind == "comment":
                comment[e] = [str(raw)] if str(raw).strip() else []
            elif kind == "multi_ann":
                prop = self.world[base + suffix]
                if prop is None:
                    continue
                if isinstance(raw, str):
                    items = [s.strip() for s in raw.replace("\n", ",").split(",")]
                else:
                    items = [str(s).strip() for s in (raw or [])]
                prop[e] = [s for s in items if s]
            elif kind == "ann":
                prop = self.world[base + suffix]
                if prop is None:
                    continue
                prop[e] = [str(raw)] if str(raw).strip() != "" else []
            elif kind == "data":
                prop = self.world[base + suffix]
                if prop is None:
                    continue
                if str(raw).strip() == "":
                    prop[e] = []
                else:
                    try:
                        prop[e] = [caster(raw)]
                    except (ValueError, TypeError):
                        continue
            changed.append(key)

        if changed:
            self._append_changelog(e, editor, f"Edited: {', '.join(sorted(changed))}")
            self._save()

        return self.get_disease_detail(iri)

    def create_disease(self, data: dict, editor: str = "user") -> dict:
        """Create a new AutoimmuneDisease individual with provisional IRI.

        Required keys in data: label, definition, def_source, tissue_iris (list[str]).
        Optional: parent_iri, synonyms, authors, author_date, clinical_subtypes,
                  and any key from EDITABLE (disease_category, icd10, etc.).
        """
        base = self.base
        dis_cls = self._disease_class()
        if dis_cls is None:
            raise KeyError("AutoimmuneDisease class not found")

        lbl = str(data.get("label", "")).strip()
        if not lbl:
            raise ValueError("label is required")

        local = f"ARI_new_{uuid.uuid4().hex[:8]}"
        with self.onto:
            new_d = dis_cls(local)

        label[new_d] = [lbl]

        defn = str(data.get("definition", "")).strip()
        if defn:
            comment[new_d] = [defn]

        def _ann(suffix, val):
            prop = self.world[base + suffix]
            v = str(val).strip() if val else ""
            if prop and v:
                prop[new_d] = [v]

        def_src = data.get("def_source", "")
        def_src_prop = self.world[base + "ARI_DefSource"]
        if def_src_prop and def_src:
            items = def_src if isinstance(def_src, list) else [str(def_src).strip()]
            def_src_prop[new_d] = [s for s in items if s]
        _ann("ARI_Author", data.get("authors", ""))
        _ann("ARI_AuthorDate", data.get("author_date", ""))

        # Tissue targets (object property)
        tis_prop = self.world[base + "targetsTissue"]
        if tis_prop:
            for tiri in (data.get("tissue_iris") or []):
                tis = self.world[tiri]
                if tis is not None:
                    tis_prop[new_d].append(tis)

        # Parent disease (object property)
        parent_iri = str(data.get("parent_iri", "")).strip()
        if parent_iri:
            par_prop = self.world[base + "hasParentDisease"]
            parent = self.world[parent_iri]
            if par_prop and parent is not None:
                par_prop[new_d] = [parent]

        def _multi(suffix, val):
            prop = self.world[base + suffix]
            if not prop:
                return
            if isinstance(val, str):
                items = [s.strip() for s in val.replace("\n", ",").split(",")]
            else:
                items = [str(s).strip() for s in (val or [])]
            prop[new_d] = [s for s in items if s]

        _multi("ARI_Synonym", data.get("synonyms", ""))
        _multi("ARI_ClinicalSubtype", data.get("clinical_subtypes", ""))

        # Other EDITABLE fields delegated generically
        skip = {"name", "definition", "synonyms", "clinical_subtypes", "def_source", "obsolete"}
        for key, raw in data.items():
            if key in skip or key not in self.EDITABLE:
                continue
            kind, suffix, caster = self.EDITABLE[key]
            if kind in ("label", "comment"):
                continue
            elif kind == "multi_ann":
                _multi(suffix, raw)
            elif kind == "ann":
                prop = self.world[base + suffix]
                if prop:
                    prop[new_d] = [str(raw)] if str(raw).strip() else []
            elif kind == "data":
                prop = self.world[base + suffix]
                if prop:
                    sv = str(raw).strip()
                    if not sv:
                        prop[new_d] = []
                    else:
                        try:
                            prop[new_d] = [caster(raw)]
                        except (ValueError, TypeError):
                            pass

        self._append_changelog(new_d, editor, f"Created: {lbl}")
        self._save()
        return self.get_disease_detail(new_d.iri)

    def _save(self):
        self.onto.save(file=str(self.path), format="rdfxml")

    def _append_changelog(self, disease_e, editor: str, msg: str):
        ts = datetime.now().strftime("%Y-%m-%d %H:%M")
        clog = self.world[self.base + "ARI_ChangeLog"]
        if clog is not None:
            clog[disease_e] = list(clog[disease_e]) + [f"{ts} | {editor} | {msg}"]

    # --------------------------------------------------------- ITEM CRUD
    def get_schema(self) -> dict:
        """Field schema for every editable disease-data category."""
        return CATEGORIES

    def _set_item_field(self, e, field: dict, raw):
        """Write one field onto an individual based on its declared kind."""
        kind = field["kind"]
        base = self.base
        sval = "" if raw is None else str(raw)

        if kind == "label":
            label[e] = [sval] if sval.strip() else []
        elif kind == "comment":
            comment[e] = [sval] if sval.strip() else []
        elif kind == "obsolete":
            prop = self.world[base + "ARI_Obsolete"]
            if prop is not None:
                on = raw is True or sval.strip().lower() in ("true", "1", "yes", "on")
                prop[e] = ["true" if on else "false"]
        elif kind == "seeAlso":
            prop = self.world[SEEALSO_IRI]
            if prop is not None:
                prop[e] = [sval] if sval.strip() else []
        elif kind == "intdata":
            prop = self.world[base + field["key"]]
            if prop is None:
                return
            if sval.strip() == "":
                prop[e] = []
            else:
                try:
                    prop[e] = [int(float(sval))]
                except (ValueError, TypeError):
                    pass
        else:  # "data" or "ann"
            prop = self.world[base + field["key"]]
            if prop is None:
                return
            prop[e] = [sval] if sval.strip() != "" else []

    def _apply_item_fields(self, e, category: str, values: dict) -> list:
        applied = []
        for f in CATEGORIES[category]["fields"]:
            if f["key"] in values:
                self._set_item_field(e, f, values[f["key"]])
                applied.append(f["key"])
        return applied

    def add_item(self, disease_iri: str, category: str, values: dict, editor: str = "user") -> dict:
        if category not in CATEGORIES:
            raise KeyError(f"Unknown category: {category}")
        spec = CATEGORIES[category]
        de = self._entity(disease_iri)
        cls = self.world[self.base + spec["cls"]]
        if cls is None:
            raise KeyError(f"Class not found: {spec['cls']}")
        local = f"{spec['id_prefix']}_{uuid.uuid4().hex[:8]}"
        with self.onto:
            new = cls(local)
        self._apply_item_fields(new, category, values)
        if not (label[new] if hasattr(new, 'storid') else []):
            label[new] = [str(values.get("name") or local)]
        link = self.world[self.base + spec["link"]]
        link[de].append(new)
        self._append_changelog(de, editor, f"Added {spec['label']}: {self._get_label(new)}")
        self._save()
        return self.get_disease_detail(disease_iri)

    def update_item(self, item_iri: str, category: str, changes: dict,
                    disease_iri: str = "", editor: str = "user") -> dict:
        if category not in CATEGORIES:
            raise KeyError(f"Unknown category: {category}")
        e = self._entity(item_iri)
        applied = self._apply_item_fields(e, category, changes)
        if disease_iri and applied:
            de = self._entity(disease_iri)
            self._append_changelog(
                de, editor,
                f"Edited {CATEGORIES[category]['label']} '{self._get_label(e)}': {', '.join(applied)}")
        self._save()
        return self.get_disease_detail(disease_iri) if disease_iri else {"ok": True}

    def delete_item(self, item_iri: str, category: str, disease_iri: str,
                    editor: str = "user") -> dict:
        e = self._entity(item_iri)
        de = self._entity(disease_iri)
        name = self._get_label(e)
        spec = CATEGORIES.get(category)
        if spec:
            link = self.world[self.base + spec["link"]]
            if link is not None:
                try:
                    link[de].remove(e)
                except (ValueError, KeyError):
                    pass
        destroy_entity(e)
        self._append_changelog(de, editor, f"Deleted {spec['label'] if spec else 'item'}: {name}")
        self._save()
        return self.get_disease_detail(disease_iri)

    # --------------------------------------------------------- RELEASES
    @property
    def _releases_dir(self) -> Path:
        d = self.path.parent.parent / "releases"
        d.mkdir(exist_ok=True)
        return d

    @property
    def _manifest_path(self) -> Path:
        return self._releases_dir / "releases.json"

    def list_releases(self) -> list:
        if self._manifest_path.exists():
            try:
                return json.loads(self._manifest_path.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                return []
        return []

    def _current_version(self) -> str:
        releases = self.list_releases()
        if releases:
            return releases[-1].get("version", "1.0")
        # fall back to a disease version annotation
        for d in self._all_diseases():
            v = self._get_annotation(d, self.base + "ARI_Version")
            if v:
                return v[0]
        return "1.0"

    def _next_version(self) -> str:
        releases = self.list_releases()
        return f"1.{len(releases) + 1}"

    def create_release(self, version: str = "", notes: str = "", editor: str = "admin") -> dict:
        """Snapshot the current ontology into releases/, stamp the version onto every
        disease, and record a per-disease changelog entry."""
        version = version.strip() or self._next_version()
        ts_human = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        ts_file = datetime.now().strftime("%Y%m%d_%H%M%S")

        # Stamp version + changelog onto every disease before snapshotting
        base = self.base
        ver_prop = self.world[base + "ARI_Version"]
        clog = self.world[base + "ARI_ChangeLog"]
        for d in self._all_diseases():
            if ver_prop is not None:
                ver_prop[d] = [version]
            if clog is not None:
                note = f" - {notes}" if notes else ""
                entry = f"{ts_human} | {editor} | Released v{version}{note}"
                clog[d] = list(clog[d]) + [entry]
        self._save()

        fname = f"ari_t1d_v{version}_{ts_file}.owl"
        dest = self._releases_dir / fname
        shutil.copy2(self.path, dest)

        record = {
            "version": version,
            "file": fname,
            "timestamp": ts_human,
            "notes": notes,
            "released_by": editor,
            "diseases": len(self._all_diseases()),
            "individuals": len(list(self.onto.individuals())),
        }
        records = self.list_releases()
        records.append(record)
        self._manifest_path.write_text(json.dumps(records, indent=2), encoding="utf-8")

        # Expire per-term feedback (entries flagged "keep" are retained).
        fb = self.feedback.archive_on_release(version)
        record["feedback_archived"] = fb["archived"]
        record["feedback_retained"] = fb["retained"]
        return record
