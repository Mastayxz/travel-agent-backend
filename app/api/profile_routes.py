from fastapi import APIRouter, HTTPException, Depends, Header
from firebase_admin import auth as firebase_auth
from pymongo import MongoClient
import os
from dotenv import load_dotenv

from app.models.profile import UserProfile, UpdateProfile

load_dotenv()

router = APIRouter()

MONGO_URI = os.getenv("MONGO_URI")
client = MongoClient(MONGO_URI)
db = client.chatbot
users_collection = db.users

# ======== Middleware Token Check ==========
async def get_current_user(authorization: str = Header(None)):
    if not authorization:
        raise HTTPException(status_code=401, detail="Authorization header missing")

    try:
        token = authorization.split(" ")[1] if authorization.startswith("Bearer ") else authorization
        decoded_token = firebase_auth.verify_id_token(token)
        uid = decoded_token["uid"]

        user = users_collection.find_one({"firebase_uid": uid})
        if not user:
            # Optional: bisa hapus auto-create ini
            user = {
                "firebase_uid": uid,
                "email": decoded_token.get("email", ""),
                "name": decoded_token.get("name"),
                "picture": decoded_token.get("picture"),
            }
            users_collection.insert_one(user)
        else:
            # Inject UID ke objek yang ditemukan (karena MongoDB gak auto return UID)
            user["firebase_uid"] = uid

        return user

    except IndexError:
        raise HTTPException(status_code=401, detail="Invalid authorization format")
    except Exception as e:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    
    
# ========== GET PROFILE ===============
@router.get("/profile", response_model=UserProfile)
async def get_profile(current_user: dict = Depends(get_current_user)):
    return UserProfile(
        email=current_user["email"],
        name=current_user.get("name"),
        picture=current_user.get("picture")
    )

# ========== UPDATE PROFILE ===========
from app.models.profile import UpdateProfile, UserProfile
from fastapi import UploadFile, File, Form
from fastapi.responses import JSONResponse
import base64
@router.put("/profile")
async def update_profile(
    name: str = Form(None),
    file: UploadFile = File(None),
    current_user: dict = Depends(get_current_user)
):
    firebase_uid = current_user.get("firebase_uid")
    if not firebase_uid:
        raise HTTPException(status_code=400, detail="Invalid user session (no firebase_uid)")

    update_fields = {}

    # ✔️ Update name jika ada
    if name is not None:
        update_fields["name"] = name

    # ✔️ Update gambar jika ada file
    if file:
        contents = await file.read()
        base64_image = base64.b64encode(contents).decode("utf-8")
        mime_type = file.content_type

        # Simpan string dalam format data URL
        picture_data_url = f"data:{mime_type};base64,{base64_image}"
        update_fields["picture"] = picture_data_url

    if not update_fields:
        raise HTTPException(status_code=400, detail="No fields to update")

    # Lakukan update MongoDB
    result = users_collection.update_one(
        {"firebase_uid": firebase_uid},
        {"$set": update_fields}
    )

    return JSONResponse(content={"message": "Profile updated successfully"})
# ========== DELETE PROFILE ===========
@router.delete("/profile", response_model=dict)
async def delete_profile(current_user: dict = Depends(get_current_user)):
    result = users_collection.delete_one({"firebase_uid": current_user["firebase_uid"]})
    if result.deleted_count == 0:
        raise HTTPException(status_code=400, detail="Failed to delete profile")
    return {"message": "Profile deleted successfully"}

# ========== GET PROFILE BY USER ID ===========
@router.get("/profile/{user_id}", response_model=UserProfile)
async def get_user_profile_by_id(
    user_id: str,
    current_user: dict = Depends(get_current_user)
):
    user = users_collection.find_one({"firebase_uid": user_id})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    return UserProfile(
        email=user["email"],
        name=user.get("name"),
        picture=user.get("picture")
    )
