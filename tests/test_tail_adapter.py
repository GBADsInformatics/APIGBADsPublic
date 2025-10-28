import os
import csv
import pytest
import spacy
from unittest.mock import patch
from app.adapters.tail_adapter import TailAdapter

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

    # Save original os.path.join
    real_join = os.path.join

    # Patch TailAdapter paths
    with patch("app.adapters.tail_adapter.os.path.join") as mock_join:
        def join_side_effect(*args):
            fname = args[-1]
            if "glove.6B.50d.txt" in fname:
                return str(glove_txt)
            if "nationality.csv" in fname:
                return str(nationality_csv)
            return real_join(*args)  # use the real join, not the patched one
        mock_join.side_effect = join_side_effect

        adapter = TailAdapter()
        adapter.nlp = spacy.blank("en")
        adapter.initialize()
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
