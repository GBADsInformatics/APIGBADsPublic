from fastapi import APIRouter, Depends
from app.utils.dependencies import get_metadata_adapter

router = APIRouter()

@router.get("/get_datasets")
def get_datasets(metadata=Depends(get_metadata_adapter)):
    """
    Retrieve a list of all datasets available in the metadata repository.

    Args:
        metadata: The metadata adapter instance provided by dependency injection.

    Returns:
        List of dataset names or identifiers.
    """
    return metadata.get_datasets()


@router.get("/get_species")
def get_species(metadata=Depends(get_metadata_adapter)):
    """
    Retrieve a list of all species available in the metadata repository.

    Args:
        metadata: The metadata adapter instance provided by dependency injection.

    Returns:
        List of species names.
    """
    return metadata.get_species()


@router.get("/get_metadata")
def get_metadata(dataset_name: str, metadata=Depends(get_metadata_adapter)):
    """
    Retrieve detailed metadata for a specific dataset.

    Args:
        dataset_name (str): The name of the dataset to retrieve metadata for.
        metadata: The metadata adapter instance provided by dependency injection.

    Returns:
        Dict containing dataset metadata including:
            - dataset: General dataset metadata
            - distribution: Dataset distribution information
            - publisher: Dataset publisher details
            - license: Dataset license information
            - provider: Dataset provider details
            - contactPoint: Contact information for the dataset
    """
    return {
        "dataset": metadata.get_dataset_metadata(dataset_name),
        "distribution": metadata.get_dataset_distribution(dataset_name),
        "publisher": metadata.get_dataset_publisher(dataset_name),
        "license": metadata.get_dataset_license(dataset_name),
        "provider": metadata.get_dataset_provider(dataset_name),
        "contactPoint": metadata.get_dataset_contact_point(dataset_name)
    }


@router.get("/search_species")
def search_species(species: str, metadata=Depends(get_metadata_adapter)):
    """
    Search for datasets containing a specific species.

    Args:
        species (str): The species name to search for.
        metadata: The metadata adapter instance provided by dependency injection.

    Returns:
        List of datasets that include the specified species.
    """
    return metadata.get_species_datasets(species)


@router.get("/search_country")
def search_country(country: str, metadata=Depends(get_metadata_adapter)):
    """
    Search for datasets related to a specific country.

    Args:
        country (str): The country name to search for.
        metadata: The metadata adapter instance provided by dependency injection.

    Returns:
        List of datasets associated with the specified country.
    """
    return metadata.get_country_datasets(country)
