# GBADs Public API
Get started with our [GBADs API Swagger Docs](https://gbadske.org/api/docs)

This is our API for accessing GBADs public database tables and supporting functionality of our other apps.

## Contribution Guidelines
- Create unit tests for new code you write!
- Create a new Adapter (with reusable functions) when integrating with a new external source
- Create a new endpoints file when working on a new set of endpoints.
- Merge into master with pull requests - get your code reviewed if possible.

## API File Structure
```
📦 APIGBADsPublic/
 ├── .aws/                          # AWS Resources
 ├── .github/                       # CI/CD Pipelines
 ├── app/                           # Application Code
 │   ├── api/v1/                    # API Routes - BUSINESS LOGIC GOES HERE
 │   │   ├── engine_endpoints.py    # Database endpoints
 │   │   ├── dpm_endpoints.py       # DPM & S3 endpoints
 │   │   └── comments_endpoints.py  # Dashboard comment endpoints
 │   ├── adapters/                  # Adapters - CODE FOR INTERACTING WITH EXTERNAL SYSTEMS GOES HERE
 │   │   ├── rds_adapter.py         # RDS Functions
 │   │   └── s3_adapter.py          # S3 Functions
 │   ├── models/                    # Data models
 │   ├── public/                    # Static files - html, public keys
 │   ├── utils/                     # Utilities - Helpers, auth lib, etc.
 │   └── main.py                    # main
 ├── requirements/                  # Python dependencies
 │   └── requirements.txt           #
 ├── tests/                         # Test suite
 ├── Dockerfile                     # Container configuration
 ├── README.md                      # Project documentation
 └── ...                            # Other files (config, scripts, etc.)
```

## Developing Locally :computer:
### Starting the Virtual Environment :floppy_disk:
To create:
```bash
python3 -m venv env
```
To activate:
```bash
source env/bin/activate
```

or

```bash
env\Scripts\activate
```

### Install the Python Dependencies :package:
```bash
pip3 install -r requirements/requirements.txt
pip3 install -r requirements/requirements-tests.txt # if running tests/linting
```

### Running the API for Development :running_woman:
> You only need to load the variables depending on the endpoint(s) you'll be working on.

Load these if you'll be running the Knowledge Engine database endpoints
```bash
export RDS_HOST=rds_host_here
export RDS_USER=rds_username_here
export RDS_PASS=rds_password_here
```
Load these if you'll be running the DPM or Comments Endpoints
```bash
export S3_USER_ACCESS_KEY_ID=aws_key
export S3_USER_SECRET_ACCESS_KEY=aws_secret_key
export S3_USER_REGION=ca-central-1
```
Start the API
```bash
uvicorn app.main:app --reload --port 8000
```

### Accessing the API :technologist:
Access the API in your web browser here:\
http://localhost:8000/docs

### Running Code Linter Locally :mag:
> To avoid being blocked by the pipeline, run the linter and tests locally.
```bash
pylint app/
```

or

```bash
python -m pylint app/
```

### Running Unit Tests Locally :triangular_flag_on_post:
```bash
pytest .
```

or

```bash
python -m pytest .
```

### Running the API in Docker :sailboat:
run:
```bash
docker run -it
   -e BASE_URL="/api"
   -e S3_USER_ACCESS_KEY_ID="aws_key"
   -e S3_USER_SECRET_ACCESS_KEY="aws_secret"
   -e S3_USER_REGION="ca-central-1"
   -e RDS_HOST="sql_host_here"
   -e RDS_NAME="sql_db_name"
   -e RDS_USER="sql_user"
   -e RDS_PASS="sql_pass"
   -p 8000:80
   gbadsinformatics/api
```
You can access it at port 8000 of your machine behind the BASE_URL. http://localhost:8000/api/docs

## Other
### How to Use the Postman Test Runner
It's a postman collection that runs in the postman application. It can be downloaded from
https://www.postman.com

Once installed, run the application and select the import button in the top right of the application. Select the postman collection .json file.

To run it select the collection under the 'Collections' tab and then select the 'Run' button in the top right of the application. This will run all the tests in the collection.

** Note this is basic and just ensures that the APIs are running and arent failing due to a code error. It does not test the data returned by the APIs. **

#### Example Calls for the API
1. ```http://localhost:8000/GBADsTables/public?format=html```
2. ```http://localhost:8000/GBADsTable/public?table_name=livestock_production_faostat&format=html```
3. ```http://localhost:8000/GBADsPublicQuery/livestock_production_faostat?fields=country,year,species,population&query=year=2017%20AND%20species=%27Goats%27&format=html```
4. ```http://localhost:8000/GBADsPublicQuery/biomass_oie?fields=%2A&query=animal_category%3D%27Bovine%27%20AND%20member_country%3D%27Canada%27&join=biomass_oie%2Ccountries_geo_area%2Cmember_country%2Ccountry&format=html&count=no```
5. ```http://localhost:8000/GBADsLivestockPopulation/oie?year=*&country=Canada&species=Cattle&format=html```
6. ```http://localhost:8000/slack/approve/2023-06-22 12:05:21.077294.json?authorization_token=lsjlsdfjaljdflajsdfljalsdfjlad```
7. ```http://localhost:8000/slack/deny/2023-06-22 12:05:21.077294.json?authorization_token=lsjlsdfjaljdflajsdfljalsdfjlad```

