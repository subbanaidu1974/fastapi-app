# db.py
from pymongo import MongoClient
import os
from dotenv import load_dotenv
from utils.constants import MONGO_URI, MONGO_APIKEY_COLLECTION_NAME, MONGO_APIKEY_DBNAME,MONGO_STATS_COLLECTION_NAME

load_dotenv()

# Connect to MongoDB
client = MongoClient(MONGO_URI)
db = client[MONGO_APIKEY_DBNAME]
keys_collection = db[MONGO_APIKEY_COLLECTION_NAME]
usage_collection = db[MONGO_STATS_COLLECTION_NAME]