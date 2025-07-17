from fastapi import FastAPI, BackgroundTasks, APIRouter, File, Form, UploadFile, HTTPException
from fastapi.responses import FileResponse, HTMLResponse, StreamingResponse
from fastapi.responses import PlainTextResponse
from botocore.exceptions import NoCredentialsError
from typing import Optional
from pathlib import Path
import uvicorn
import secure_rds as secure
import rds_functions as rds
# import pandas as pd
import os
import logging
# import boto3
import newS3TicketLib as s3f
import jwt
import datetime
from cryptography.fernet import Fernet
import json
import psycopg2 as ps

app = FastAPI(
    docs_url=os.environ.get("BASE_URL", "") + "/docs",
    openapi_url=os.environ.get("BASE_URL", "") + "/openapi.json",
)
router = None

if "BASE_URL" in os.environ:
    router = APIRouter(prefix=os.environ["BASE_URL"])
else:
    router = APIRouter()


# Function to removed the created CSV/HTML file
def remove_file(path):
    try:
        os.unlink(path)
        logging.info("Successfully removed file")
    except Exception as e:
        logging.error("Failed to delete %s." % path)
        print(e)


#
# Loads the key into key.conf
#
def load_key():
    if os.environ.get("MAJOR_KEY", ""):
        return os.environ.get("MAJOR_KEY", "")
    else:
        return open("MajorKey/key.conf", "rb").read()
    return open("key.conf", "rb").read()


# Telling the logger where to log the information
logging.basicConfig(
    filename="logs/logs.txt", level=logging.DEBUG, format="%(asctime)s %(message)s"
)
logging.basicConfig(
    filename="logs/errors.txt", level=logging.ERROR, format="%(asctime)s %(message)s"
)


# Used to access the data portal screen
@router.get("/", include_in_schema=False)
@router.head("/", include_in_schema=False)
def main():
    logging.info("Main endpoint accessed (/)")
    return "Welcome to the public GBADs database tables!"


# Used to access the data portal screen
@router.get("/dataportal/", tags=["Knowledge Engine"])
def home():
    logging.info("Home page accessed")
    html_string = Path("dataPortalDocumentation.html").read_text()
    return HTMLResponse(html_string)


# Used to access the list of all tables
@router.get("/GBADsTables/{public}", tags=["Knowledge Engine"])
async def get_public_tables(public: str, format: Optional[str] = "html"):
    logging.info("GBADsTables/{public} called")

    # Establish a connection to the aws server
    try:
        conn = secure.connect_public()
        cur = conn.cursor()
        logging.info("Connected to GBAD database")
    except Exception as e:
        logging.error("Error connecting to GBAD database")
        htmlMsg = rds.generateHTMLErrorMessage("Error connecting to Database: " + str(e))
        return HTMLResponse(htmlMsg)

    # Get the list of tables from the database
    logging.info("Fetching tables")
    try:
        tables = rds.displayTables(cur)
    except Exception as e:
        logging.error("Error fetching tables")
        htmlMsg = rds.generateHTMLErrorMessage("Error fetching tables: " + str(e))
        return HTMLResponse(htmlMsg)

    fieldCount = len(tables)

    # Start building HTML string
    htmlstring = "<html><body><H2>GBADs Public Database Tables</h2><ul>"
    retstring = ""
    tableCount = 0

    # List each table from the query in the html string and return string
    logging.info("Formatting tables into HTML and the return string")
    for table in tables:
        tableCount = tableCount + 1
        if tableCount < fieldCount:
            htmlstring = htmlstring + "<li> " + table[1]
            if tableCount == 1:
                retstring = table[1]
            else:
                retstring = retstring + "," + table[1]
        else:
            htmlstring = htmlstring + "<li> " + table[1] + "</ul></body></html>"
            retstring = retstring + "," + table[1]

    # Return the text or html string to the user
    if format == "text":
        logging.info("Returning tables as text")
        return PlainTextResponse(retstring)
    else:
        logging.info("Returning tables as HTML")
        return HTMLResponse(htmlstring)


