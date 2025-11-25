from pymongo import MongoClient
from dotenv import load_dotenv
import gridfs
import os

load_dotenv()
MONGO_PW = os.getenv("MONGO_PW") # MONGO_URI가 없을 경우 기본 URI를 생성하는데 사용

MONGO_URI = os.getenv(
    "MONGO_URI",
    f"mongodb+srv://somsumun_db_user:{MONGO_PW}@cluster0.3liugev.mongodb.net/?appName=Cluster0"
)

client = MongoClient(MONGO_URI)
db = client["trip_room_db"]
fs = gridfs.GridFS(db) # GridFS 인스턴스 생성
users = db["users"]
rooms = db["rooms"]
schedules = db["schedules"]
