# from fastapi import FastAPI
# from app.api import agent, auth_routes, history_routes
# from fastapi.middleware.cors import CORSMiddleware
# app = FastAPI()

# app.add_middleware(
#     CORSMiddleware,
#     allow_origins=["http://localhost:5500", "http://127.0.0.1:5500"],
#     allow_credentials=True,
#     allow_methods=["*"],
#     allow_headers=["*"],
# )
# app.include_router(auth_routes.router, prefix="/auth")
# app.include_router(history_routes.router, prefix="/history")
# app.include_router(agent.router, prefix="/agent")


from fastapi import FastAPI, APIRouter
from fastapi.middleware.cors import CORSMiddleware
from app.api import agent, auth_routes, history_routes
import logging
import os
from dotenv import load_dotenv
import firebase_admin
from firebase_admin import credentials, auth
# Load .env file
load_dotenv()

cred = credentials.Certificate("chatbot-df6c2-firebase-adminsdk-fbsvc-f7f47d1f49.json")
firebase_admin.initialize_app(cred)
# cred = credentials.Certificate(os.getenv("GOOGLE_CREDENTIALS_PATH"))

# firebase_admin.initialize_app(cred)

# Check for API key
google_api_key = os.environ.get('GOOGLE_API_KEY')
if not google_api_key:
    print("⚠️ WARNING: GOOGLE_API_KEY not found in environment variables")
    print("Please set your Google API key in .env file")

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Import your router
from app.api.agent import router as agent_router
from app.api.history_routes import router as history_router  # Import router riwayat chat

# Create FastAPI app
app = FastAPI(
    title="Bali Travel Agent API",
    description="API untuk asisten wisata Bali menggunakan Google ADK",
    version="0.1.0"
)

# Setup CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # atau spesifik: ["http://localhost:5173"]
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routes
app.include_router(agent_router, prefix="/api")
app.include_router(auth_routes.router, prefix="/auth")
app.include_router(history_router, prefix="/api")  # Tambahkan router riwayat chat

# Root endpoint
@app.get("/")
async def root():
    return {
        "message": "Bali Travel Agent API is running",
        "api_key_configured": google_api_key is not None
    }

# Health check endpoint
@app.get("/health")
async def health_check():
    return {
        "status": "ok",
        "api_key_configured": google_api_key is not None
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)


# from fastapi import FastAPI, HTTPException, Request
# from pydantic import BaseModel
# from google.oauth2 import id_token
# from google.auth.transport import requests
# from pymongo import MongoClient
# from datetime import datetime
# from fastapi.middleware.cors import CORSMiddleware
# app = FastAPI()
# origins = [
#     "http://localhost:5500",
#     "http://127.0.0.1:5500",
#     # tambahkan domain lain jika perlu
# ]

# app.add_middleware(
#     CORSMiddleware,
#     allow_origins=origins,  # domain frontend yang diizinkan
#     allow_credentials=True,
#     allow_methods=["*"],    # izinkan semua method HTTP
#     allow_headers=["*"],    # izinkan semua headers
# )
# # Ganti dengan Google Client ID milikmu
# GOOGLE_CLIENT_ID = "1012341806322-on472qvgiii3k104bvrllockvfgv9mh8.apps.googleusercontent.com"

# # MongoDB Atlas connection
# client = MongoClient("mongodb+srv://masta:masta123@mastaverse.mqbexf4.mongodb.net/chatbot")
# db = client.chatbot
# users_collection = db.users
# history_collection = db.histories

# # Model untuk token dari frontend
# class TokenData(BaseModel):
#     token: str

# @app.post("/login")
# async def login(token_data: TokenData):
#     try:
#         # Verifikasi token dari Google
#         idinfo = id_token.verify_oauth2_token(token_data.token, requests.Request(), GOOGLE_CLIENT_ID)
        
#         google_id = idinfo["sub"]
#         user = {
#             "google_id": google_id,
#             "email": idinfo["email"],
#             "name": idinfo.get("name"),
#             "picture": idinfo.get("picture")
#         }

#         # Simpan user jika belum ada
#         users_collection.update_one({"google_id": google_id}, {"$set": user}, upsert=True)

#         return {"message": "Login success", "user": user}
#     except ValueError:
#         raise HTTPException(status_code=401, detail="Invalid token")

# @app.post("/chat")
# async def chat(request: Request):
#     data = await request.json()
#     user_id = data["user_id"]  # google_id
#     user_message = data["message"]

#     # Simulasi jawaban bot
#     bot_reply = f"Halo, kamu bilang: {user_message}"

#     # Simpan histori
#     history_collection.insert_one({
#         "user_id": user_id,
#         "messages": [
#             {"from": "user", "text": user_message},
#             {"from": "bot", "text": bot_reply}
#         ],
#         "timestamp": datetime.utcnow()
#     })

#     return {"reply": bot_reply}


