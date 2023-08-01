from fastapi import FastAPI, Response, BackgroundTasks, APIRouter
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
import boto3
import newS3TicketLib as s3f
import jwt
from datetime import datetime
from Crypto.Cipher import AES
import base64, math

app = FastAPI(docs_url=os.environ.get('BASE_URL', '') + "/docs", openapi_url=os.environ.get('BASE_URL', '') + "/openapi.json")
router = None

if "BASE_URL" in os.environ:
    router = APIRouter(prefix=os.environ["BASE_URL"])
else:
    router = APIRouter()

#Function to removed the created CSV/HTML file
def remove_file(path):
    try:
        os.unlink(path)
        logging.info("Successfully removed file")
    except Exception as e:
        logging.error("Failed to delete %s." % path)

#
# Decrypting functions
#
def get_common_cipher( ce_key, cbyte ):
    return AES.new(ce_key, AES.MODE_CBC, cbyte)

def decrypt_with_common_cipher( ce_key, cbyte, ciphertext):
    common_cipher = get_common_cipher( ce_key, cbyte )
    raw_ciphertext = base64.b64decode(ciphertext)
    decrypted_message_with_padding = common_cipher.decrypt(raw_ciphertext)
    return decrypted_message_with_padding.decode('utf-8').strip()

def get_info ( filename ):
    fp = open(filename, "r")
    Lines = fp.readlines()
    ce_key = Lines[0].strip()
    cbyte = Lines[1].strip()
    ens1 = Lines[2].strip()
    ens2 = Lines[3].strip()
    s1 = decrypt_with_common_cipher( ce_key, cbyte, ens1)
    s2 = decrypt_with_common_cipher( ce_key, cbyte, ens2)
    return s1, s2

#Telling the logger where to log the information
logging.basicConfig(filename="logs/logs.txt", level=logging.DEBUG, format="%(asctime)s %(message)s")
logging.basicConfig(filename="logs/errors.txt", level=logging.ERROR, format="%(asctime)s %(message)s")


#Used to access the data portal screen
@router.get("/dataportal/", tags=["Knowledge Engine"])
def home():
    logging.info("Home page accessed")
    html_string = Path('dataPortalDocumentation.html').read_text()
    return HTMLResponse(html_string)


#Used to access the list of all tables
@router.get("/GBADsTables/{public}", tags=["Knowledge Engine"])
async def get_public_tables( public: str, 
                                format: Optional[str] = "html"):
    logging.info("GBADsTables/{public} called")

    #Establish a connection to the aws server
    try:
        conn = secure.connect_public()
        cur = conn.cursor()
        logging.info("Connected to GBAD database")
    except:
        logging.error("Error connecting to GBAD database")
        htmlMsg = rds.generateHTMLErrorMessage("Error connecting to Database")
        return HTMLResponse(htmlMsg)

    #Get the list of tables from the database
    logging.info("Fetching tables")
    try:
        tables = rds.displayTables(cur)
    except:
        logging.error("Error fetching tables")
        htmlMsg = rds.generateHTMLErrorMessage("Error fetching tables")
        return HTMLResponse(htmlMsg)

    fieldCount = len(tables)

    #Start building HTML string
    htmlstring = "<html><body><H2>GBADs Public Database Tables</h2><ul>"
    retstring = ""
    tableCount = 0

    #List each table from the query in the html string and return string
    logging.info("Formatting tables into HTML and the return string")
    for table in tables:
        tableCount = tableCount + 1
        if tableCount < fieldCount:
            htmlstring = htmlstring+"<li> "+table[1]
            if tableCount == 1:
                retstring = table[1]
            else:
                retstring = retstring+","+table[1]
        else:
            htmlstring = htmlstring+"<li> "+table[1]+"</ul></body></html>"
            retstring = retstring+","+table[1]

    # Return the text or html string to the user
    if format == "text":
        logging.info("Returning tables as text")
        return PlainTextResponse(retstring)
    else:
        logging.info("Returning tables as HTML")
        return HTMLResponse(htmlstring)


