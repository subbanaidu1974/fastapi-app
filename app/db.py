# db.py
from pymongo import MongoClient
import os
from dotenv import load_dotenv

load_dotenv()

# client = MongoClient(os.getenv("MONGO_URI"))
# db = client[os.getenv("DB_NAME")]
# api_keys_collection = db["api_keys"]

from utils.constants import MONGO_URI, MONGO_APIKEY_COLLECTION_NAME, MONGO_APIKEY_DBNAME

# Connect to MongoDB
client = MongoClient(MONGO_URI)
db = client[MONGO_APIKEY_DBNAME]
keys_collection = db[MONGO_APIKEY_COLLECTION_NAME]