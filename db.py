from pymongo import MongoClient
from dotenv import load_dotenv
import gridfs
import os

load_dotenv()
MONGO_PW = os.getenv("MONGO_PW")

MONGO_URI = os.getenv(
    "MONGO_URI",
    f"mongodb+srv://somsumun_db_user:{MONGO_PW}@cluster0.3liugev.mongodb.net/?appName=Cluster0"
)

client = MongoClient(MONGO_URI)
db = client["trip_room_db"]
fs = gridfs.GridFS(db)
users = db["users"]
rooms = db["rooms"]
schedules = db["schedules"]
