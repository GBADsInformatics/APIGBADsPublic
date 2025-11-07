import csv
import pytest
import spacy
from spacy.tokens import Span
from spacy.language import Language
import numpy as np
from unittest.mock import patch
from app.adapters.tail_adapter import TailAdapter, NER

@pytest.fixture
def tail_adapter_fixture(tmp_path):
    # Mock nationality CSV
    nationality_csv = tmp_path / "nationality.csv"
    with open(nationality_csv, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["nationality", "en_short_name"])
        writer.writeheader()
        writer.writerow({"nationality": "canadian", "en_short_name": "Canada"})
        writer.writerow({"nationality": "russian", "en_short_name": "Russia"})

    # Mock glove embeddings
    glove_txt = tmp_path / "glove.6B.50d.txt"
    with open(glove_txt, "w", encoding="utf-8") as f:
        f.write("chickens " + " ".join(["0.1"] * 50) + "\n")
        f.write("cows " + " ".join(["0.2"] * 50) + "\n")
        f.write("canada " + " ".join(["0.3"] * 50) + "\n")
        f.write("russia " + " ".join(["0.4"] * 50) + "\n")

    # Instead of calling TailAdapter.initialize (which may try to load large resources),
    # construct a minimal adapter state and attach a NER instance so tests can run deterministically.
    adapter = TailAdapter()
    adapter.nlp = spacy.blank("en")

    # Register and add a tiny test component that marks simple country tokens as GPE so
    # extract_country can pick them up without a full spaCy model.
    @Language.component("test_ents")
    def _test_set_ents(doc):
        ents = []
        for i, tok in enumerate(doc):
            if tok.text.lower() in ("canada", "russia", "russian"):
                ents.append(Span(doc, i, i + 1, label="GPE"))
        doc.ents = ents
        return doc

    # add the registered component by name
    adapter.nlp.add_pipe("test_ents", last=True)

    # Minimal data set matching the adapter's default categories
    data = {
        "Names": ["john", "jay", "dan", "nathan", "bob"],
        "Continents": ["asia", "north america", "south america", "europe", "oceania", "antarctica", "africa"],
        "Places": ["tokyo", "beijing", "washington", "mumbai", "ethiopia", "canada", "sub-saharan africa", "madagascar"],
        "Species": ["cows", "chickens", "poultry", "bovine", "horses", "tigers", "puffins", "koalas", "lion", "hawks"],
        "Years": ["2001", "1971", "96", "2000s", "93'"],
        "General": ["the", "by", "here", "population", "random", "tile", "canda"],
        "Regions": ["central asia", "latin america", "oceania", "caribbean"],
        "Mistakes": ["rusia", "subsaharan", "saharan"],
    }

    categories = {word: k for k, v in data.items() for word in v}

    # Read nationality mapping from the temp CSV we created
    nationality_mapping = {}
    with open(nationality_csv, newline="", encoding="utf-8") as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            if "nationality" in row and "en_short_name" in row:
                nationality_mapping[row["nationality"].lower()] = row["en_short_name"]

    # Load embeddings from the mocked glove file so process_match_scores won't KeyError
    embeddings_index = {}
    words = []
    with open(glove_txt, encoding="utf-8") as gf:
        for line in gf:
            parts = line.strip().split()
            if not parts:
                continue
            w = parts[0]
            vec = np.array([float(x) for x in parts[1:]], dtype=np.float32)
            embeddings_index[w] = vec
            words.append(w)
    data_embeddings = {k: v for k, v in embeddings_index.items() if k in [w for sub in data.values() for w in sub]}

    # Attach attributes and create NER instance
    adapter.data = data
    adapter.categories = categories
    adapter.embeddings_index = embeddings_index
    adapter.data_embeddings = data_embeddings
    adapter.words = words
    adapter.nationality_mapping = nationality_mapping
    adapter.V = set(words)
    adapter.ner = NER(adapter.nlp, adapter.data, adapter.categories, adapter.embeddings_index, adapter.data_embeddings, adapter.nationality_mapping)

    yield adapter

def test_perform_ner_basic(tail_adapter_fixture):
    adapter = tail_adapter_fixture
    query = "Chickens in Canada in 2019"

    with patch.object(adapter.ner, "process_match_scores", side_effect=lambda word, cat: word.capitalize() if word.lower() in ["chickens", "canada", "2019"] else None):
        result = adapter.perform_ner(query)
    
    assert set(result.keys()) == {"species", "years", "countries"}
    assert "Chickens" in result["species"]
    assert "Canada" in result["countries"]
    assert "2019" in result["years"]

def test_perform_ner_with_nationality(tail_adapter_fixture):
    """
    Check that nationalities are correctly linked to countries.
    """
    adapter = tail_adapter_fixture
    query = "Russian poultry population"
    result = adapter.perform_ner(query)
    assert "Russia" in result["countries"]

def test_extract_species_returns_empty_if_none(tail_adapter_fixture):
    """
    Check species extraction returns empty list for unknown words.
    """
    adapter = tail_adapter_fixture
    query = "Unrelated text without species"
    result = adapter.perform_ner(query)
    assert result["species"] == []

def test_extract_years_detects_current_year(tail_adapter_fixture):
    """
    If query mentions 'this year', current year should be added.
    """
    adapter = tail_adapter_fixture
    current_year = str(adapter.ner.find_curr_year("this year"))
    query = "Population of cows this year"
    result = adapter.perform_ner(query)
    assert current_year in result["years"]
