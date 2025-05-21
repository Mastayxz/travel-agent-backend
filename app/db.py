from motor.motor_asyncio import AsyncIOMotorClient
from pymongo import MongoClient
from app.config import MONGO_DETAILS, DATABASE_NAME
client = MongoClient("mongodb+srv://masta:masta123@mastaverse.mqbexf4.mongodb.net/chatbot")
db = client.chatbot
users_collection = db.users
history_collection = db.histories
# user_collection = database.get_collection("users")
# history_collection = database.get_collection("histories")
# preference_collection = database.get_collection("preferences")
