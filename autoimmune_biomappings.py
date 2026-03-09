"""Generate mappings."""

from collections.abc import Iterable
import csv

import pyobo
from bioregistry import NormalizedNamableReference
from curies.vocabulary import exact_match, lexical_matching_process
from sssom_pydantic import MappingTool, SemanticMapping
from tqdm import tqdm

from biomappings.resources import append_predictions
from biomappings.utils import get_script_url


def iterate_autoimmune_matches() -> Iterable[SemanticMapping]:
    """Iterate over predictions from autoimmune terms CSV to GO and MeSH."""
    provenance = get_script_url(__file__)
    grounder = pyobo.get_grounder({"mondo", "mesh"})
    
    with open("../autoimmune-single.csv", "r") as f:
        reader = csv.reader(f)
        next(reader)  # Skip header row
        for row in tqdm(reader, desc="Mapping Autoimmune Terms"):
            if not row:
                continue
            identifier = row[0]
            name = row[1]
            
            for match in grounder.get_matches(name):
                if match.prefix not in {"mondo", "mesh"}:
                    continue

                yield SemanticMapping(
                    subject=NormalizedNamableReference(
                        prefix="autoimmune", identifier=identifier, name=name
                    ),
                    predicate=exact_match,
                    object=match.reference,
                    justification=lexical_matching_process,
                    confidence=match.score,
                    mapping_tool=MappingTool(name=provenance),
                )


if __name__ == "__main__":
    append_predictions(iterate_autoimmune_matches())
