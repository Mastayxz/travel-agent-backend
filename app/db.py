from motor.motor_asyncio import AsyncIOMotorClient
from pymongo import MongoClient
from app.config import MONGO_URI, DATABASE_NAME
import os
from dotenv import load_dotenv

load_dotenv()  
client = MongoClient(MONGO_URI)
db = client.chatbot
users_collection = db.users
history_collection = db.histories
# user_collection = database.get_collection("users")
# history_collection = database.get_collection("histories")
# preference_collection = database.get_collection("preferences")
