import os
from pathlib import Path
from typing import Optional
from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import HTMLResponse
from app.adapters.rds_adapter import RDSAdapter
from app.utils.dependencies import get_rds_adapter
from app.utils.helpers import format_table


router = APIRouter()


@router.get("/dataportal/")
async def get_dataportal():
    """
    Serve the dataportal HTML page for some additional documentation.\n
    :return: HTMLResponse containing the dataportal page content.
    """
    dataportal_html = Path('app/public/dataportal.html').read_text(encoding="utf-8")
    return HTMLResponse(content=dataportal_html, status_code=200)


@router.get("/GBADsTables/public")
async def list_all_public_tables(
    format: str = "text",
    rds_adapter: RDSAdapter = Depends(get_rds_adapter(
        db_host=os.getenv("RDS_HOST"),
        db_name=os.getenv("RDS_NAME"),
        db_user=os.getenv("RDS_USER"),
        db_password= os.getenv("RDS_PASS")
    ))
):
    """
    List all tables in the GBADs public database.\n
    It is used by the dataportal to generate the list of tables that are available for the user to query.\n
    :param format: The format of the response. Can be 'text', 'csv', 'file', or 'html'.\n
    :return: A formatted table of all public tables in the GBADs database.
    """
    tables = rds_adapter.list_tables()
    if not tables:
        raise HTTPException(status_code=404, detail="No tables found")
    table_names = [table[0] for table in tables]
    return format_table(table_names, format=format, dimensions=1, html_title="GBADs Public Database Tables")


@router.get("/GBADsTable/public")
async def list_table_fields(
    table_name: str,
    format: str = "text",
    rds_adapter: RDSAdapter = Depends(get_rds_adapter(
        db_host=os.getenv("RDS_HOST"),
        db_name=os.getenv("RDS_NAME"),
        db_user=os.getenv("RDS_USER"),
        db_password= os.getenv("RDS_PASS")
    ))
):
    """
    List fields of a specific table in the GBADs public database.\n
    :param table_name: The name of the table to list fields for.\n
    :param format: The format of the response. Can be 'text', 'csv', 'file', or 'html'.\n
    :return: A formatted table of fields in the specified table.
    """
    fields = rds_adapter.list_table_fields(table_name)
    if not fields:
        raise HTTPException(status_code=404, detail="No fields found")
    if format in ["text", "csv"]:
        fields = [field[0] for field in fields]
        return format_table(fields, format=format, dimensions=1)
    return format_table(fields, format=format, column_names=["name", "type"], html_title=f"Data fields: {table_name}")