@router.get("/GBADsTable/{public}", tags=["Knowledge Engine"])
async def get_public_table_fields(
    public: str, table_name: str, format: Optional[str] = "html"
):
    logging.info("GBADs Public Query called")

    # Establish connection to AWS
    try:
        conn = secure.connect_public()
        cur = conn.cursor()
        logging.info("Connected to GBAD database")
    except Exception as e:
        logging.error("Error connecting to GBAD database")
        htmlMsg = rds.generateHTMLErrorMessage("Error connecting to Database: " + str(e))
        return HTMLResponse(htmlMsg)

    # Get table info
    logging.info("Fetching fields")
    try:
        fields = rds.displayTabInfo(cur, table_name)
    except Exception as e:
        logging.error("Error fetching fields")
        htmlMsg = rds.generateHTMLErrorMessage("Error fetching fields: " + str(e))
        return HTMLResponse(htmlMsg)

    # Format table info int html format and the return string
    fieldCount = len(fields)
    htmlstring = "<html><body><H2>Data Fields for " + str(table_name) + "</h2><ul>"
    retstring = ""
    tableCount = 0

    logging.info("Formatting fields into HTML and the return string")
    for field in fields:
        tableCount = tableCount + 1
        if tableCount < fieldCount:
            htmlstring = htmlstring + "<li> " + field[0] + " (" + field[1] + ")"
            retstring = retstring + field[0] + ","
        else:
            htmlstring = (
                htmlstring
                + "<li> "
                + field[0]
                + " ("
                + field[1]
                + ") </ul></body></html>"
            )
            retstring = retstring + field[0]

    if format == "html":
        logging.info("Returning fields as HTML")
        return HTMLResponse(htmlstring)
    else:
        logging.info("Returning fields as text")
        return PlainTextResponse(retstring)


@router.get("/GBADsPublicQuery/{table_name}", tags=["Knowledge Engine"])
async def get_db_query(
    table_name: str,
    fields: str,
    query: str,
    join: Optional[str] = "",
    order: Optional[str] = "",
    format: Optional[str] = "html",
    count: Optional[str] = "no",
    pivot: Optional[str] = "",
    background_tasks: BackgroundTasks = None,
):
    logging.info("GBADsPublicQuery called")

    # Establish connection to AWS
    try:
        conn = secure.connect_public()
        cur = conn.cursor()
        logging.info("Connected to GBAD database")
    except Exception as e:
        logging.error("Error connecting to GBAD database")
        htmlMsg = rds.generateHTMLErrorMessage("Error connecting to Database: " + str(e))
        return HTMLResponse(htmlMsg)

    # Get all fields if fields == *
    if fields == "*":
        try:
            newfields = rds.generateFieldNames(cur, table_name)
        except Exception as e:
            logging.error("Error fetching fields")
            htmlMsg = rds.generateHTMLErrorMessage("Error fetching fields: " + str(e))
            return HTMLResponse(htmlMsg)

        # Format the fields into a string
        fields = ""
        for i in range(len(newfields)):
            fields = fields + newfields[i]
            if i < len(newfields) - 1:
                fields = fields + ","

    logging.info("Formatting the query")
    joinitems = []
    if join != "":
        joinitems = join.split(",")
        table_name1 = joinitems[0]
        table_name2 = joinitems[1]
        jfield_1 = joinitems[2]
        jfield_2 = joinitems[3]
        joinstring = rds.setJoin(table_name1, table_name2, jfield_1, jfield_2)
    else:
        joinstring = ""

    logging.info("Setting and running the query on the database")
    if count == "no":
        try:
            returnedQuery = rds.query(cur, table_name, fields, query, joinstring, order)
        except Exception as e:
            logging.error("Error running the query")
            htmlMsg = rds.generateHTMLErrorMessage(
                "Error in the given query. Please check the syntax and try again. " + str(e)
            )
            return HTMLResponse(htmlMsg)

        querystr = rds.setQuery(table_name, fields, query, joinstring)
    else:
        try:
            returnedQuery = rds.countQuery(
                cur, table_name, fields, query, joinstring, order
            )
        except Exception as e:
            logging.error("Error running the query")
            htmlMsg = rds.generateHTMLErrorMessage(
                "Error in the given query. Please check the syntax and try again. " + str(e)
            )
            return HTMLResponse(htmlMsg)

        querystr = rds.setCountQuery(table_name, fields, query, joinstring)

    # debugging
    # print ( query )

    # Format the query into the html and return string
    logging.info("Formatting the results into a file and reutrn string")
    htmlstring = "<head> <style> table { font-family: arial, sans-serif; border-collapse: collapse; width: 80%; }"
    htmlstring = (
        htmlstring
        + " td, th { border: 1px solid #dddddd; text-align: left; padding: 8px; }"
    )
    htmlstring = (
        htmlstring
        + " tr:nth-child(even) { background-color: #dddddd; } </style> </head>"
    )
    htmlstring = htmlstring + "<html><body><H2>GBADs Public Database Query </h2>"
    htmlstring = htmlstring + "<i>" + str(querystr) + "</i><br><br>"
    htmlstring = htmlstring + "<table><tr>"
    for col in fields.split(","):
        htmlstring = htmlstring + "<td><b>" + col + "</b></td>"
    htmlstring = htmlstring + "</tr>"
    file_name = table_name + ".csv"
    f = open(file_name, "w")
    print(fields, file=f)

    # Format the rows of the table
    for field in returnedQuery:
        x = 0
        htmlstring = htmlstring + "<tr>"
        while x < len(field) - 1:
            print('"' + str(field[x]) + '"', end=",", file=f)
            fstring = str(field[x])
            htmlstring = htmlstring + "<td>" + fstring.rstrip() + "</td>"
            x = x + 1
        fstring = str(field[x])
        htmlstring = htmlstring + "<td>" + fstring.rstrip() + "</td></tr>"
        print('"' + str(field[x]) + '"', file=f)
    htmlstring = htmlstring + "</table></body></html>"
    f.close()

    # Return the html or text string to the user
    if format == "html":
        logging.info("Returning results as HTML")
        background_tasks.add_task(remove_file, file_name)
        return HTMLResponse(htmlstring)
    else:
        logging.info("Returning results as CSV")
        background_tasks.add_task(remove_file, file_name)
        return FileResponse(file_name, filename=file_name)


