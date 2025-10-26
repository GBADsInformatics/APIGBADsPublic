import os
from neo4j import GraphDatabase
import atexit


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
        self.driver.close()

    def get_datasets(self):
        """
        Retrieve all dataset names.

        :return: A dictionary containing dataset names.
        """
        with self.driver.session() as session:
            result = session.execute_read(self.return_datasets)
            return result

    def return_datasets(self, tx):
        """
        Transaction function for retrieving datasets.

        :param tx: Neo4j transaction object
        :return: A dictionary containing dataset names.
        """
        dataset = []
        query = (
            "MATCH (n:dataset) "
            "RETURN n.name AS name"
        )
        result = tx.run(query)
        for line in result:
            dataset.append(line["name"])
        return {"name": dataset}

    def get_species(self):
        """
        Retrieve all species (categories).

        :return: A dictionary containing species names.
        """
        with self.driver.session() as session:
            result = session.execute_read(self.return_species)
            return result

    def return_species(self, tx):
        """
        Transaction function for retrieving species categories.

        :param tx: Neo4j transaction object
        :return: A dictionary containing species names.
        """
        species = []
        query = (
            "MATCH (n:Category) "
            "RETURN n.name AS name"
        )
        result = tx.run(query)
        for line in result:
            species.append(line["name"])
        return {"name": species}

    def get_species_datasets(self, category):
        """
        Retrieve datasets related to a given species/category.

        :param category: Species name or partial string
        :return: A dictionary containing dataset metadata entries.
        """
        with self.driver.session() as session:
            datasets = session.execute_read(self.return_species_datasets, category)
        return datasets

    def return_species_datasets(self, tx, category):
        """
        Transaction function for retrieving species datasets.

        :param tx: Neo4j transaction object
        :param category: Species name or partial string
        :return: A dictionary of dataset metadata objects.
        """
        query = (
            "MATCH (n:Category)-[]-()-[]-(d:dataset) "
            "WHERE toLower(n.name) CONTAINS toLower($category) "
            "RETURN DISTINCT(d) AS data"
        )
        result = tx.run(query, category=category)
        return {"dataset": [self.serialize_metadata(line) for line in result]}

    def get_dataset_metadata(self, name):
        """
        Retrieve detailed metadata for a dataset.

        :param name: Dataset name
        :return: A dictionary of dataset metadata fields.
        """
        with self.driver.session() as session:
            metadata = session.execute_read(self.return_dataset_metadata, name)
        return metadata

    def return_dataset_metadata(self, tx, name):
        """
        Transaction function for dataset metadata retrieval.

        :param tx: Neo4j transaction object
        :param name: Dataset name
        :return: A dictionary containing metadata details.
        """
        query = (
            "MATCH (n:dataset {name: $name}) "
            "RETURN n AS data"
        )
        result = tx.run(query, name=name)
        for record in result:
            return self.serialize_metadata(record)

    def get_dataset_distribution(self, name):
        """
        Retrieve distribution information for a dataset.

        :param name: Dataset name
        :return: A dictionary with distribution fields.
        """
        with self.driver.session() as session:
            distribution = session.execute_read(self.return_dataset_distribution, name)
        return distribution

    def return_dataset_distribution(self, tx, name):
        """
        Transaction function for retrieving dataset distribution.

        :param tx: Neo4j transaction object
        :param name: Dataset name
        :return: A dictionary of distribution details.
        """
        query = (
            "MATCH (n:dataset {name: $name})-[]-(d:distribution) "
            "RETURN d AS distribution"
        )
        result = tx.run(query, name=name)
        for record in result:
            return {
                "name": record["distribution"]["name"],
                "identifier": record["distribution"]["identifier"],
                "description": record["distribution"]["description"],
                "fileFormat": record["distribution"]["fileFormat"],
                "contentSize": record["distribution"]["contentSize"],
            }

    def get_dataset_publisher(self, name):
        """
        Retrieve publisher information for a dataset.

        :param name: Dataset name
        :return: A dictionary with publisher details.
        """
        with self.driver.session() as session:
            publisher = session.execute_read(self.return_dataset_publisher, name)
        return publisher

    def return_dataset_publisher(self, tx, name):
        """Transaction function for retrieving publisher data."""
        query = (
            "MATCH (n:dataset {name: $name})-[]-(p:publisher) "
            "RETURN p AS publisher"
        )
        result = tx.run(query, name=name)
        for record in result:
            return {"name": record["publisher"]["name"]}

    def get_dataset_contact_point(self, name):
        """Retrieve contact point details."""
        with self.driver.session() as session:
            contact_point = session.execute_read(self.return_dataset_contact_point, name)
        return contact_point

    def return_dataset_contact_point(self, tx, name):
        """Transaction function for retrieving dataset contact point."""
        query = (
            "MATCH (n:dataset {name: $name})-[]-(cp:contactPoint) "
            "RETURN cp AS contactPoint"
        )
        result = tx.run(query, name=name)
        for record in result:
            return {"name": record["contactPoint"]["name"]}

    def get_dataset_provider(self, name):
        """Retrieve provider information for a dataset."""
        with self.driver.session() as session:
            provider = session.execute_read(self.return_dataset_provider, name)
        return provider

    def return_dataset_provider(self, tx, name):
        """Transaction function for retrieving dataset provider."""
        query = (
            "MATCH (n:dataset {name: $name})-[]-(p:provider) "
            "RETURN p AS provider"
        )
        result = tx.run(query, name=name)
        for record in result:
            return {"name": record["provider"]["name"]}

    def get_dataset_license(self, name):
        """Retrieve license info for a dataset."""
        with self.driver.session() as session:
            license_data = session.execute_read(self.return_dataset_license, name)
        return license_data

    def return_dataset_license(self, tx, name):
        """Transaction function for retrieving dataset license."""
        query = (
            "MATCH (n:dataset {name: $name})-[]-(l:license) "
            "RETURN l AS license"
        )
        result = tx.run(query, name=name)
        for record in result:
            return {"name": record["license"]["name"], "url": record["license"]["url"]}

    def get_country_datasets(self, country):
        """
        Retrieve datasets associated with a given country.

        :param country: Country name or partial string
        :return: A dictionary of dataset metadata entries.
        """
        with self.driver.session() as session:
            metadata = session.execute_read(self.return_country_dataset, country)
            return metadata

    def serialize_metadata(self, record):
        """
        Convert Neo4j dataset metadata records to a dictionary.

        :param record: Neo4j result record
        :return: Dictionary representation of dataset metadata.
        """
        return {
            "name": record["data"]["name"],
            "datePublished": record["data"]["datePublished"],
            "datasetTimeInterval": record["data"]["datasetTimeInterval"],
            "citation": record["data"]["citation"],
            "description": record["data"]["description"],
            "id": record["data"]["id"],
        }

    def return_country_dataset(self, tx, country):
        """
        Transaction function for retrieving country-specific datasets.

        :param tx: Neo4j transaction object
        :param country: Country name or partial string
        :return: A dictionary of dataset metadata entries.
        """
        query = (
            "MATCH (n:Area)-[]-()-[]-()-[]-(d:dataset) "
            "WHERE toLower(n.name) CONTAINS toLower($name) "
            "RETURN d AS data"
        )
        try:
            result = tx.run(query, name=country)
            return {"dataset": [self.serialize_metadata(line) for line in result]}
        except Exception:
            return "Provide a valid country."


