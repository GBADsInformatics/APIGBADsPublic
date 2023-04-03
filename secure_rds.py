#
# Connect to the public or private GBADs database in READONLY mode
#
#    Connection parameters include:
#       host = database location in AWS which is gbadske-database-public-data.cp73fx22weet.ca-central-1.rds.amazonaws.com
#       dbname = name of the database which is publicData_1 since this database will contain public data
#       user = readonly database user "reader"
#       password = password for reader is "readonly"
#
#    Author: Deb Stacey
#
#    Date of last update: April 3, 2023
#
#    Usage: import secure_rds as secure
#           conn = secure.connect_public()
#           conn = secure.connect_private()
#
#
# Libraries
#
import psycopg2 as ps
#
def connect_public():    
#
# Create connection and cursor
#
    conn = ps.connect("host=gbadske-database-public-data.cp73fx22weet.ca-central-1.rds.amazonaws.com dbname=publicData_1 user=reader password=readonly")
# 
# Return connection information
#
    return conn
#
# End of function connect_public()
#

#
def connect_private():    
#
# Create connection and cursor
#
    conn = ps.connect("host=gbadske-database-private-data.cp73fx22weet.ca-central-1.rds.amazonaws.com dbname=privateData_1 user=reader password=readonly")
# 
# Return connection information
#
    return conn
#
# End of function connect_private()
#

