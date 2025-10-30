from pymongo import MongoClient
import os

MONGO_URI = os.getenv(
    "MONGO_URI",
    "mongodb+srv://username:password@cluster0.mongodb.net/dbname?retryWrites=true&w=majority"
)
client = MongoClient(MONGO_URI)
db = client["trip_room_db"]
users = db["users"]
rooms = db["rooms"]
schedules = db["schedules"]
