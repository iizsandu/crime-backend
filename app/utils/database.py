import os
from pymongo import MongoClient
from dotenv import load_dotenv

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '../..' ,'info.env'))

MONGO_URI = os.getenv("MONGO_URI")
MONGO_DB = os.getenv("MONGO_DB")
MONGO_COLLECTION = os.getenv("MONGO_COLLECTION")
REPORT_COLLECTION = os.getenv("REPORT_COLLECTION")

client = MongoClient(MONGO_URI)
db = client[MONGO_DB]
crime_collection = db[MONGO_COLLECTION]
report_collection = db[REPORT_COLLECTION]