
CENSUS_BASE_URL = "https://api.census.gov/data"
URL_PATH = "/2023/acs/acs5"
CENSUS_URL = CENSUS_BASE_URL + URL_PATH
    

API_KEY_NAME = "x-api-key"
MONGO_URI = "mongodb://mongo:27017"
MONGO_APIKEY_DBNAME = "fastapi_keys"
MONGO_APIKEY_COLLECTION_NAME = "apikeys"
# Allowed IPs for docs (e.g. localhost only)
ALLOWED_DOC_IPS = {"127.0.0.1", "::1"}