from fastapi import FastAPI, Response, BackgroundTasks
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.responses import PlainTextResponse
from typing import Optional
from pathlib import Path
import uvicorn
import secure_rds as secure
import rds_functions as rds
import pandas as pd
import os
import logging

app = FastAPI()

#Function to removed the created CSV/HTML file
def remove_file(path):
    try:
        os.unlink(path)
        logging.info("Successfully removed file")
    except Exception as e:
        logging.error("Failed to delete %s." % path)

#Telling the logger where to log the information
logging.basicConfig(filename="logs/logs.txt", level=logging.DEBUG, format="%(asctime)s %(message)s")
logging.basicConfig(filename="logs/errors.txt", level=logging.ERROR, format="%(asctime)s %(message)s")


@app.get("/dataportal/")
def home():
    logging.info("Home page accessed")
    html_string = Path('dataPortalDocumentation.html').read_text()
#    return {"GBADsKE Data Portal Status": "Up"}
    return HTMLResponse(html_string)

@app.get("/GBADsTables/{public}")
async def get_public_tables( public: str, format: Optional[str] = "html"):
    logging.info("GBADsTables/{public} called")

    try:
        conn = secure.connect_public()
        cur = conn.cursor()
        logging.info("Connected to GBAD database")
    except:
        logging.error("Error connecting to GBAD database")
        return "Error connecting to GBAD database"

    logging.info("Fetching tables")
    tables = rds.displayTables(cur)
    num = len(tables)
    htmlstring = "<html><body><H2>GBADs Public Database Tables</h2><ul>"
    retstring = ""
    ct = 0

    logging.info("Formatting tables into HTML and the return string")
    for table in tables:
        ct = ct + 1
        if ct < num:
            htmlstring = htmlstring+"<li> "+table[1]
            if ct == 1:
                retstring = table[1]
            else:
                retstring = retstring+","+table[1]
        else:
            htmlstring = htmlstring+"<li> "+table[1]+"</ul></body></html>"
            retstring = retstring+","+table[1]

    if format == "text":
        logging.info("Returning tables as text")
        return PlainTextResponse(retstring)
    else:
        logging.info("Returning tables as HTML")
        return HTMLResponse(htmlstring)

@app.get("/GBADsTable/{public}")
async def get_public_table_fields( public: str, table_name: str, format: Optional[str] = "html" ):
    logging.info("GBADsPublicQuery called")

    try:
        conn = secure.connect_public()
        cur = conn.cursor()
        logging.info("Connected to GBAD database")
    except:
        logging.error("Error connecting to GBAD database")
        return "Error connecting to GBAD database"

    logging.info("Fetching fields")
    fields = rds.displayTabInfo ( cur, table_name )
    num = len(fields)
    htmlstring = "<html><body><H2>Data Fields for "+str(table_name)+"</h2><ul>"
    retstring = ""
    ct = 0

    logging.info("Formatting fields into HTML and the return string")
    for field in fields:
        ct = ct + 1
        if ct < num:
            htmlstring = htmlstring+"<li> "+field[0]+" ("+field[1]+")"
            retstring = retstring+field[0]+","
        else:
            htmlstring = htmlstring+"<li> "+field[0]+" ("+field[1]+") </ul></body></html>"
            retstring = retstring+field[0]

    if format == "html":
        logging.info("Returning fields as HTML")
        return HTMLResponse(htmlstring)
    else:
        logging.info("Returning fields as text")
        return PlainTextResponse(retstring)

