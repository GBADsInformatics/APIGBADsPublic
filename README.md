# API_GBADsPublic
RDS library routines and API functions to access the public GBADs database tables on AWS RDS

### Starting the Virtual environment
To create:
```
python3.9 -m venv env
```
To activate:
```
source env/bin/activate
```

### Install the Python Dependencies :package:
```
pip3 install -r requirements/requirements.txt
```

### Running the API (Development) :running_woman:
```
uvicorn main:app --reload
```

### Accessing the API :technologist:
To access the API in your web browser start with the command:\
http://localhost:9000/dataportal/


### Running in Docker (Production) :sailboat:
run `docker run -d -p 9000:8000 gbadsinformatics/api`
You can access it at port 8000 of your machine. (change the '9000' to run the api on a different port)


### How to Use the Postman Test Runner
It's a postman collection that runs in the postman application. It can be downloaded from
https://www.postman.com

Once installed, run the application and select the import button in the top right of the application. Select the postman collection .json file.

To run it select the collection under the 'Collections' tab and then select the 'Run' button in the top right of the application. This will run all the tests in the collection.

** Note this is basic and just ensures that the APIs are running and arent failing due to a code error. It does not test the data returned by the APIs. **

### S3 Additions
Now you can do actions on the GBADs S3 Storage:
   1. /slack/approve - move file from underreview/ to approved/ - for the Comments Slackbot system
   2. /slack/deny - move file from underreview/ to notapproved/ - for the Comments Slackbot system
   3. /slack/download - download file from S3 storage to local storage - To Be Developed
   4. /slack/upload - upload file from local storage to S3 storage- To Be Developed

#### Example Calls From each API
1. ```http://localhost:9000/GBADsTables/public?format=html```
2. ```http://localhost:9000/GBADsTable/public?table_name=livestock_production_faostat&format=html```
3. ```http://localhost:9000/GBADsPublicQuery/livestock_production_faostat?fields=country,year,species,population&query=year=2017%20AND%20species=%27Goats%27&format=html```
4. ```http://localhost:9000/GBADsLivestockPopulation/oie?year=*&country=Canada&species=Cattle&format=html```
5. ```http://localhost:9000/slack/approve/2023-06-22 12:05:21.077294.json?authorization_token=lsjlsdfjaljdflajsdfljalsdfjlad```
5. ```http://localhost:9000/slack/deny/2023-06-22 12:05:21.077294.json?authorization_token=lsjlsdfjaljdflajsdfljalsdfjlad```

