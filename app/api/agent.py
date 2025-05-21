from fastapi import APIRouter, HTTPException, Request, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
import os
import traceback
import logging
from google.oauth2 import id_token
from google.auth.transport import requests as google_requests
from google.genai import types
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService

# Import travel agent
from agents.travel_agent import travel_agent

# Setup logging
logger = logging.getLogger(__name__)

# Init router
router = APIRouter()

# Setup security scheme (for Swagger + Bearer token)
security = HTTPBearer()

# ====== VERIFIKASI GOOGLE TOKEN DINAMIS ======
async def verify_google_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    token = credentials.credentials
    try:
        # Verifikasi ID token ke Google
        id_info = id_token.verify_oauth2_token(token, google_requests.Request())

        # Ambil info penting dari token
        return {
            "email": id_info.get("email"),
            "name": id_info.get("name"),
            "picture": id_info.get("picture"),
            "sub": id_info.get("sub")
        }
    except Exception as e:
        logger.error(f"Token verification failed: {str(e)}")
        raise HTTPException(status_code=401, detail="Token tidak valid atau kadaluarsa")

# ====== SCHEMA INPUT ======
class QueryInput(BaseModel):
    email: str
    query: str

# ====== ROUTE UTAMA /ASK ======
@router.post("/ask")
async def ask_agent(
    data: QueryInput,
    user_data: dict = Depends(verify_google_token)
):
    # Validasi email dari token dan request body cocok
    if data.email != user_data["email"]:
        raise HTTPException(status_code=401, detail="Email tidak cocok dengan token")

    if "bali" not in data.query.lower():
        return {"response": "Maaf, saya hanya bisa menjawab pertanyaan seputar Bali."}

    try:
        logger.info(f"Processing query: {data.query} dari user: {user_data['name']}")

        # Setup session
        session_service = InMemorySessionService()
        session = session_service.create_session(
            app_name="bali_travel_guide",
            user_id=data.email
        )

        # Setup agent runner
        runner = Runner(
            agent=travel_agent,
            session_service=session_service,
            app_name="bali_travel_guide"
        )

        content = types.Content(
            role='user',
            parts=[types.Part(text=data.query)]
        )

        result = ""

        # Run agent and stream response
        async for event in runner.run_async(
            session_id=session.id,
            user_id=data.email,
            new_message=content
        ):
            if hasattr(event, 'is_final_response') and event.is_final_response:
                if hasattr(event, 'content') and hasattr(event.content, 'parts'):
                    for part in event.content.parts:
                        if hasattr(part, 'text') and part.text:
                            result += part.text

        return {
            "user_name": user_data["name"],
            "email": data.email,
            "query": data.query,
            "response": result
        }

    except Exception as e:
        logger.error(f"Error: {str(e)}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Gagal memproses permintaan: {str(e)}")

# ====== DEBUGGING ENDPOINT ======
@router.post("/debug")
async def debug_request(request: Request):
    body = await request.json()
    return {
        "received": body,
        "google_api_key_set": "GOOGLE_API_KEY" in os.environ,
        "travel_agent_type": str(type(travel_agent))
    }
