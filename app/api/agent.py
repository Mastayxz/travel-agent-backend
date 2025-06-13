from fastapi import APIRouter, HTTPException, Request, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from typing import Optional
import os
import traceback
import logging
import uuid
from datetime import datetime

from google.oauth2 import id_token
from google.auth.transport import requests as google_requests
from google.genai import types
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from typing import List
import firebase_admin
from firebase_admin import auth as firebase_auth
# Import travel agent
from agents.travel_agent import travel_agent

# Import history model & MongoDB collection
from app.models.history import ChatHistory, Message
from app.db import history_collection

# Setup logging
logger = logging.getLogger(__name__)

# Init router
router = APIRouter()

# Setup security scheme (for Swagger + Bearer token)
security = HTTPBearer()

# ====== VERIFIKASI GOOGLE TOKEN ======
async def verify_google_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    token = credentials.credentials
    try:
        id_info = id_token.verify_oauth2_token(token, google_requests.Request())
        return {
            "email": id_info.get("email"),
            "name": id_info.get("name"),
            "picture": id_info.get("picture"),
            "sub": id_info.get("sub")
        }
    except Exception as e:
        logger.error(f"Token verification failed: {str(e)}")
        raise HTTPException(status_code=401, detail="Token tidak valid atau kadaluarsa")



async def verify_firebase_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    token = credentials.credentials
    try:
        decoded_token = firebase_auth.verify_id_token(token)
        return {
            "email": decoded_token.get("email"),
            "name": decoded_token.get("name"),
            "picture": decoded_token.get("picture"),
            "uid": decoded_token.get("uid")
        }
    except Exception as e:
        logger.error(f"Firebase token verification failed: {str(e)}")
        raise HTTPException(status_code=401, detail="Token tidak valid atau kadaluarsa")
# Dummy content types
class QueryInput(BaseModel):
    email: str
    query: str
    session_id: Optional[str] = None


@router.post("/ask")
async def ask_agent(
    data: QueryInput,
    user_data: dict = Depends(verify_firebase_token)  # ganti di sini
):
    if data.email != user_data["email"]:
        raise HTTPException(status_code=401, detail="Email tidak cocok dengan token")

    try:
        logger.info(f"Processing query: {data.query} dari user: {user_data.get('name')}")

        # Ambil histori chat
        session_id = data.session_id or str(uuid.uuid4())
        existing_chat = history_collection.find_one({
            "firebase_uid": user_data["uid"], 
            "session_id": session_id
        })

        chat_history: List[types.Content] = []

        if existing_chat:
            for msg in existing_chat["messages"]:
                chat_history.append(
                    types.Content(
                        role=msg["role"],
                        parts=[types.Part(text=msg["content"])]
                    )
                )

        # Tambahkan pesan user terbaru ke dalam history
        chat_history.append(
            types.Content(
                role="user",
                parts=[types.Part(text=data.query)]
            )
        )

        # Siapkan runner dan session
        session_service = InMemorySessionService()
        session = await session_service.create_session(
            app_name="bali_travel_guide",
            user_id=data.email
        )

        runner = Runner(
            agent=travel_agent,
            session_service=session_service,
            app_name="bali_travel_guide"
        )
        context_text = ""
        for content in chat_history:
            role = content.role
            for part in content.parts:
                context_text += f"{role}: {part.text}\n"

        new_message = types.Content(
            role="user",
            parts=[types.Part(text=context_text)]
        )

        result = ""
        async for event in runner.run_async(
            session_id=session.id,
            user_id=data.email,
            new_message=new_message  # KIRIM CONTENT BUKAN LIST
        ):
    

            if hasattr(event, 'is_final_response') and event.is_final_response:
                if hasattr(event, 'content') and hasattr(event.content, 'parts'):
                    for part in event.content.parts:
                        if hasattr(part, 'text') and part.text:
                            result += part.text

        # Simpan pesan user dan agent ke history
        user_message = Message(
            role="user",
            content=data.query,
            timestamp=datetime.utcnow()
        )

        agent_message = Message(
            role="agent",
            content=result,
            timestamp=datetime.utcnow()
        )

        if existing_chat:
             history_collection.update_one(
                {"firebase_uid": user_data["uid"], "session_id": session_id},
                {
                    "$push": {
                        "messages": {
                            "$each": [user_message.dict(), agent_message.dict()]
                        }
                    },
                    "$set": {"timestamp": datetime.utcnow()}
                }
            )
        else:
            new_history = ChatHistory(
                firebase_uid=user_data["uid"],
                session_id=session_id,
                messages=[user_message, agent_message],
                timestamp=datetime.utcnow()
            )
            history_collection.insert_one(new_history.dict())

        return {
            "user_name": user_data.get("name"),
            "email": data.email,
            "query": data.query,
            "response": result,
            "session_id": session_id
        }

    except Exception as e:
        logger.error(f"Agent failed to respond.")
        logger.error(f"Error: {str(e)}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Gagal memproses permintaan: {str(e)}")



