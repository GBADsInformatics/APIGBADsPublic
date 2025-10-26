# app/api/v1/metadata_endpoints.py
from fastapi import APIRouter, Depends
from app.utils.dependencies import get_metadata_adapter

router = APIRouter()

@router.get("/get_datasets")
def get_datasets(metadata=Depends(get_metadata_adapter)):
    return metadata.get_datasets()

@router.get("/get_species")
def get_species(metadata=Depends(get_metadata_adapter)):
    return metadata.get_species()

@router.get("/get_metadata")
def get_metadata(dataset_name: str, metadata=Depends(get_metadata_adapter)):
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
    return metadata.get_species_datasets(species)

@router.get("/search_country")
def search_country(country: str, metadata=Depends(get_metadata_adapter)):
    return metadata.get_country_datasets(country)
