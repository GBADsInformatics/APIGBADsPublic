import atexit
from neo4j import GraphDatabase
from app.utils.helpers import (
    get_datasets_country_species,
    get_datasets_query,
    get_countries_query,
    get_species_query,
    get_metadata_table,
    get_all_metadata,
)


class Metadata:
    """Handles Neo4j database operations for dataset metadata."""

    def __init__(self, uri, user, password):
        """
        Initialize the Neo4j driver.

        :param uri: Neo4j database URI
        :param user: Username for authentication
        :param password: Password for authentication
        """
        self.driver = GraphDatabase.driver(uri, auth=(user, password))

    def close(self):
        """Close the Neo4j driver connection."""
        if self.driver:
            self.driver.close()

    # -------------------------------------------------------------------------
    # COUNTRIES
    # -------------------------------------------------------------------------
    def get_countries(self):
        """Retrieve all available countries."""
        with self.driver.session() as session:
            return session.execute_read(self._return_countries)

    @staticmethod
    def _return_countries(tx):
        """Retrieve all available countries."""
        result = tx.run(get_countries_query())
        countries = [record["country"] for record in result]
        return {"countries": countries}

    # -------------------------------------------------------------------------
    # SPECIES
    # -------------------------------------------------------------------------
    def get_species(self):
        """Retrieve all species."""
        with self.driver.session() as session:
            return session.execute_read(self._return_species)

    @staticmethod
    def _return_species(tx):
        result = tx.run(get_species_query())
        species = [record["species"] for record in result]
        return {"species": species}

    # -------------------------------------------------------------------------
    # DATASETS
    # -------------------------------------------------------------------------
    def get_datasets(self, countries=None, species=None):
        """
        Retrieve datasets based on provided countries and species.
        If none provided, returns all datasets.
        """
        with self.driver.session() as session:
            return session.execute_read(self._return_datasets, countries, species)

    @staticmethod
    def _return_datasets(tx, countries, species):
        """Retrieve all available datasets."""
        result = tx.run(get_datasets_query(), countries=countries, species=species)
        return [record.data() for record in result]

    # -------------------------------------------------------------------------
    # METADATA (TABLE + ALL)
    # -------------------------------------------------------------------------
    def get_metadata_table(self, table_name):
        """Retrieve metadata for a specific table."""
        with self.driver.session() as session:
            return session.execute_read(self._return_metadata_table, table_name)

    @staticmethod
    def _return_metadata_table(tx, table_name):
        """Retrieve all available metadatatables."""
        result = tx.run(get_metadata_table(), table_name=table_name)
        return [record.data() for record in result]

    def get_all_metadata(self):
        """Retrieve metadata for all datasets."""
        with self.driver.session() as session:
            return session.execute_read(self._return_all_metadata)

    @staticmethod
    def _return_all_metadata(tx):
        """Retrieve all available metadata."""
        result = tx.run(get_all_metadata())
        return [record.data() for record in result]

    # -------------------------------------------------------------------------
    # COUNTRY + SPECIES FILTERED NAMES
    # -------------------------------------------------------------------------
    def get_names_country_species(self, countries, species):
        """Retrieve dataset names for specific countries and species."""
        with self.driver.session() as session:
            return session.execute_read(self._return_names_country_species, countries, species)

    @staticmethod
    def _return_names_country_species(tx, countries, species):
        """Retrieve all available names country and species."""
        result = tx.run(get_datasets_country_species(), countries=countries, species=species)
        return [record.data() for record in result]


# =============================================================================
# ADAPTER SINGLETON
# =============================================================================
class MetadataAdapter:
    """Singleton wrapper providing easy access to metadata operations."""

    _instance = None

    def __init__(self, uri: str, user: str, password: str):
        """Initialize the Metadata adapter wrapper."""
        self.driver = Metadata(uri, user, password)

    def close(self):
        """Close the underlying Neo4j driver."""
        self.driver.close()

    @classmethod
    def get_instance(cls, uri: str = None, user: str = None, password: str = None):
        """
        Get the singleton MetadataAdapter instance.

        :param uri: Neo4j URI (required only on first call)
        :param user: Username (required only on first call)
        :param password: Password (required only on first call)
        :return: MetadataAdapter instance
        """
        if cls._instance is None:
            if not all([uri, user, password]):
                raise ValueError("Must provide URI, user, password for first initialization")
            cls._instance = MetadataAdapter(uri, user, password)
            atexit.register(cls._instance.close)
        return cls._instance

    def initialize(self):
        """No-op for compatibility with DI frameworks."""
        pass

    # -------------------------------------------------------------------------
    # PROXY METHODS
    # -------------------------------------------------------------------------
    def get_countries(self):
        """Retrieve all available countries."""
        return self.driver.get_countries()

    def get_species(self):
        """Retrieve all available species."""
        return self.driver.get_species()

    def get_datasets(self, countries=None, species=None):
        """Retrieve all available datasets."""
        return self.driver.get_datasets(countries, species)

    def get_metadata_table(self, table_name):
        """Retrieve all available metadata from the table."""
        return self.driver.get_metadata_table(table_name)

    def get_all_metadata(self):
        """Retrieve all available metadata."""
        return self.driver.get_all_metadata()

    def get_names_country_species(self, countries, species):
        """Retrieve all available country and species."""
        return self.driver.get_names_country_species(countries, species)