# # ====== ROUTE UTAMA /ASK ======
# @router.post("/ask")
# async def ask_agent(
#     data: QueryInput,
#     user_data: dict = Depends(verify_google_token)
# ):
#     if data.email != user_data["email"]:
#         raise HTTPException(status_code=401, detail="Email tidak cocok dengan token")

#     # Filter query: hanya menerima query yang mengandung "bali"
#     if "bali" not in data.query.lower():
#         return {"response": "Maaf, saya hanya bisa menjawab pertanyaan seputar Bali."}

#     try:
#         logger.info(f"Processing query: {data.query} dari user: {user_data['name']}")

#         # Setup session dengan InMemorySessionService (jangan bikin baru terus, idealnya disimpan di luar fungsi)
#         session_service = InMemorySessionService()
#         session = session_service.create_session(
#             app_name="bali_travel_guide",
#             user_id=data.email
#         )

#         runner = Runner(
#             agent=travel_agent,
#             session_service=session_service,
#             app_name="bali_travel_guide"
#         )

#         content = types.Content(
#             role='user',
#             parts=[types.Part(text=data.query)]
#         )

#         result = ""

#         # Jalankan agent dan kumpulkan response
#         async for event in runner.run_async(
#             session_id=session.id,
#             user_id=data.email,
#             new_message=content
#         ):
#             if hasattr(event, 'is_final_response') and event.is_final_response:
#                 if hasattr(event, 'content') and hasattr(event.content, 'parts'):
#                     for part in event.content.parts:
#                         if hasattr(part, 'text') and part.text:
#                             result += part.text

#         # Gunakan session_id yang dikirim, atau buat baru kalau kosong
#         session_id = data.session_id or str(uuid.uuid4())

#         user_message = Message(
#             role="user",
#             content=data.query,
#             timestamp=datetime.utcnow()
#         )

#         agent_message = Message(
#             role="agent",
#             content=result,
#             timestamp=datetime.utcnow()
#         )

#         # Cari history chat yang sudah ada berdasarkan google_id dan session_id
#         existing_chat = history_collection.find_one({
#             "google_id": user_data["sub"],
#             "session_id": session_id
#         })

#         if existing_chat:
#             # Update history: push user & agent message ke array messages dengan $each supaya flat array
#             history_collection.update_one(
#                 {"google_id": user_data["sub"], "session_id": session_id},
#                 {
#                     "$push": {
#                         "messages": {
#                             "$each": [user_message.dict(), agent_message.dict()]
#                         }
#                     },
#                     "$set": {"timestamp": datetime.utcnow()}
#                 }
#             )
#         else:
#             # Kalau belum ada history, buat baru
#             new_history = ChatHistory(
#                 google_id=user_data["sub"],
#                 session_id=session_id,
#                 messages=[user_message, agent_message],
#                 timestamp=datetime.utcnow()
#             )
#             history_collection.insert_one(new_history.dict())

#         # Return response plus session_id untuk dipakai terus kalau mau lanjut chat
#         return {
#             "user_name": user_data["name"],
#             "email": data.email,
#             "query": data.query,
#             "response": result,
#             "session_id": session_id
#         }

#     except Exception as e:
#         logger.error(f"Error: {str(e)}")
#         logger.error(traceback.format_exc())
#         raise HTTPException(status_code=500, detail=f"Gagal memproses permintaan: {str(e)}")

# # ====== DEBUGGING ENDPOINT ======
# @router.post("/debug")
# async def debug_request(request: Request):
#     body = await request.json()
#     return {
#         "received": body,
#         "google_api_key_set": "GOOGLE_API_KEY" in os.environ,
#         "travel_agent_type": str(type(travel_agent))
#     }