@router.get("/GBADsTable/{public}", tags=["Knowledge Engine"])
async def get_public_table_fields( public: str, 
                                    table_name: str, 
                                    format: Optional[str] = "html" ):
    logging.info("GBADs Public Query called")

    # Establish connection to AWS
    try:
        conn = secure.connect_public()
        cur = conn.cursor()
        logging.info("Connected to GBAD database")
    except:
        logging.error("Error connecting to GBAD database")
        htmlMsg = rds.generateHTMLErrorMessage("Error connecting to Database")
        return HTMLResponse(htmlMsg)

    # Get table info
    logging.info("Fetching fields")
    try:
        fields = rds.displayTabInfo ( cur, table_name )
    except:
        logging.error("Error fetching fields")
        htmlMsg = rds.generateHTMLErrorMessage("Error fetching fields")
        return HTMLResponse(htmlMsg)

    # Format table info int html format and the return string
    fieldCount = len(fields)
    htmlstring = "<html><body><H2>Data Fields for "+str(table_name)+"</h2><ul>"
    retstring = ""
    tableCount = 0

    logging.info("Formatting fields into HTML and the return string")
    for field in fields:
        tableCount = tableCount + 1
        if tableCount < fieldCount:
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


@router.get("/GBADsPublicQuery/{table_name}", tags=["Knowledge Engine"])
async def get_db_query( table_name: str,
                        fields: str,
                        query: str,
                        join: Optional[str] = "",
                        order: Optional[str] = "",
                        format: Optional[str] = "html",
                        count: Optional[str] = "no",
                        pivot: Optional[str] = "",
                        background_tasks: BackgroundTasks = None ):
    logging.info("GBADsPublicQuery called")

    # Establish connection to AWS
    try:
        conn = secure.connect_public()
        cur = conn.cursor()
        logging.info("Connected to GBAD database")
    except:
        logging.error("Error connecting to GBAD database")
        htmlMsg = rds.generateHTMLErrorMessage("Error connecting to Database")
        return HTMLResponse(htmlMsg)

    # Get all fields if fields == *
    if fields == "*":
        try:
            newfields = rds.generateFieldNames ( cur, table_name )
        except:
            logging.error("Error fetching fields")
            htmlMsg = rds.generateHTMLErrorMessage("Error fetching fields")
            return HTMLResponse(htmlMsg)

        # Format the fields into a string
        fields = ""
        for i in range(len(newfields)):
            fields = fields+newfields[i]
            if i < len(newfields)-1:
                fields = fields+","

    logging.info("Formatting the query")
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
        try:
            returnedQuery = rds.query(cur, table_name, fields, query, joinstring, order)
        except:
            logging.error("Error running the query")
            htmlMsg = rds.generateHTMLErrorMessage("Error in the given query. Please check the syntax and try again.")
            return HTMLResponse(htmlMsg)

        querystr = rds.setQuery ( table_name, fields, query, joinstring )
    else:
        try:
            returnedQuery = rds.countQuery(cur, table_name, fields, query, joinstring, order)
        except:
            logging.error("Error running the query")
            htmlMsg = rds.generateHTMLErrorMessage("Error in the given query. Please check the syntax and try again.")
            return HTMLResponse(htmlMsg)

        querystr = rds.setCountQuery ( table_name, fields, query, joinstring )

#debugging
    # print ( query )

    # Format the query into the html and return string
    logging.info("Formatting the results into a file and reutrn string")
    htmlstring = "<head> <style> table { font-family: arial, sans-serif; border-collapse: collapse; width: 80%; }"
    htmlstring = htmlstring+" td, th { border: 1px solid #dddddd; text-align: left; padding: 8px; }"
    htmlstring = htmlstring+" tr:nth-child(even) { background-color: #dddddd; } </style> </head>"
    htmlstring = htmlstring+"<html><body><H2>GBADs Public Database Query </h2>"
    htmlstring = htmlstring+"<i>"+str(querystr)+"</i><br><br>"
    htmlstring = htmlstring+"<table><tr>"
    for col in fields.split(","):
        htmlstring = htmlstring+"<td><b>"+col+"</b></td>"
    htmlstring = htmlstring+"</tr>"
    file_name = table_name+".csv"
    f = open(file_name, "w")
    print ( fields, file=f )

    # Format the rows of the table
    for field in returnedQuery:
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

    # Return the html or text string to the user
    if format == "html":
        logging.info("Returning results as HTML")
        background_tasks.add_task(remove_file, file_name)
        return HTMLResponse(htmlstring)
    else:
        logging.info("Returning results as CSV")
        background_tasks.add_task(remove_file, file_name)
        return FileResponse(file_name,filename=file_name)


