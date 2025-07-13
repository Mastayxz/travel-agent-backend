from fastapi import APIRouter, HTTPException, Query
from app.models.history import ChatHistory, Message
from app.db import history_collection, bookmarks_collection
from datetime import datetime
from fastapi.responses import JSONResponse
from bson import ObjectId

router = APIRouter()
@router.post("/history/save/{firebase_uid}/{session_id}")
async def save_chat_history(
    firebase_uid: str,
    session_id: str,
    body: dict,
):
    try:
        # Cek apakah sesi sudah ada
        existing = bookmarks_collection.find_one({
            "firebase_uid": firebase_uid,
            "session_id": session_id
        })

        if existing:
           return JSONResponse(
            status_code=200,  # atau 409 jika mau anggap duplikat
            content={
                "message": "Session already saved",
                "id": str(existing["_id"]),
                "status": "already_saved"
            }
        )

        messages = body.get("messages", [])
        timestamp = body.get("timestamp", datetime.utcnow())

        # Pastikan tiap message memiliki timestamp
        for msg in messages:
            if "timestamp" not in msg:
                msg["timestamp"] = datetime.utcnow()

        history_data = {
            "firebase_uid": firebase_uid,
            "session_id": session_id,
            "messages": messages,
            "timestamp": timestamp,
        }

        result = bookmarks_collection.insert_one(history_data)

        return {
            "message": "History saved successfully",
            "id": str(result.inserted_id),
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Gagal menyimpan: {str(e)}")

@router.get("/history/{firebase_uid}")
async def get_user_history(
    firebase_uid: str, 
    limit: int = Query(10, description="Jumlah riwayat yang akan diambil"),
    offset: int = Query(0, description="Jumlah riwayat yang dilewati")
):
    try:
        history = list(
            history_collection.find({"firebase_uid": firebase_uid})
            .sort("timestamp", -1)  # Urutkan dari yang terbaru
            .skip(offset)
            .limit(limit)
        )
        
        for item in history:
            item["_id"] = str(item["_id"])  # convert ObjectId to string
            
        return {"history": history, "total": history_collection.count_documents({"firebase_uid": firebase_uid})}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve history: {str(e)}")

@router.get("/history/{firebase_uid}/{session_id}")
async def get_chat_session(firebase_uid: str, session_id: str):
    try:
        chat = history_collection.find_one({"firebase_uid": firebase_uid, "session_id": session_id})
        if not chat:
            raise HTTPException(status_code=404, detail="Chat session not found")
        
        chat["_id"] = str(chat["_id"])  # convert ObjectId to string
        return chat
    except Exception as e:
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(status_code=500, detail=f"Failed to retrieve chat session: {str(e)}")

@router.put("/history/{firebase_uid}/{session_id}")
async def update_chat_session(firebase_uid: str, session_id: str, history: ChatHistory):
    try:
        data = history.dict()
        data["timestamp"] = datetime.utcnow()  # Update timestamp
        
        result = history_collection.update_one(
            {"google_id": firebase_uid, "session_id": session_id},
            {"$set": data}
        )
        
        if result.matched_count == 0:
            raise HTTPException(status_code=404, detail="Chat session not found")
               
        return {"message": "Chat session updated successfully"}
    except Exception as e:
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(status_code=500, detail=f"Failed to update chat session: {str(e)}")

@router.delete("/history/{firebase_uid}/{session_id}")
async def delete_chat_session(firebase_uid: str, session_id: str):
    try:
        result = history_collection.delete_one({"firebase_uid": firebase_uid, "session_id": session_id})
        
        if result.deleted_count == 0:
            raise HTTPException(status_code=404, detail="Chat session not found")
        
        return {"message": "Chat session deleted successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete chat session: {str(e)}")

@router.delete("/bookmark/{firebase_uid}/{session_id}")
async def delete_bookmark_session(firebase_uid: str, session_id: str):
    try:
        result = bookmarks_collection.delete_one({"firebase_uid": firebase_uid, "session_id": session_id})
        
        if result.deleted_count == 0:
            raise HTTPException(status_code=404, detail="Chat session not found")
        
        return {"message": "Chat session deleted successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete chat session: {str(e)}")

@router.post("/history/{firebase_uid}/{session_id}/messages")
async def add_message_to_chat(google_id: str, session_id: str, message: Message):
    message_data = message.dict()
    message_data["timestamp"] = message.timestamp or datetime.utcnow()
    
    try:
        result = history_collection.update_one(
            {"google_id": google_id, "session_id": session_id},
            {
                "$push": {"messages": message_data},
                "$set": {"timestamp": datetime.utcnow()}  # Update timestamp percakapan
            }
        )
        
        if result.matched_count == 0:
            raise HTTPException(status_code=404, detail="Chat session not found")
            
        return {"message": "Message added successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to add message: {str(e)}")

@router.get("/bookmark/{firebase_uid}")
async def get_bookmark(firebase_uid: str):
    try:
        bookmarks = list(bookmarks_collection.find({"firebase_uid": firebase_uid}).sort("timestamp", -1))
        for b in bookmarks:
            b["_id"] = str(b["_id"])
        return {"bookmarks": bookmarks}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Gagal mengambil bookmark: {str(e)}")
 