@router.get("/GBADsLivestockPopulation/{data_source}", tags=["Knowledge Engine"])
async def get_population(
    data_source: str,
    format: str,
    year: Optional[str] = "*",
    iso3: Optional[str] = "*",
    country: Optional[str] = "*",
    species: Optional[str] = "*",
    background_tasks: BackgroundTasks = None,
):
    logging.info("GBADsLivestockPopulation called")

    # Establish a connection to AWS
    try:
        conn = secure.connect_public()
        cur = conn.cursor()
        logging.info("Connected to GBAD database")
    except Exception as e:
        logging.error("Error connecting to GBAD database")
        htmlMsg = rds.generateHTMLErrorMessage("Error connecting to Database: " + str(e))
        return HTMLResponse(htmlMsg)

    logging.info("Formatting query")
    if data_source == "oie":
        table_name = "livestock_national_population_" + data_source
        fields = "country,year,species,population,metadataflags"

    elif data_source == "faostat":
        table_name = "livestock_countries_population_" + data_source
        fields = "iso3,country,year,species,population"

    else:
        return "Invalid data source, Try faostat or oie instead"

    query1 = ""
    query2 = ""
    query3 = ""
    if year != "*":
        query1 = "year=" + year

    if country != "*":
        if data_source == "faostat":
            query2 = "country='" + country + "'"
        elif data_source == "oie":
            query2 = "country='" + country + "'"

    if iso3 != "*":
        if data_source == "faostat":
            query2 = "iso3='" + iso3 + "'"

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
                query3 = "species='" + species + "'"
        else:
            if species == "Poultry":
                query3 = "(species='Chickens' OR species='Turkeys' OR species='Ducks' OR species='Geese and guinea fowls')"
            else:
                query3 = "species='" + species + "'"

    query = ""
    if query1 != "":
        query = query1
    if query2 != "":
        if query == "":
            query = query2
        else:
            query = query + " AND " + query2
    if query3 != "":
        if query == "":
            query = query3
        else:
            query = query + " AND " + query3

    joinstring = ""
    logging.info("Setting and runnning the query on the database")
    querystr = rds.setQuery(table_name, fields, query, joinstring)

    try:
        returnedQuery = rds.query(cur, table_name, fields, query, joinstring)
        logging.info("Query returned")
    except Exception as e:
        logging.error("Error running query")
        htmlstring = rds.generateHTMLErrorMessage(
            "Error in the given query. Please check the syntax and try again. " + str(e)
        )
        return HTMLResponse(htmlstring)

    htmlstring = "<head> <style> table { font-family: arial, sans-serif; border-collapse: collapse; width: 80%; }"
    htmlstring = (
        htmlstring
        + " td, th { border: 1px solid #dddddd; text-align: left; padding: 8px; }"
    )
    htmlstring = (
        htmlstring
        + " tr:nth-child(even) { background-color: #dddddd; } </style> </head>"
    )
    htmlstring = (
        htmlstring
        + "<html><body><H2>GBADs Public Database Query: "
        + str(table_name)
        + "</h2>"
    )
    htmlstring = htmlstring + "<i>" + str(querystr) + "</i><br><br>"
    htmlstring = htmlstring + "<table><tr>"
    for col in fields.split(","):
        htmlstring = htmlstring + "<td><b>" + col + "</b></td>"
    htmlstring = htmlstring + "</tr>"
    file_name = table_name + ".csv"
    f = open(file_name, "w")
    print(fields, file=f)
    # print("returnedQuery ",returnedQuery)

    logging.info("Adding the returned data to the htmlstring and CSV file")
    for field in returnedQuery:
        x = 0
        htmlstring = htmlstring + "<tr>"
        while x < len(field) - 1:
            if str(field[x])[0] != '"':
                print('"' + str(field[x]) + '"', end=",", file=f)
            else:
                print(str(field[x]), end=",", file=f)
            fstring = str(field[x])
            htmlstring = htmlstring + "<td>" + fstring.strip('"') + "</td>"
            x = x + 1
        fstring = str(field[x])
        htmlstring = htmlstring + "<td>" + fstring.strip('"') + "</td></tr>"
        if str(field[x])[0] != '"':
            print('"' + str(field[x]) + '"', file=f)
        else:
            print(str(field[x]), file=f)
    htmlstring = htmlstring + "</table></body></html>"
    f.close()

    if format == "file":
        # Remove file after sending it
        background_tasks.add_task(remove_file, file_name)
        logging.info("Returning data as a csv")
        return FileResponse(file_name, filename=file_name)

    elif format == "html":
        background_tasks.add_task(remove_file, file_name)
        logging.info("Returning data as HTML")
        return HTMLResponse(htmlstring)
    else:
        logging.error("Invalid format")
        background_tasks.add_task(remove_file, file_name)
        htmlstring = rds.generateHTMLErrorMessage(
            "Invalid format. Please use html or file."
        )
        return HTMLResponse(htmlstring)