@router.get("/GBADsPublicQuery/{table_name}")
async def public_query(
    table_name: str,
    fields: str,
    query: str,
    join: str = "",
    order: str = "",
    format: str = "text",
    count: str = "no",
    pivot: str = "",
    rds_adapter: RDSAdapter = Depends(get_rds_adapter(
        db_host=os.getenv("RDS_HOST"),
        db_name=os.getenv("RDS_NAME"),
        db_user=os.getenv("RDS_USER"),
        db_password= os.getenv("RDS_PASS")
    ))
):
    """
    Perform a query on the GBADs public database.\n
    :param table_name: The name of the table to query.\n
    :param fields: The fields to select in the query. Use '*' for all fields.\n
    :param query: The WHERE clause of the query.\n
    :param join: Optional join clause in the format 'table1,table2,field1,field2'.\n
    :param order: Optional ORDER BY clause.\n
    :param format: The format of the response. Can be 'text', 'csv', 'file', or 'html'.\n
    :param count: Whether to count the results. Default is 'no'.\n
    :param pivot: Not implemented yet.\n
    :return: A formatted table of the query results.
    """
    # Formatting Fields
    if fields == "*" and not join:
        table_fields = rds_adapter.list_table_fields(table_name)
        allowed_fields = [field[0] for field in table_fields]
        fields = ",".join(allowed_fields)

    # Formatting Join
    if join:
        try:
            t1, t2, f1, f2 = map(str.strip, join.split(","))
        except ValueError as exc:
            raise HTTPException(status_code=400,
                                detail="Join must contain exactly 4 items: table1,table2,field1,field2") from exc
        join = rds_adapter.build_from_join_clause(t1, t2, f1, f2)

    # Selecting Data
    try:
        data, column_names, executed_query = rds_adapter.select(
            table_name=table_name,
            fields=fields,
            where=query,
            join=join,
            order_by=order,
            count=(count.lower() != "no"),
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if not data:
        raise HTTPException(status_code=404, detail="No data found for the query")

    # Returning table
    return format_table(
        data,
        column_names=column_names,
        format=format,
        html_title=f"GBADs Public Database Query: {table_name}",
        html_subtitle=executed_query,
        download_filename=table_name,
    )

@router.get("/GBADsLivestockPopulation/{data_source}")
async def get_population(
    data_source: str,
    format: str = "text",
    year: Optional[str] = "*",
    iso3: Optional[str] = "*",
    country: Optional[str] = "*",
    species: Optional[str] = "*",
    rds_adapter: RDSAdapter = Depends(get_rds_adapter(
        db_host=os.getenv("RDS_HOST"),
        db_name=os.getenv("RDS_NAME"),
        db_user=os.getenv("RDS_USER"),
        db_password=os.getenv("RDS_PASS")
    ))
):
    """
    Get livestock population data from the GBADs public database.\n
    :param data_source: The data source to query. Can be 'oie' or 'faostat'.\n
    :param format: The format of the response. Can be 'text', 'csv', 'file', or 'html'.\n
    :param year: The year to filter by. Use '*' for all years.\n
    :param iso3: The ISO3 code to filter by. Use '*' for all countries. (only for faostat)\n
    :param country: The country name to filter by. Use '*' for all countries.\n
    :param species: The species to filter by. Use '*' for all species.\n
    :return: A formatted table of livestock population data.
    """
    # Validate data_source
    allowed_sources = {"oie", "faostat"}
    if data_source not in allowed_sources:
        raise HTTPException(status_code=400, detail="Invalid data source. Allowed sources are: oie, faostat")

    if data_source == "oie":
        table_name = "livestock_national_population_oie"
        fields = "country,year,species,population,metadataflags"
    elif data_source == "faostat":
        table_name = "livestock_countries_population_faostat"
        fields = "iso3,country,year,species,population"
    else:
        raise HTTPException(status_code=400, detail="Unsupported data source")

    filters = []
    if year != "*":
        filters.append(f"year={year}")

    if country != "*":
        filters.append(f"country='{country}'")

    if iso3 != "*" and data_source == "faostat":
        filters.append(f"iso3='{iso3}'")

    aggregate_queries = {
        "oie": {
            "Poultry": ["Birds", "Layers", "Broilers", "Turkeys", "Other commercial poultry", "Backyard poultry"],
            "All Cattle": ["Cattle", "Male and female cattle", "Adult beef cattle", "Adult dairy cattle", "Calves"],
            "All Swine": ["Swine", "Adult pigs", "Backyard pigs", "Commercial pigs", "Fattening pigs", "Piglets"],
            "All Sheep": ["Sheep", "Adult sheep", "Lambs"],
            "All Goats": ["Goats", "Adult goats", "Kids"],
            "All Equids": ["Equidae", "Domestic Horses", "Donkeys/ Mules/ Hinnies"]
        },
        "faostat": {
            "Poultry": ["Chickens", "Turkeys", "Ducks", "Geese and guinea fowls"],
        }
    }

    if species != "*":
        if species in aggregate_queries[data_source]:
            filters.append(f"(species IN ({', '.join(map(repr, aggregate_queries[data_source][species]))}))")
        else:
            filters.append(f"species='{species}'")

    where = " AND ".join(filters)

    # Query the database
    try:
        data, column_names, executed_query = rds_adapter.select(
            table_name=table_name,
            fields=fields,
            where=where,
            join="",
            order_by="",
            count=False,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if not data:
        raise HTTPException(status_code=404, detail="No data found for the query")

    return format_table(
        data,
        column_names=column_names,
        format=format,
        html_title=f"GBADs Public Database Query: {table_name}",
        html_subtitle=executed_query,
        download_filename=table_name,
    )
