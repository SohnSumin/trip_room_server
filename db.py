from pymongo import MongoClient
import gridfs
import os

MONGO_URI = os.getenv(
    "MONGO_URI",
    "mongodb+srv://somsumun_db_user:4icsvnpMW7hnlX0M@cluster0.3liugev.mongodb.net/?appName=Cluster0"
)
client = MongoClient(MONGO_URI)
db = client["trip_room_db"]
fs = gridfs.GridFS(db) # GridFS 인스턴스 생성
users = db["users"]
rooms = db["rooms"]
schedules = db["schedules"]
