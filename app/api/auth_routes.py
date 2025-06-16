from fastapi import FastAPI, HTTPException, Request, APIRouter
from pydantic import BaseModel, EmailStr, validator  
from google.oauth2 import id_token
from google.auth.transport import requests
from pymongo import MongoClient
from datetime import datetime
from fastapi.middleware.cors import CORSMiddleware
# config.py
import os
from dotenv import load_dotenv
from firebase_admin import auth as firebase_auth

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
        # Verifikasi ID token dari Firebase
        decoded_token = firebase_auth.verify_id_token(token_data.token)
        email = decoded_token["email"]
        uid = decoded_token["uid"]
        name = decoded_token.get("name")
        picture = decoded_token.get("picture")

        user = {
            "firebase_uid": uid,
            "email": email,
            "name": name,
            "picture": picture
        }

        # Simpan user jika belum ada
        users_collection.update_one({"firebase_uid": uid}, {"$set": user}, upsert=True)

        return {"message": "Login success", "user": user}
    except Exception as e:
        raise HTTPException(status_code=401, detail="Invalid Firebase token")
    
class RegisterData(BaseModel):
    email: EmailStr
    password: str
    name: str = None  # Optional

@router.post("/register")
async def register(token_data: TokenData):
    try:
        # Verifikasi ID token Firebase dari frontend
        decoded_token = firebase_auth.verify_id_token(token_data.token)
        email = decoded_token["email"]
        uid = decoded_token["uid"]
        name = decoded_token.get("name") or email.split("@")[0]
        picture = decoded_token.get("picture", "")

        user = {
            "firebase_uid": uid,
            "email": email,
            "name": name,
            "picture": picture,
        }

        # Simpan user jika belum ada
        users_collection.update_one(
            {"firebase_uid": uid},
            {"$setOnInsert": user},
            upsert=True
        )

        return {"message": "Register success", "user": user}
    except Exception as e:
        raise HTTPException(status_code=401, detail="Invalid Firebase token")
