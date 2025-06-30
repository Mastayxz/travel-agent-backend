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
import re
import base64
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



from fastapi import FastAPI, UploadFile, File, Form
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import os
from dotenv import load_dotenv
import google.generativeai as genai

@router.post("/ask")
async def ask_agent(
    request: Request,
    email: Optional[str] = Form(None),
    query: Optional[str] = Form(None),
    session_id: Optional[str] = Form(None),
    file: Optional[UploadFile] = File(None),
    user_data: dict = Depends(verify_firebase_token)
):
    try:
        content_type = request.headers.get("content-type", "")

        # Handle application/json request
        if "application/json" in content_type:
            data = await request.json()
            email = data.get("email")
            query = data.get("query")
            session_id = data.get("session_id")

        # Validasi input
        if not email or not query:
            raise HTTPException(status_code=400, detail="Email dan query wajib diisi.")

        # Validasi email
        if email != user_data["email"]:
            raise HTTPException(status_code=401, detail="Email tidak cocok dengan token")

        logger.info(f"Processing query: {query} dari user: {user_data.get('name')}")

        session_id = session_id or str(uuid.uuid4())

        # Ambil histori lama
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

        # Tambahkan pesan user (dengan atau tanpa gambar)
        if file:
            contents = await file.read()

            # ✅ Encode image ke base64
            base64_image = base64.b64encode(contents).decode("utf-8")

            image_parts = [types.Part(
                inline_data=types.Blob(
                    mime_type=file.content_type,
                    data=contents
                )
            )]

            image_prompt = types.Part(text="""
            Kamu adalah pemandu wisata ahli yang bisa mengenali destinasi dari gambar.
            Analisis gambar ini untuk memberikan informasi wisata yang relevan di Bali.
            """)

            chat_history.append(
                types.Content(
                    role="user",
                    parts=[image_prompt] + image_parts + [types.Part(text=query)]
                )
            )
        else:
            base64_image = None
            chat_history.append(
                types.Content(
                    role="user",
                    parts=[types.Part(text=query)]
                )
            )

        # Jalankan agent
        session_service = InMemorySessionService()
        session = session_service.create_session(
            app_name="bali_travel_guide",
            user_id=email
        )
        

        runner = Runner(
            agent=travel_agent,
            session_service=session_service,
            app_name="bali_travel_guide"
        )
                # Siapkan konteks dalam bentuk teks (dari riwayat sebelumnya)
        context_text = ""
        for content in chat_history[:-1]:
            role = content.role
            for part in content.parts:
                context_text += f"{role}: {part.text}\n"

        # Ambil pesan terakhir sebagai new_message (bisa gambar/teks)
        new_message = chat_history[-1]

        # Sisipkan konteks teks ini sebagai awal dari `new_message.parts`
        # supaya model tahu konteks sebelumnya
        if new_message.parts and new_message.parts[0].text:
            new_message.parts[0].text = f"Konteks sebelumnya:\n{context_text.strip()}\n\n{new_message.parts[0].text}"
        else:
            # jika part pertama bukan teks, tambahkan teks baru di awal
            new_message.parts.insert(0, types.Part(text=f"Konteks sebelumnya:\n{context_text.strip()}"))
        result = ""
        # Jalankan seperti biasa
        async for event in runner.run_async(
            session_id=session.id,
            user_id=email,
            new_message=new_message
        ):
            ...

            ...
        
            if hasattr(event, 'is_final_response') and event.is_final_response:
                if hasattr(event, 'content') and hasattr(event.content, 'parts'):
                    for part in event.content.parts:
                        if hasattr(part, 'text') and part.text:
                            clean_text = re.sub(r"[*]{1,2}", "", part.text)
                            result += clean_text

        # Simpan pesan ke histori
        user_message = Message(
            role="user",
            content=query,
            timestamp=datetime.utcnow(),
            file_name=file.filename if file else None,
            image=base64_image if file else None
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
                timestamp=agent_message.timestamp  # gunakan waktu agent_message sebagai waktu terakhir
            )
            history_collection.insert_one(new_history.dict())

        return {
            "user_name": user_data.get("name"),
            "email": email,
            "query": query,
            "response": result,
            "image_url": file.filename if file else None,
            "image": base64_image,  # ✅ ini dikonsumsi frontend
            "session_id": session_id
        }

    except Exception as e:
        logger.error(f"Agent failed to respond: {str(e)}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Gagal memproses permintaan: {str(e)}")





