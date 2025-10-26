import os
import csv
import spacy
import numpy as np
import logging
import pytz
import datetime
import nltk
from nltk.corpus import stopwords
from nltk.tokenize import word_tokenize


class NER:
    """Performs Named Entity Recognition and data extraction using shared TailAdapter resources."""

    def __init__(self, nlp, data, categories, embeddings_index, data_embeddings, nationality_mapping):
        self.nlp = nlp
        self.data = data
        self.categories = categories
        self.embeddings_index = embeddings_index
        self.data_embeddings = data_embeddings
        self.nationality_mapping = nationality_mapping

    def link_nationality_to_country(self, text):
        """
        Links the nationality to a country (Canadian -> Canada)
        :return: mapping of nationalityh or empty string
        """
        for token in self.nlp(text):
            if token.text.lower() in self.nationality_mapping:
                return self.nationality_mapping[token.text.lower()]
        return ""

    def remove_stopwords(self, text):
        """
        Removes stop words for better parsing
        :return: list of words that do not include stopwords
        """
        all_stopwords = stopwords.words("english")
        all_stopwords.extend(["The", "population"])
        tokens = word_tokenize(text)
        return " ".join([w for w in tokens if w not in all_stopwords])

    def process_match_scores(self, check_meaning, category_to_check):
        """
        Provides a likeliness scoring to how closely a word relates to a category to check against
        :return: Returns the meaning capitalized or None if the highest key doesnt match the categhory to check
        """
        try:
            query_embed = self.embeddings_index[check_meaning]
            scores = {}
            for word, embed in self.data_embeddings.items():
                category = self.categories[word]
                dist = query_embed.dot(embed)
                dist /= len(self.data[category])
                scores[category] = scores.get(category, 0) + dist

            highest_key = max(scores, key=scores.get)
            if category_to_check == "Places":
                if highest_key in ["Places", "Continents", "Regions"]:
                    return check_meaning.capitalize()
            if highest_key == category_to_check:
                return check_meaning.capitalize()
        except Exception as e:
            print(f"ERROR: {e}")
        return None

    def extract_species(self, text):
        """
        Extracts the species from the text
        :return: returns a list of species found in the query
        """
        species_list = []
        for token in self.nlp(text):
            match = self.process_match_scores(token.text.lower(), "Species")
            if match:
                species_list.append(match)
        return species_list

    def extract_country(self, text):
        """
        Extracts the countries from the text
        :return: returns a list of countries found in the query
        """
        country_list = []
        doc = self.nlp(text)
        for ent in doc.ents:
            if ent.label_ in ["GPE", "LOC"]:
                country_list.append(ent.text.capitalize())

        nationality = self.link_nationality_to_country(text)
        if nationality:
            country_list.append(nationality.capitalize())

        real_countries = []
        newtext = text
        for country in country_list:
            newtext = newtext.replace(country, "")
            c = country.lower()
            if " " not in c:
                match = self.process_match_scores(c, "Places")
                if match:
                    real_countries.append(match)
            else:
                real_countries.append(country)
        self.remove_stopwords(newtext)
        return real_countries

    def is_convertible_to_number(self, s):
        """
        Checks if the string can be converted into a number
        :return: boolean
        """
        try:
            float(s)
            return True
        except ValueError:
            return False

    def extract_years(self, text):
        """
        Extracts the country from the text
        :return: returns a list of countries found in the query
        """
        years = []
        for token in self.nlp(text):
            ranked = self.process_match_scores(token.text.lower(), "Years")
            if ranked or self.is_convertible_to_number(token.text):
                years.append(token.text)

        current = self.find_curr_year(text)
        if current and current not in years:
            years.append(current)

        washed = []
        for y in years:
            if y.isdigit() or (y[:-1].isdigit() and y.endswith("s")):
                washed.append(y)
        return washed

    def find_curr_year(self, text):
        """
        Checks if common keywords for the current year are in the text
        :return: Returns the current year in number format
        """
        keywords = ["this year", "latest", "current"]
        if any(k in text.lower() for k in keywords):
            return str(datetime.datetime.now().year)
        return ""

    def perform_ner(self, query):
        """
        Starts the near search and combines them into json output
        :return: Return the species, years, and countries into json/dict
        """
        countries = self.extract_country(query)
        species = self.extract_species(query)
        years = self.extract_years(query)
        return {"species": species, "years": years, "countries": countries}