@app.get("/GBADsPublicQuery/{table_name}")
async def get_db_query( table_name: str, fields: str, query: str, join: Optional[str] = "", order: Optional[str] = "", format: Optional[str] = "html", count: Optional[str] = "no", pivot: Optional[str] = "",  background_tasks: BackgroundTasks = None  ):
    logging.info("GBADsPublicQuery called")

    try:
        conn = secure.connect_public()
        cur = conn.cursor()
        logging.info("Connected to GBAD database")
    except:
        logging.error("Error connecting to GBAD database")
        return "Error connecting to GBAD database"

    logging.info("Formatting the query")
    columns = fields.split(",")
    joinitems = []
    if join != "":
        joinitems = join.split(",")
        table_name1 = joinitems[0]
        table_name2 = joinitems[1]
        jfield_1 = joinitems[2]
        jfield_2 = joinitems[3]
        joinstring = rds.setJoin ( table_name1, table_name2, jfield_1, jfield_2 )
    else:
        joinstring = ""

    logging.info("Setting and running the query on the database")
    if count == "no":
        querystr = rds.setQuery ( table_name, fields, query, joinstring )
    else:
        querystr = rds.setCountQuery ( table_name, fields, query, joinstring )
    if order != "":
        querystr = querystr+" ORDER BY "+str(order)
#debugging
    print ( query )
#debugging
    retQ = rds.execute ( cur, querystr )

    logging.info("Formatting the results into a file and reutrn string")
    htmlstring = "<head> <style> table { font-family: arial, sans-serif; border-collapse: collapse; width: 80%; }"
    htmlstring = htmlstring+" td, th { border: 1px solid #dddddd; text-align: left; padding: 8px; }"
    htmlstring = htmlstring+" tr:nth-child(even) { background-color: #dddddd; } </style> </head>"
    htmlstring = htmlstring+"<html><body><H2>GBADs Public Database Query </h2>"
    htmlstring = htmlstring+"<i>"+str(querystr)+"</i><br><br>"
    htmlstring = htmlstring+"<table><tr>"
    for col in columns:
        htmlstring = htmlstring+"<td><b>"+col+"</b></td>"
    htmlstring = htmlstring+"</tr>"
    file_name = table_name+".csv"
    f = open(file_name, "w")
    print ( fields, file=f  )
    for field in retQ:
        x = 0
        htmlstring = htmlstring+"<tr>"
        while x < len(field)-1:
            print ( "\""+str(field[x])+"\"", end=",", file=f  )
            fstring = str(field[x])
            htmlstring = htmlstring+"<td>"+fstring.rstrip()+"</td>"
            x = x + 1
        fstring = str(field[x])
        htmlstring = htmlstring+"<td>"+fstring.rstrip()+"</td></tr>"
        print ( "\""+str(field[x])+"\"", file=f  )
    htmlstring = htmlstring+"</table></body></html>"
    f.close()

    if format == "html":
        logging.info("Returning results as HTML")
        remove_file(file_name)
        return HTMLResponse(htmlstring)
    else:
        logging.info("Returning results as CSV")
        background_tasks.add_task(remove_file, file_name)
        return FileResponse(file_name,filename=file_name)

