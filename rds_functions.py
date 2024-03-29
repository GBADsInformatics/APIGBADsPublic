#
#   Functions to perform Postgres database functions on AWS RDS
#
#   Author: Deb Stacey, Ian McKechnie
#
#   Date of last update: Dec 3, 2022
#

#
# Libraries
#
# import psycopg2 as ps
from typing import Optional


#
#  Functions
#


#
# displayTables returns the names of the tables that are in the GBADs AWS RDS Postgres database
#    Parameter(s): pointer to database generated by psycopg2
#    Returns: table names
#
def displayTables(cur):
    cur.execute(
        "SELECT table_schema,table_name FROM information_schema.tables WHERE table_schema='public' ORDER BY table_schema,table_name ;"
    )
    tables = cur.fetchall()
    return tables


#
# displayTabInfo returns the column names and datatypes of a given table that is in the GBADs AWS RDS Postgres database
#    Parameter(s): pointer to database generated by psycopg2, table name
#    Returns: column names and datatypes
#
def displayTabInfo(cur, table_name):
    cur.execute(
        "SELECT column_name,data_type FROM information_schema.columns WHERE table_name='%s';"
        % (table_name)
    )
    response = cur.fetchall()
    return response


#
# checkTable checks if the table is in the database
#    Parameter(s): pointer to database generated by psycopg2, table name
#    Returns: 1 if table is in the database and 0 if it is not
#
def checkTable(cur, table_name):
    cur.execute(
        "SELECT table_schema,table_name FROM information_schema.tables WHERE table_schema='public' ORDER BY table_schema,table_name ;"
    )
    tabs = cur.fetchall()
    if any(table_name in i for i in tabs):
        ret_flag = 1
    else:
        ret_flag = 0
    return ret_flag


#
# checkDataFields checks if the fields chosen to query on are valid
#    Parameter(s): pointer to database generated by psycopg2, table name, string with comma seperated field/column names
#    Returns: 1 if every field checks out and 0 otherwise
#
def checkDataFields(cur, table_name, fieldstring):
    cur.execute(
        "SELECT column_name FROM information_schema.columns WHERE table_name=%s;"
        % (table_name)
    )
    # cur.execute(f"""SELECT column_name FROM information_schema.columns WHERE table_name='{table_name}' ;""")
    fields_list = cur.fetchall()
    ret = 0
    flist = fieldstring.split(",")
    num = len(flist)
    for fname in flist:
        if any(fname in i for i in fields_list):
            ret = ret + 1
        else:
            ret = ret + 0
    if ret - num == 0:
        ret = 1
    else:
        ret = 0
    return ret


#
# setJoin defines the tables that are to be joined and the fields that are in the join
#    Parameter(s): table1 name, table2 name, field1 name, field2 name
#    Returns: join string ( string to be sent to the query builder )
#
def setJoin(table_name1, table_name2, jfield_1, jfield_2):
    jstring = f"""FROM {table_name1} INNER JOIN {table_name2} ON {table_name1}.{jfield_1}={table_name2}.{jfield_2}"""
    return jstring


#
# The query method. Queries the database and returns the answer
#   Parameter(s): Cursor pointer to database generated by psycopg2, table_name name of table, selectstring: Query string, joinstring, order: order by value
#   Returns: The answer to the query
#
def query(
    cursor, table_name, selectstring, wherestring, joinstring, order: Optional[str] = ""
):
    if wherestring == "":
        if joinstring == "":
            if order != "":
                cursor.execute(
                    "SELECT %s FROM %s ORDER BY %s" % (selectstring, table_name, order)
                )
            else:
                cursor.execute("SELECT %s FROM %s" % (selectstring, table_name))
        else:
            if order != "":
                cursor.execute(
                    "SELECT %s %s ORDER BY %s" % (selectstring, joinstring, order)
                )
            else:
                cursor.execute("SELECT %s %s " % (selectstring, joinstring))
    else:
        if joinstring == "":
            if order != "":
                cursor.execute(
                    "SELECT %s FROM %s WHERE %s ORDER BY %s"
                    % (selectstring, table_name, wherestring, order)
                )
            else:
                cursor.execute(
                    "SELECT %s FROM %s WHERE %s"
                    % (selectstring, table_name, wherestring)
                )
        else:
            if order != "":
                cursor.execute(
                    "SELECT %s %s WHERE %s ORDER BY %s"
                    % (selectstring, joinstring, wherestring, order)
                )
            else:
                cursor.execute(
                    "SELECT %s %s WHERE %s" % (selectstring, joinstring, wherestring)
                )

    answer = cursor.fetchall()
    return answer