class MetadataAdapter:
    """Singleton wrapper providing easy access to metadata operations."""

    _instance = None

    def __init__(self, uri: str, user: str, password: str):
        """
        Initialize the Metadata adapter wrapper.

        :param uri: Neo4j database URI
        :param user: Username for authentication
        :param password: Password for authentication
        """
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

    def get_datasets(self):
        """Proxy to Metadata.get_datasets()."""
        return self.driver.get_datasets()

    def get_species(self):
        """Proxy to Metadata.get_species()."""
        return self.driver.get_species()

    def get_species_datasets(self, species: str):
        """Proxy to Metadata.get_species_datasets()."""
        return self.driver.get_species_datasets(species)

    def get_country_datasets(self, country: str):
        """Proxy to Metadata.get_country_datasets()."""
        return self.driver.get_country_datasets(country)

    def get_dataset_metadata(self, name: str):
        """Proxy to Metadata.get_dataset_metadata()."""
        return self.driver.get_dataset_metadata(name)

    def get_dataset_distribution(self, name: str):
        """Proxy to Metadata.get_dataset_distribution()."""
        return self.driver.get_dataset_distribution(name)

    def get_dataset_publisher(self, name: str):
        """Proxy to Metadata.get_dataset_publisher()."""
        return self.driver.get_dataset_publisher(name)

    def get_dataset_contact_point(self, name: str):
        """Proxy to Metadata.get_dataset_contact_point()."""
        return self.driver.get_dataset_contact_point(name)

    def get_dataset_provider(self, name: str):
        """Proxy to Metadata.get_dataset_provider()."""
        return self.driver.get_dataset_provider(name)

    def get_dataset_license(self, name: str):
        """Proxy to Metadata.get_dataset_license()."""
        return self.driver.get_dataset_license(name)


MetadataAdapterInstance = MetadataAdapter(
    uri=os.getenv("GRAPHDB_URI"),
    user=os.getenv("GRAPHDB_USERNAME"),
    password=os.getenv("GRAPHDB_PASSWORD"),
)

atexit.register(MetadataAdapterInstance.close)