@router.post("/slack/approve/{comment_id}", tags=["Internal Slack"])
async def slack_approve_comment(
    comment_id: str, authorization_token: str, reviewer: Optional[str] = "none"
):
    logging.info("/slack/approve called")
    #
    # Information for the task
    #
    key_filename = "slackbot_comments_move_approve_key.pub"
    #
    # Read in the public key
    #
    try:
        fptr = open(key_filename, "rb")
        key = fptr.read()
        fptr.close()
    except Exception as e:
        logging.error("Bad information about public key filename")
        htmlMsg = rds.generateHTMLErrorMessage(
            "Bad information about public key filename: " + str(e)
        )
        return HTMLResponse(htmlMsg)
    #
    # Decode the token and check for validity
    #
    desired_app = "slackbot_comments_move"
    desired_task = "approve"
    try:
        decoded = jwt.decode(authorization_token, key, algorithms=["RS256"])
        logging.info("Valid JSON Web Token")
    except Exception as e:
        logging.error("Invalid JSON Web Token")
        htmlMsg = rds.generateHTMLErrorMessage("Invalid JSON Web Token: " + str(e))
        return HTMLResponse(htmlMsg)
    #
    # Check to see if the JWT payload is valid
    #
    if decoded["app"] != desired_app:
        logging.error("Invalid app in JSON Web Token payload")
        htmlMsg = rds.generateHTMLErrorMessage("Invalid app in JSON Web Token payload")
        return HTMLResponse(htmlMsg)
    else:
        logging.info("JWT app = " + decoded["app"])
    if decoded["task"] != desired_task:
        logging.error("Invalid task in JSON Web Token payload")
        htmlMsg = rds.generateHTMLErrorMessage("Invalid task in JSON Web Token payload")
        return HTMLResponse(htmlMsg)
    else:
        logging.info("JWT task = " + decoded["app"])
    #
    # decode keys
    #
    key = load_key()
    # initialize the Fernet class
    f = Fernet(key)
    # read the encrypted keys
    encrypt1 = os.environ.get("MAJOR_INFO1", "")
    encrypt2 = os.environ.get("MAJOR_INFO2", "")
    if not encrypt1:
        with open("info.conf", "r") as info_file:
            encrypt1 = info_file.readline().strip()
            encrypt2 = info_file.readline().strip()

    access = f.decrypt(encrypt1.encode("utf-8")).decode("utf-8")
    secret = f.decrypt(encrypt2.encode("utf-8")).decode("utf-8")
    #
    #  Access AWS Credentials and establish session as a client and resource
    #
    s3_client = s3f.credentials_client(access, secret)
    if s3_client == -1:
        logging.error("Cannot connect to S3 as client")
        htmlMsg = rds.generateHTMLErrorMessage(
            "Cannot connect to S3 as client: " + access + " and " + secret
        )
        return HTMLResponse(htmlMsg)
    s3_resource = s3f.credentials_resource(access, secret)
    if s3_resource == -1:
        logging.error("Cannot connect to S3 as resource")
        htmlMsg = rds.generateHTMLErrorMessage(
            "Cannot connect to S3 as resource: " + access + " and " + secret
        )
        return HTMLResponse(htmlMsg)

    # htmlstring = "<html><body><H2>Slackbot</h2><ul><li>stage 1 good</li>"

    #
    # Extract information from the json file and construct a database table entry
    #
    bucket = "gbads-comments"
    srcFolder = "underreview/"
    key0 = srcFolder + comment_id
    json_object = s3_client.get_object(Bucket=bucket, Key=key0)
    file_reader = json_object["Body"].read().decode("utf-8")
    file_reader = json.loads(file_reader)

    # htmlstring = htmlstring+" <li>stage 2a - json "+key0+" retrieved and loaded</li>"

    created = str(file_reader["created"])[0:19]
    approved = str(datetime.datetime.now())[0:19]
    dashboard = str(file_reader["dashboard"])
    table = str(file_reader["table"])
    subject = str(file_reader["subject"])
    message = str(file_reader["message"])
    isPublic = str(file_reader["isPublic"]).upper()
    if isPublic == "FALSE":
        name = "NULL"
        email = "NULL"
    else:
        name = str(file_reader["name"])
        email = str(file_reader["email"])
    if len(reviewer) > 0:
        dbRow = (
            "('"
            + created
            + "','"
            + approved
            + "','"
            + dashboard
            + "','"
            + table
            + "','"
            + subject
            + "','"
            + message
            + "','"
            + name
            + "','"
            + email
            + "',"
            + isPublic
            + ",'"
            + reviewer
            + "')"
        )
    else:
        reviewer = "Unknown"
        dbRow = (
            "('"
            + created
            + "','"
            + approved
            + "','"
            + dashboard
            + "','"
            + table
            + "','"
            + subject
            + "','"
            + message
            + "','"
            + name
            + "','"
            + email
            + "',"
            + isPublic
            + ",'"
            + reviewer
            + "')"
        )

    # htmlstring = htmlstring + " <li>stage 2b - json decoded from comment_id</li>"

    #
    # Get database information
    #
    key1 = "information/database.json"

    # htmlstring = htmlstring+" <li>stage 3a - json "+key1+" started...</li>"

    json_object1 = s3_client.get_object(Bucket=bucket, Key=key1)
    file_reader1 = json_object1["Body"].read().decode("utf-8")
    file_reader1 = json.loads(file_reader1)
    db_host = str(file_reader1["DBHOST"])
    db_name = str(file_reader1["DBNAME"])
    db_user = str(file_reader1["DBUSER"])
    db_pass = str(file_reader1["DBPASS"])

    # htmlstring = htmlstring+" <li>stage 3a - json "+key1+" retrieved and decoded</li>"

    #
    # Create connection and cursor to database and insert new record
    #
    conn_string = (
        "host="
        + db_host
        + " dbname="
        + db_name
        + " user="
        + db_user
        + " password="
        + db_pass
    )
    conn_write = ps.connect(conn_string)
    cur_write = conn_write.cursor()
    insert_string = "INSERT into gbads_comments VALUES " + dbRow + ";"
    cur_write.execute(insert_string)
    #
    # Commit data insertion and close database connection
    #
    conn_write.commit()
    conn_write.close()

    # htmlstring = htmlstring+" <li>stage 3b - database table insert completed</li>"

    #
    # To move a file: 1) copy the file to the given directory
    #
    bucket = "gbads-comments"
    srcFolder = "underreview/"
    destFolder = "approved/"
    sourceObj = srcFolder + comment_id
    destObj = destFolder + comment_id
    ret = s3f.s3Copy(s3_client, bucket, sourceObj, destObj)
    #
    # Next: 2) delete the original file
    #
    if ret == 0:
        ret = s3f.s3Delete(s3_client, bucket, sourceObj)
        if ret == 0:
            logging.info("S3 Approve successful")
            htmlstring = (
                "<html><body><H3>GBADs S3 Slack Approve Comment</h3></body></html>"
            )
            # htmlstring = "<html><body><H2>Slackbot</h2><ul><li>stage 1 good</li>"
            return HTMLResponse(htmlstring)
        else:
            logging.error("S3 Delete not successful")
            htmlMsg = rds.generateHTMLErrorMessage("S3 Delete not successful")
            return HTMLResponse(htmlMsg)
    else:
        logging.error("S3 Copy not successful")
        htmlMsg = rds.generateHTMLErrorMessage("S3 Copy not successful")
        return HTMLResponse(htmlMsg)


