from fastapi import APIRouter, Depends, BackgroundTasks
from fastapi.responses import HTMLResponse, FileResponse
from pathlib import Path
from datetime import date
import json
import os
from app.utils.dependencies import get_metadata_adapter

router = APIRouter()


def remove_file(path: str):
    os.unlink(path)

@router.get("/countries")
def countries(metadata=Depends(get_metadata_adapter)):
    """
    Retrieve a list of all countries available in the metadata repository.

    Args:
        metadata: The metadata adapter instance provided by dependency injection.

    Returns:
        Dict containing a list of countries.
    """
    return metadata.get_countries()


@router.get("/species")
def species(metadata=Depends(get_metadata_adapter)):
    """
    Retrieve a list of all species available in the metadata repository.

    Args:
        metadata: The metadata adapter instance provided by dependency injection.

    Returns:
        Dict containing a list of species.
    """
    return metadata.get_species()


@router.get("/datasets")
def datasets(
    countries: str = "*",
    species: str = "*",
    metadata=Depends(get_metadata_adapter),
):
    """
    Retrieve datasets filtered by countries and species.
    Use '*' to return all datasets.

    Args:
        countries (str): Comma-separated list of countries or '*' for all.
        species (str): Comma-separated list of species or '*' for all.
        metadata: The metadata adapter instance provided by dependency injection.

    Returns:
        List of dataset metadata entries.
    """
    if countries == "*" and species == "*":
        return metadata.get_all_metadata()

    try:
        countries_list = countries.split(",")
        species_list = species.split(",")
        return metadata.get_datasets(countries_list, species_list)
    except Exception:
        return {"error": "Please provide valid countries and species."}


@router.get("/tbl_metadata")
def metadata_tbl_name(
    table_name: str,
    format: str = "json",
    background_tasks: BackgroundTasks = None,
    metadata=Depends(get_metadata_adapter),
):
    """
    Retrieve metadata for a specific dataset table, either as JSON or a downloadable file.

    Args:
        table_name (str): The name of the dataset table.
        format (str): 'json' for direct output or 'file' for downloadable JSON file.
        background_tasks (BackgroundTasks, optional): Background task manager to remove temporary files.
        metadata: The metadata adapter instance provided by dependency injection.

    Returns:
        JSONResponse or FileResponse containing the metadata.
    """
    data = metadata.get_metadata_table(table_name)

    if format == "file":
        today = date.today()
        date_str = today.strftime("%Y%m%d")
        file_name = f"{date_str}_{table_name}.json"
        with open(file_name, "w") as f:
            json.dump(data, f, indent=4)
        background_tasks.add_task(remove_file, file_name)
        return FileResponse(file_name, filename=file_name)

    elif format == "json":
        return data

    else:
        return {"error": "Invalid format type, please provide 'file' or 'json'."}