#
# The countQuery method. Queries the database to retrieve the number of records
#   Parameter(s): Cursor pointer to database generated by psycopg2, table_name name of table, selectstring: Query string, joinstring, order: order by value
#   Returns: The answer to the query
#
def countQuery(
    cursor, table_name, selectstring, wherestring, joinstring, order: Optional[str] = ""
):
    if wherestring == "":
        if joinstring == "":
            if order != "":
                cursor.execute(
                    "SELECT count(*) FROM %s ORDER BY %s" % (table_name, order)
                )
            else:
                cursor.execute("SELECT count(*) FROM %s" % (table_name))
        else:
            if order != "":
                cursor.execute(
                    "SELECT %s %s ORDER BY %s" % (selectstring, joinstring, order)
                )
            else:
                cursor.execute("SELECT %s %s " % (selectstring, joinstring))
    else:
        if joinstring == "":
            if order != "":
                cursor.execute(
                    "SELECT count(*) FROM %s WHERE %s ORDER BY %s"
                    % (table_name, wherestring, order)
                )
            else:
                cursor.execute(
                    "SELECT count(*) FROM %s WHERE %s" % (table_name, wherestring)
                )
        else:
            if order != "":
                cursor.execute(
                    "SELECT %s %s WHERE %s ORDER BY %s"
                    % (selectstring, joinstring, wherestring, order)
                )
            else:
                cursor.execute(
                    "SELECT %s %s WHERE %s" % (selectstring, joinstring, wherestring)
                )

    answer = cursor.fetchall()
    return answer


#
# setQuery builds a query that's returned in the html
#    Parameter(s): string of fields to be retrieved, query string, join string
#    Returns: completed query string
#
def setQuery(table_name, fields, query, joinstring):
    if query == "":
        if joinstring == "":
            querystring = f"""SELECT {fields} FROM {table_name}"""
        else:
            querystring = f"""SELECT {fields} {joinstring}"""
    else:
        if joinstring == "":
            querystring = f"""SELECT {fields} FROM {table_name} WHERE {query}"""
        else:
            querystring = f"""SELECT {fields} {joinstring} WHERE {query}"""
    return querystring


#
# setCountQuery builds a query to be sent to the database to retrieve the number of records
#    that match the query
#    Parameter(s): string of fields to be retrieved, query string, join string
#    Returns: completed query
#
def setCountQuery(table_name, selectstring, wherestring, joinstring):
    if wherestring == "":
        if joinstring == "":
            querystring = f"""SELECT count(*) FROM {table_name}"""
        else:
            querystring = f"""SELECT {selectstring} {joinstring}"""
    else:
        if joinstring == "":
            querystring = f"""SELECT count(*) FROM {table_name} WHERE {wherestring}"""
        else:
            querystring = f"""SELECT {selectstring} {joinstring} WHERE {wherestring}"""
    return querystring


#
# execute runs the query against the database
#    Parameter(s): pointer to database generated by psycopg2, query string
#    Returns: answer to the query
#
def execute(cur, querystring):
    cur.execute(f"""{querystring}""")
    answer = cur.fetchall()
    return answer


def generateFieldNames(cur, tablename):
    cur.execute("SELECT * FROM %s" % (tablename))
    # rows = cur.fetchone()
    colunmnames = [desc[0] for desc in cur.description]
    return colunmnames


# Error message for bad query
def generateHTMLErrorMessage(msg):
    html = (
        """ <!DOCTYPE html>
        <html>
        <head>
        <title>
        Error</title>
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <style>
        body {background-color:#ffffff;background-repeat:no-repeat;background-position:top left;background-attachment:fixed;}
        h1{font-family:Arial, sans-serif;color:#000000;background-color:#ffffff;}
        p {font-family:Georgia, serif;font-size:14px;font-style:normal;font-weight:normal;color:#000000;background-color:#ffffff;}
        </style>
        </head>
        <body>
        <h1>Error</h1>
        <p>"""
        + msg
        + """</p>
        </body>
        </html>"""
    )

    return html


#
#   End of rds_functions.py
#