@router.post("/slack/deny/{comment_id}", tags=["Internal Slack"])
def slack_deny_comment(comment_id: str, authorization_token: str):
    logging.info("/slack/deny called")
    #
    # Information for the task
    #
    key_filename = "slackbot_comments_move_deny_key.pub"
    #
    # Read in the public key
    #
    try:
        fptr = open(key_filename, "rb")
        key = fptr.read()
        fptr.close()
    except Exception as e:
        logging.error("Bad information about public key filename")
        htmlMsg = rds.generateHTMLErrorMessage(
            "Bad information about public key filename: " + str(e)
        )
        return HTMLResponse(htmlMsg)
    #
    # Decode the token and check for validity
    #
    desired_app = "slackbot_comments_move"
    desired_task = "deny"
    try:
        decoded = jwt.decode(authorization_token, key, algorithms=["RS256"])
        logging.info("Valid JSON Web Token")
    except Exception as e:
        logging.error("Invalid JSON Web Token")
        htmlMsg = rds.generateHTMLErrorMessage("Invalid JSON Web Token: " + str(e))
        return HTMLResponse(htmlMsg)
    #
    # Check to see if the JWT payload is valid
    #
    if decoded["app"] != desired_app:
        logging.error("Invalid app in JSON Web Token payload")
        htmlMsg = rds.generateHTMLErrorMessage("Invalid app in JSON Web Token payload")
        return HTMLResponse(htmlMsg)
    else:
        logging.info("JWT app = " + decoded["app"])
    if decoded["task"] != desired_task:
        logging.error("Invalid task in JSON Web Token payload")
        htmlMsg = rds.generateHTMLErrorMessage("Invalid task in JSON Web Token payload")
        return HTMLResponse(htmlMsg)
    else:
        logging.info("JWT task = " + decoded["task"])
    #
    # decode keys
    #
    key = load_key()
    # initialize the Fernet class
    f = Fernet(key)
    # read the encrypted keys
    encrypt1 = os.environ.get("MAJOR_INFO1", "")
    encrypt2 = os.environ.get("MAJOR_INFO2", "")
    if not encrypt1:
        with open("info.conf", "r") as info_file:
            encrypt1 = info_file.readline().strip()
            encrypt2 = info_file.readline().strip()

    access = f.decrypt(encrypt1.encode("utf-8")).decode("utf-8")
    secret = f.decrypt(encrypt2.encode("utf-8")).decode("utf-8")

    #
    #  Access AWS Credentials and establish session as a client and resource
    #
    s3_client = s3f.credentials_client(access, secret)
    if s3_client == -1:
        logging.error("Cannot connect to S3 as client")
        htmlMsg = rds.generateHTMLErrorMessage("Cannot connect to S3 as client")
        return HTMLResponse(htmlMsg)
    s3_resource = s3f.credentials_resource(access, secret)
    if s3_resource == -1:
        logging.error("Cannot connect to S3 as resource")
        htmlMsg = rds.generateHTMLErrorMessage(
            "Cannot connect to S3 as resource: " + access + " and " + secret
        )
        return HTMLResponse(htmlMsg)
    #
    # To move a file: 1) copy the file to the given directory
    #
    bucket = "gbads-comments"
    srcFolder = "underreview/"
    destFolder = "notapproved/"
    sourceObj = srcFolder + comment_id
    destObj = destFolder + comment_id
    ret = s3f.s3Copy(s3_client, bucket, sourceObj, destObj)
    #
    # Next: 2) delete the original file
    #
    if ret == 0:
        ret = s3f.s3Delete(s3_client, bucket, sourceObj)
        if ret == 0:
            logging.info("S3 Deny successful")
            htmlstring = (
                "<html><body><H3>GBADs S3 Slack Deny Comment</h3></body></html>"
            )
            return HTMLResponse(htmlstring)
        else:
            logging.error("S3 Delete not successful")
            htmlMsg = rds.generateHTMLErrorMessage("S3 Delete not successful")
            return HTMLResponse(htmlMsg)
    else:
        logging.error("S3 Copy not successful")
        htmlMsg = rds.generateHTMLErrorMessage("S3 Copy not successful")
        return HTMLResponse(htmlMsg)