# @router.post("/ask")
# async def ask_agent(
#     data: QueryInput,
#     # file: Optional[UploadFile] = File(None),
#     user_data: dict = Depends(verify_firebase_token)  # ganti di sini
# ):
#     if data.email != user_data["email"]:
#         raise HTTPException(status_code=401, detail="Email tidak cocok dengan token")
    
#     try:
#         logger.info(f"Processing query: {data.query} dari user: {user_data.get('name')}")

#         # Ambil histori chat
#         session_id = data.session_id or str(uuid.uuid4())
#         existing_chat = history_collection.find_one({
#             "firebase_uid": user_data["uid"], 
#             "session_id": session_id
#         })

#         chat_history: List[types.Content] = []

#         if existing_chat:
#             for msg in existing_chat["messages"]:
#                 chat_history.append(
#                     types.Content(
#                         role=msg["role"],
#                         parts=[types.Part(text=msg["content"])]
#                     )
#                 )

#         # Tambahkan pesan user terbaru ke dalam history
#         chat_history.append(
#             types.Content(
#                 role="user",
#                 parts=[types.Part(text=data.query)]
#             )
#         )

#         # Siapkan runner dan session
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
#         context_text = ""
#         for content in chat_history:
#             role = content.role
#             for part in content.parts:
#                 context_text += f"{role}: {part.text}\n"

#         new_message = types.Content(
#             role="user",
#             parts=[types.Part(text=context_text)]
#         )

#         result = ""
#         async for event in runner.run_async(
#             session_id=session.id,
#             user_id=data.email,
#             new_message=new_message  # KIRIM CONTENT BUKAN LIST
#         ):
    

#             if hasattr(event, 'is_final_response') and event.is_final_response:
#                 if hasattr(event, 'content') and hasattr(event.content, 'parts'):
#                     for part in event.content.parts:
#                         if hasattr(part, 'text') and part.text:
#                             clean_text = re.sub(r"[*]{1,2}", "", part.text)
#                             result += clean_text


#         # Simpan pesan user dan agent ke history
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

#         if existing_chat:
#              history_collection.update_one(
#                 {"firebase_uid": user_data["uid"], "session_id": session_id},
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
#             new_history = ChatHistory(
#                 firebase_uid=user_data["uid"],
#                 session_id=session_id,
#                 messages=[user_message, agent_message],
#                 timestamp=datetime.utcnow()
#             )
#             history_collection.insert_one(new_history.dict())

#         return {
#             "user_name": user_data.get("name"),
#             "email": data.email,
#             "query": data.query,
#             "response": result,
#             "session_id": session_id
#         }

#     except Exception as e:
#         logger.error(f"Agent failed to respond.")
#         logger.error(f"Error: {str(e)}")
#         logger.error(traceback.format_exc())
#         raise HTTPException(status_code=500, detail=f"Gagal memproses permintaan: {str(e)}")




@router.post("/analyze-image")
async def analyze_image(
    file: UploadFile = File(...),
    prompt: str = Form(...)
):
    try:
        contents = await file.read()

        image_parts = [{
            "mime_type": file.content_type,
            "data": contents
        }]

        input_prompt = """
        You are an expert in identifying tourist destinations.
        You will receive input images and a prompt.
        Based on the image and prompt, analyze and answer accordingly.
        """

        model = genai.GenerativeModel('gemini-2.0-flash')
        response = model.generate_content([input_prompt, image_parts[0], prompt])

        return {"response": response.text}

    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})
   # app/api/agent.py


# app/api/agent.py
from fastapi import APIRouter, UploadFile, File, Form
from fastapi.responses import JSONResponse
from google import genai
import pathlib
import tempfile
import traceback
import os
from dotenv import load_dotenv

# load_dotenv()

# genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))
client = genai.Client()

# router = APIRouter()

@router.post("/analyze-document")
async def analyze_document(
    file: UploadFile = File(...),
    prompt: str = Form("Summarize this document")
):
    try:
        # Simpan file sementara
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
            tmp.write(await file.read())
            tmp_path = pathlib.Path(tmp.name)

        # Upload ke Google
        uploaded_file = client.files.upload(file=tmp_path)

        # Panggil model
        response = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=[uploaded_file, prompt]
        )

        # Hapus file lokal
        tmp_path.unlink()

        return {"response": response.text}

    except Exception as e:
        traceback.print_exc()
        return JSONResponse(status_code=500, content={"error": str(e)})