@router.get("/GBADsLivestockPopulation/{data_source}", tags=["Knowledge Engine"])
async def get_population ( data_source: str,
                            format: str,
                            year: Optional[str] = "*",
                            iso3: Optional[str] = "*",
                            country: Optional[str] = "*",
                            species: Optional[str] = "*",
                            background_tasks: BackgroundTasks = None ):

    logging.info("GBADsLivestockPopulation called")

    # Establish a connection to AWS
    try:
        conn = secure.connect_public()
        cur = conn.cursor()
        logging.info("Connected to GBAD database")
    except:
        logging.error("Error connecting to GBAD database")
        htmlMsg = rds.generateHTMLErrorMessage("Error connecting to Database")
        return HTMLResponse(htmlMsg)

    logging.info("Formatting query")
    if data_source == "oie":
        table_name = "livestock_national_population_"+data_source
        fields = "country,year,species,population,metadataflags"

    elif data_source == "faostat":
        table_name = "livestock_countries_population_"+data_source
        fields = "iso3,country,year,species,population"

    else:
        return "Invalid data source, Try faostat or oie instead"


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

    joinstring = ""
    logging.info("Setting and runnning the query on the database")
    querystr = rds.setQuery ( table_name, fields, query, joinstring )

    try:
        returnedQuery = rds.query(cur, table_name, fields, query, joinstring)
        logging.info("Query returned")
    except:
        logging.error("Error running query")
        htmlstring = rds.generateHTMLErrorMessage("Error in the given query. Please check the syntax and try again.")
        return HTMLResponse(htmlstring)

    htmlstring = "<head> <style> table { font-family: arial, sans-serif; border-collapse: collapse; width: 80%; }"
    htmlstring = htmlstring+" td, th { border: 1px solid #dddddd; text-align: left; padding: 8px; }"
    htmlstring = htmlstring+" tr:nth-child(even) { background-color: #dddddd; } </style> </head>"
    htmlstring = htmlstring+"<html><body><H2>GBADs Public Database Query: "+str(table_name)+"</h2>"
    htmlstring = htmlstring+"<i>"+str(querystr)+"</i><br><br>"
    htmlstring = htmlstring+"<table><tr>"
    for col in fields.split(","):
        htmlstring = htmlstring+"<td><b>"+col+"</b></td>"
    htmlstring = htmlstring+"</tr>"
    file_name = table_name+".csv"
    f = open(file_name, "w")
    print ( fields, file=f  )
    # print("returnedQuery ",returnedQuery)

    logging.info("Adding the returned data to the htmlstring and CSV file")
    for field in returnedQuery:
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
        background_tasks.add_task(remove_file, file_name)
        logging.info("Returning data as HTML")
        return HTMLResponse(htmlstring)
    else :
        logging.error("Invalid format")
        background_tasks.add_task(remove_file, file_name)
        htmlstring = rds.generateHTMLErrorMessage("Invalid format. Please use html or file.")
        return HTMLResponse(htmlstring)


@router.post("/slack/approve/{comment_id}", tags=["Internal Slack"])
async def slack_approve_comment(comment_id: str, authorization_token: str):
    logging.info("/slack/approve called")
    #
    # Information for the task
    #
    desired_app = "slack-approve"
    #
    # Read in the public key
    #
    key_filename = desired_app+"key.pub"
    try:
        fptr = open(key_filename, "rb")
        key = fptr.read()
        fptr.close()
    except:
        logging.error("Bad information about public key filename")
        htmlMsg = rds.generateHTMLErrorMessage("Bad information about public key filename")
        return HTMLResponse(htmlMsg)
    #
    # Decode the token and check for validity
    #
    try:
        decoded = jwt.decode (
            authorization_token,
            key,
            algorithms=["RS256"]
        )
        logging.info("Valid JSON Web Token")
    except:
        logging.error("Invalid JSON Web Token")
        htmlMsg = rds.generateHTMLErrorMessage("Invalid JSON Web Token")
        return HTMLResponse(htmlMsg)
    #
    # Check to see if the JWT payload is valid
    #
    if decoded["app"] != desired_app:
        logging.error("Invalid app in JSON Web Token payload")
        htmlMsg = rds.generateHTMLErrorMessage("Invalid app in JSON Web Token payload")
        return HTMLResponse(htmlMsg)
    else:
        logging.info("JWT app = "+decoded['app'])
    access = decoded["access"]
    secret = decoded["secret"]
    #
    #  Access AWS Credentials and establish session as a client and resource
    #
    s3_client = s3f.credentials_client ( access, secret )
    if s3_client == -1:
        logging.error("Cannot connect to S3 as client")
        htmlMsg = rds.generateHTMLErrorMessage("Cannot connect to S3 as client: "+access+" and "+secret)
        return HTMLResponse(htmlMsg)
    s3_resource = s3f.credentials_resource ( access, secret )
    if s3_resource == -1:
        logging.error("Cannot connect to S3 as resource")
        htmlMsg = rds.generateHTMLErrorMessage("Cannot connect to S3 as resource: "+access+" and "+secret)
        return HTMLResponse(htmlMsg)
    #
    # To move a file: 1) copy the file to the given directory
    #
    bucket = "gbads-comments"
    srcFolder = "underreview/"
    destFolder = "approved/"
    sourceObj = srcFolder+comment_id
    destObj = destFolder+comment_id
    ret = s3f.s3Copy ( s3_client, bucket, sourceObj, destObj )
    #
    # Next: 2) delete the original file
    #
    if ret == 0:
        ret = s3f.s3Delete ( s3_client, bucket, sourceObj )
        if ret == 0:
            logging.info("S3 Approve successful")
            htmlstring = "<html><body><H3>GBADs S3 Slack Approve Comment</h3></body></html>"
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
    except:
        logging.error("Bad information about public key filename")
        htmlMsg = rds.generateHTMLErrorMessage("Bad information about public key filename")
        return HTMLResponse(htmlMsg)
    htmlstring = "<html><body><H3>GBADs S3 Slack Deny Comment Entered - 1</h3></body></html>"
    return HTMLResponse(htmlstring)
    #
    # Decode the token and check for validity
    #