class TailAdapter:
    """Handles NLP and embedding initialization and provides NER interface."""

    def __init__(self):
        self._initialized = False

    def initialize(self):
        # Download NLTK data
        nltk.download("stopwords", quiet=True)
        nltk.download("punkt_tab", quiet=True)
        if self._initialized:
            return
        print("🟡 Initializing TailAdapter...")

        # Load spaCy
        self.nlp = spacy.load("en_core_web_lg")

        # Define category data
        self.data = {
            "Names": ["john", "jay", "dan", "nathan", "bob"],
            "Continents": ["asia", "north america", "south america", "europe", "oceania", "antarctica", "africa"],
            "Places": ["tokyo", "beijing", "washington", "mumbai", "ethiopia", "canada", "sub-saharan africa", "madagascar"],
            "Species": ["cows", "chickens", "poultry", "bovine", "horses", "tigers", "puffins", "koalas", "lion", "hawks"],
            "Years": ["2001", "1971", "96", "2000s", "93'"],
            "General": ["the", "by", "here", "population", "random", "tile", "canda"],
            "Regions": ["central asia", "latin america", "oceania", "caribbean"],
            "Mistakes": ["rusia", "subsaharan", "saharan"],
        }

        self.categories = {word: k for k, v in self.data.items() for word in v}

        # Load embeddings
        # Dynamically locate the file in the 'requirements' folder (absolute-safe)
        base_dir = os.path.dirname(os.path.abspath(__file__))  # current file directory
        glove_path = os.path.join(base_dir, "..", "..", "requirements", "glove.6B.50d.txt")
        glove_path = os.path.normpath(glove_path)
        embeddings_index, words = {}, []
        with open(glove_path, encoding="utf-8") as f:
            for line in f:
                values = line.split()
                word = values[0]
                words.append(word)
                embeddings_index[word] = np.array(values[1:], dtype=np.float32)
        self.embeddings_index = embeddings_index
        self.data_embeddings = {k: v for k, v in embeddings_index.items() if k in self.categories}
        self.words = words

        # Load nationality mapping from CSV
        # Dynamically locate the file in the 'requirements' folder (absolute-safe)
        base_dir = os.path.dirname(os.path.abspath(__file__))  # current file directory
        nationality_path = os.path.join(base_dir, "..", "..", "requirements", "nationality.csv")
        nationality_path = os.path.normpath(nationality_path)
        nationality_mapping = {}
        with open(nationality_path, newline="", encoding="utf-8") as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                nationality_mapping[row["nationality"].lower()] = row["en_short_name"]
        self.nationality_mapping = nationality_mapping

        self.V = set(words)
        self.ner = NER(self.nlp, self.data, self.categories, self.embeddings_index, self.data_embeddings, self.nationality_mapping)
        self._initialized = True
        print("✅ TailAdapter initialized successfully.")

    def log_message(self, message: str):
        """
        Log messages
        :return: Nothing
        """
        toronto_timezone = pytz.timezone("America/Toronto")
        toronto_time = datetime.datetime.now(toronto_timezone)
        formatted_time = toronto_time.strftime("%d-%m-%Y %H:%M")
        logging.info(formatted_time + " - " + message)

    def perform_ner(self, query: str):
        """Expose NER functionality directly through TailAdapter."""
        return self.ner.perform_ner(query)


# Singleton instance
TailAdapterInstance = TailAdapter()