@app.get("/GBADsLivestockPopulation/{data_source}")
async def get_population ( data_source: str, format: str, year: Optional[str] = "*", iso3: Optional[str] = "*", country: Optional[str] = "*", species: Optional[str] = "*", background_tasks: BackgroundTasks = None ):
    logging.info("GBADsLivestockPopulation called")

    try:
        conn = secure.connect_public()
        cur = conn.cursor()
        logging.info("Connected to GBAD database")
    except:
        logging.error("Error connecting to GBAD database")
        return "Error connecting to GBAD database"

    logging.info("Formatting query")
    joinstring = ""
    if data_source == "oie":
        table_name = "livestock_national_population_"+data_source
        fields = "country,year,species,population,metadataflags"
    else:
        table_name = "livestock_countries_population_"+data_source
        fields = "iso3,country,year,species,population"
    columns = fields.split(",")
    query1 = ""
    query2 = ""
    query3 = ""
    if year != "*":
        query1 = "year="+year
    if country != "*":
        if data_source == "faostat":
            query2 = "country='"+country+"'"
        elif data_source == "oie":
            query2 = "country='"+country+"'"
    if iso3 != "*":
        if data_source == "faostat":
            query2 = "iso3='"+iso3+"'"
    if species != "*":
        if data_source == "oie":
            if species == "Poultry":
                query3 = "(species='Birds' OR species='Layers' OR species='Broilers' OR species='Turkeys' OR species='Other commercial poultry' OR species='Backyard poultry')"
            elif species == "All Cattle":
                query3 = "(species='Cattle' OR species='Male and female cattle' OR species='Adult beef cattle' OR species='Adult dairy cattle' OR species='Calves')"
            elif species == "All Swine":
                query3 = "(species='Swine' OR species='Adult pigs' OR species='Backyard pigs' OR species='Commercial pigs' OR species='Fattening pigs' OR species='Piglets')"
            elif species == "All Sheep":
                query3 = "(species='Sheep' OR species='Adult sheep' OR species='Lambs')"
            elif species == "All Goats":
                query3 = "(species='Goats' OR species='Adult goats' OR species='Kids')"
            elif species == "All Equids":
                query3 = "(species='Equidae' OR species='Domestic Horses' OR species='Donkeys/ Mules/ Hinnies')"
            else:
                query3 = "species='"+species+"'"
        else:
            if species == "Poultry":
                query3 = "(species='Chickens' OR species='Turkeys' OR species='Ducks' OR species='Geese and guinea fowls')"
            else:
                query3 = "species='"+species+"'"
    query = ""
    if query1 != "":
        query = query1
    if query2 != "":
        if query == "":
            query = query2
        else:
            query = query+" AND "+query2
    if query3 != "":
        if query == "":
            query = query3
        else:
            query = query+" AND "+query3

    logging.info("Setting and runnning the query on the database")
    querystr = rds.setQuery ( table_name, fields, query, joinstring )
    retQ = rds.execute ( cur, querystr )

    htmlstring = "<head> <style> table { font-family: arial, sans-serif; border-collapse: collapse; width: 80%; }"
    htmlstring = htmlstring+" td, th { border: 1px solid #dddddd; text-align: left; padding: 8px; }"
    htmlstring = htmlstring+" tr:nth-child(even) { background-color: #dddddd; } </style> </head>"
    htmlstring = htmlstring+"<html><body><H2>GBADs Public Database Query: "+str(table_name)+"</h2>"
    htmlstring = htmlstring+"<i>"+str(querystr)+"</i><br><br>"
    htmlstring = htmlstring+"<table><tr>"
    for col in columns:
        htmlstring = htmlstring+"<td><b>"+col+"</b></td>"
    htmlstring = htmlstring+"</tr>"
    file_name = table_name+".csv"
    f = open(file_name, "w")
    print ( fields, file=f  )
    print("retQ",retQ)

    logging.info("Adding the returned data to the htmlstring and CSV file")
    for field in retQ:
        x = 0
        htmlstring = htmlstring+"<tr>"
        while x < len(field)-1:
            if str(field[x])[0] != "\"":
                print ( "\""+str(field[x])+"\"", end=",", file=f  )
            else:
                print ( str(field[x]), end=",", file=f  )
            fstring = str(field[x])
            htmlstring = htmlstring+"<td>"+fstring.strip("\"")+"</td>"
            x = x + 1
        fstring = str(field[x])
        htmlstring = htmlstring+"<td>"+fstring.strip("\"")+"</td></tr>"
        if str(field[x])[0] != "\"":
            print ( "\""+str(field[x])+"\"", file=f  )
        else:
            print ( str(field[x]), file=f  )
    htmlstring = htmlstring+"</table></body></html>"
    f.close()

    if format == "file":
        # Remove file after sending it
        background_tasks.add_task(remove_file, file_name)
        logging.info("Returning data as a csv")
        return FileResponse(file_name,filename=file_name)

    elif format == "html":
        logging.info("Returning data as HTML")
        return HTMLResponse(htmlstring)

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=9000)

