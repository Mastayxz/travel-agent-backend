from fastapi import FastAPI, HTTPException, Request, APIRouter
from pydantic import BaseModel
from google.oauth2 import id_token
from google.auth.transport import requests
from pymongo import MongoClient
from datetime import datetime
from fastapi.middleware.cors import CORSMiddleware
# config.py
import os
from dotenv import load_dotenv

load_dotenv()  # load file .env

router = APIRouter()
# origins = [
#     "http://localhost:5500",
#     "http://127.0.0.1:5500",
#     # tambahkan domain lain jika perlu
# ]

# router.add_middleware(
#     CORSMiddleware,
#     allow_origins=origins,  # domain frontend yang diizinkan
#     allow_credentials=True,
#     allow_methods=["*"],    # izinkan semua method HTTP
#     allow_headers=["*"],    # izinkan semua headers
# )
# Ganti dengan Google Client ID milikmu
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
MONGO_URI = os.getenv("MONGO_URI")
# MongoDB Atlas connection
client = MongoClient(MONGO_URI)
db = client.chatbot
users_collection = db.users
history_collection = db.histories

# Model untuk token dari frontend
class TokenData(BaseModel):
    token: str

@router.post("/login")
async def login(token_data: TokenData):
    try:
        # Verifikasi token dari Google
        idinfo = id_token.verify_oauth2_token(token_data.token, requests.Request(), GOOGLE_CLIENT_ID)
        
        google_id = idinfo["sub"]
        user = {
            "google_id": google_id,
            "email": idinfo["email"],
            "name": idinfo.get("name"),
            "picture": idinfo.get("picture")
        }

        # Simpan user jika belum ada
        users_collection.update_one({"google_id": google_id}, {"$set": user}, upsert=True)

        return {"message": "Login success", "user": user}
    except ValueError:
        raise HTTPException(status_code=401, detail="Invalid token")