@app.post("/s3/upload", tags=["S3 DPM Endpoints"])
async def upload_file(bucket_name: str = Form(...), object_name: str = Form(...), file: UploadFile = File(...)):
    key = load_key()
    f = Fernet(key)
    encrypt1 = os.environ.get("MAJOR_INFO1", "")
    encrypt2 = os.environ.get("MAJOR_INFO2", "")
    if not encrypt1:
        with open("info.conf", "r") as info_file:
            encrypt1 = info_file.readline().strip()
            encrypt2 = info_file.readline().strip()

    access = f.decrypt(encrypt1.encode("utf-8")).decode("utf-8")
    secret = f.decrypt(encrypt2.encode("utf-8")).decode("utf-8")

    #  Access AWS Credentials and establish session as a client and resource
    s3_client = s3f.credentials_client(access, secret)
    if s3_client == -1:
        logging.error("Cannot connect to S3 as client")
        htmlMsg = rds.generateHTMLErrorMessage("Cannot connect to S3 as client")
        return HTMLResponse(htmlMsg)
    s3_resource = s3f.credentials_resource(access, secret)
    if s3_resource == -1:
        logging.error("Cannot connect to S3 as resource")
        htmlMsg = rds.generateHTMLErrorMessage(
            "Cannot connect to S3 as resource: " + access + " and " + secret
        )
        return HTMLResponse(htmlMsg)

    try:
        # Upload the file to S3
        s3f.upload_file(s3_client, bucket_name, object_name, file.file)
        return {"message": "File uploaded successfully"}
    except NoCredentialsError:
        raise HTTPException(status_code=500, detail="AWS credentials not available")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An error occurred: {str(e)}")