#    desired_app = "slackbot_comments_move"
#    desired_task = "deny"
#    try:
#        decoded = jwt.decode (
#            authorization_token,
#            key,
#            algorithms=["RS256"]
#        )
#        logging.info("Valid JSON Web Token")
#    except:
#        logging.error("Invalid JSON Web Token")
#        htmlMsg = rds.generateHTMLErrorMessage("Invalid JSON Web Token")
#        return HTMLResponse(htmlMsg)
    #
    # Check to see if the JWT payload is valid
    #
#    if decoded["app"] != desired_app:
#        logging.error("Invalid app in JSON Web Token payload")
#        htmlMsg = rds.generateHTMLErrorMessage("Invalid app in JSON Web Token payload")
#        return HTMLResponse(htmlMsg)
#    else:
#        logging.info("JWT app = "+decoded['app'])
#    if decoded["task"] != desired_task:
#        logging.error("Invalid task in JSON Web Token payload")
#        htmlMsg = rds.generateHTMLErrorMessage("Invalid task in JSON Web Token payload")
#        return HTMLResponse(htmlMsg)
#    else:
#        logging.info("JWT task = "+decoded['task'])
    #
    # decode keys
    #
#    access, secret = get_info ( "info.conf" )
    #access = decoded["access"]
    #secret = decoded["secret"]
    #
    #  Access AWS Credentials and establish session as a client and resource
#    #
#    s3_client = s3f.credentials_client ( access, secret )
#    if s3_client == -1:
#        logging.error("Cannot connect to S3 as client")
#        htmlMsg = rds.generateHTMLErrorMessage("Cannot connect to S3 as client")
#        return HTMLResponse(htmlMsg)
#    s3_resource = s3f.credentials_resource ( access, secret )
#    if s3_resource == -1:
#        logging.error("Cannot connect to S3 as resource")
#        htmlMsg = rds.generateHTMLErrorMessage("Cannot connect to S3 as resource: "+access+" and "+secret)
#        return HTMLResponse(htmlMsg)
    #
    # To move a file: 1) copy the file to the given directory
    #
#    bucket = "gbads-comments"
#    srcFolder = "underreview/"
#    destFolder = "notapproved/"
#    sourceObj = srcFolder+comment_id
#    destObj = destFolder+comment_id
#    ret = s3f.s3Copy ( s3_client, bucket, sourceObj, destObj )
    #
    # Next: 2) delete the original file
    #
#    if ret == 0:
#        ret = s3f.s3Delete ( s3_client, bucket, sourceObj )
#        if ret == 0:
#            logging.info("S3 Deny successful")
#            htmlstring = "<html><body><H3>GBADs S3 Slack Deny Comment</h3></body></html>"
#            return HTMLResponse(htmlstring)
#        else:
#            logging.error("S3 Delete not successful")
#            htmlMsg = rds.generateHTMLErrorMessage("S3 Delete not successful")
#            return HTMLResponse(htmlMsg)
#    else:
#        logging.error("S3 Copy not successful")
#        htmlMsg = rds.generateHTMLErrorMessage("S3 Copy not successful")
#        return HTMLResponse(htmlMsg)

# This router allows a custom path to be used for the API
app.include_router(router)

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=9000)