@app.get("/s3/download", tags=["S3 DPM Endpoints"])
async def download_file(bucket_name: str, object_name: str):
    key = load_key()
    f = Fernet(key)
    encrypt1 = os.environ.get("MAJOR_INFO1", "")
    encrypt2 = os.environ.get("MAJOR_INFO2", "")
    if not encrypt1:
        with open("info.conf", "r") as info_file:
            encrypt1 = info_file.readline().strip()
            encrypt2 = info_file.readline().strip()

    access = f.decrypt(encrypt1.encode("utf-8")).decode("utf-8")
    secret = f.decrypt(encrypt2.encode("utf-8")).decode("utf-8")

    #  Access AWS Credentials and establish session as a client and resource
    s3_client = s3f.credentials_client(access, secret)
    if s3_client == -1:
        logging.error("Cannot connect to S3 as client")
        htmlMsg = rds.generateHTMLErrorMessage("Cannot connect to S3 as client")
        return HTMLResponse(htmlMsg)
    s3_resource = s3f.credentials_resource(access, secret)
    if s3_resource == -1:
        logging.error("Cannot connect to S3 as resource")
        htmlMsg = rds.generateHTMLErrorMessage(
            "Cannot connect to S3 as resource: " + access + " and " + secret
        )
        return HTMLResponse(htmlMsg)

    try:
        response = s3f.download_file(s3_client, bucket_name, object_name)
        if response is None:
            raise HTTPException(status_code=404, detail="File not found")
        return StreamingResponse(
            response['Body'].iter_chunks(),
            media_type=response['ContentType'],
            headers={"Content-Disposition": f"attachment; filename={object_name}"}
        )
    except NoCredentialsError:
        raise HTTPException(status_code=500, detail="AWS credentials not available")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An error occurred: {str(e)}")

# This router allows a custom path to be used for the API
app.include_router(router)

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=9000)
