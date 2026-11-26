import os
import re
import time
from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, Response
from bson import ObjectId
from services.database import get_users
from models.schemas import UpdateProfileRequest
from routes.auth import get_current_user

router = APIRouter(prefix="/users", tags=["users"])


def _s(doc):
    doc["_id"] = str(doc["_id"])
    if "avatar_data" in doc:
        del doc["avatar_data"]
    return doc


@router.get("/search")
async def search_users(tag: str, current_user: dict = Depends(get_current_user)):
    """Search users by @tag or display name prefix — returns up to 20 suggestions."""
    clean = tag.strip().lstrip("@")
    safe_query = re.escape(clean)
    users = get_users()
    cursor = users.find(
        {
            "$and": [
                {"_id": {"$ne": ObjectId(current_user["_id"])}},
                {
                    "$or": [
                        {"tag": {"$regex": safe_query, "$options": "i"}},
                        {"display_name": {"$regex": safe_query, "$options": "i"}},
                    ]
                },
            ]
        },
        {"password_hash": 0, "avatar_data": 0},
    ).limit(20)
    results = []
    async for u in cursor:
        results.append(_s(u))
    return results


@router.get("/blocked")
async def get_blocked_users(current_user: dict = Depends(get_current_user)):
    users = get_users()
    me = await users.find_one({"_id": ObjectId(current_user["_id"])})
    blocked_ids = (me or {}).get("blocked_users", [])
    if not blocked_ids:
        return []

    blocked_oids = [ObjectId(bid) for bid in blocked_ids if ObjectId.is_valid(bid)]
    cursor = users.find({"_id": {"$in": blocked_oids}}, {"password_hash": 0, "avatar_data": 0})
    results = []
    async for u in cursor:
        results.append(_s(u))
    return results


@router.post("/block/{user_id}")
async def block_user(user_id: str, current_user: dict = Depends(get_current_user)):
    if user_id == current_user["_id"]:
        raise HTTPException(status_code=400, detail="Cannot block yourself")
    users = get_users()
    await users.update_one(
        {"_id": ObjectId(current_user["_id"])},
        {"$addToSet": {"blocked_users": user_id}}
    )
    return {"message": "User blocked successfully", "blocked_user_id": user_id}


@router.post("/unblock/{user_id}")
async def unblock_user(user_id: str, current_user: dict = Depends(get_current_user)):
    users = get_users()
    await users.update_one(
        {"_id": ObjectId(current_user["_id"])},
        {"$pull": {"blocked_users": user_id}}
    )
    return {"message": "User unblocked successfully", "unblocked_user_id": user_id}


@router.get("/{tag}")
async def get_user(tag: str, current_user: dict = Depends(get_current_user)):
    users = get_users()
    clean_tag = f"@{re.sub(r'^@+', '', tag)}"
    u = await users.find_one({"tag": clean_tag}, {"password_hash": 0, "avatar_data": 0})
    if not u:
        raise HTTPException(status_code=404, detail="User not found")
    return _s(u)


@router.put("/profile")
async def update_profile(req: UpdateProfileRequest, current_user: dict = Depends(get_current_user)):
    users = get_users()
    update = {k: v for k, v in req.dict().items() if v is not None}
    if not update:
        raise HTTPException(status_code=400, detail="Nothing to update")
    await users.update_one({"_id": ObjectId(current_user["_id"])}, {"$set": update})
    u = await users.find_one({"_id": ObjectId(current_user["_id"])}, {"password_hash": 0, "avatar_data": 0})
    return _s(u)


@router.post("/upload-avatar")
async def upload_avatar(
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user),
):
    content_type = file.content_type or "image/jpeg"
    if not content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="Only image files are allowed")

    data = await file.read()
    if len(data) > 10 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="Image size exceeds 10MB")

    users = get_users()
    user_id = current_user["_id"]

    base_url = os.getenv("SPACE_URL", "https://always-together-backend.onrender.com").rstrip("/")
    v = int(time.time())
    avatar_url = f"{base_url}/users/avatar/{user_id}?v={v}"

    await users.update_one(
        {"_id": ObjectId(user_id)},
        {
            "$set": {
                "avatar_data": data,
                "avatar_content_type": content_type,
                "avatar_url": avatar_url,
            }
        },
    )
    return {"avatar_url": avatar_url}


@router.get("/avatar/{user_id}")
async def get_avatar(user_id: str):
    users = get_users()
    try:
        oid = ObjectId(user_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid user ID")

    u = await users.find_one({"_id": oid}, {"avatar_data": 1, "avatar_content_type": 1})
    if not u or "avatar_data" not in u or not u["avatar_data"]:
        raise HTTPException(status_code=404, detail="Avatar not found")

    content_type = u.get("avatar_content_type", "image/jpeg")
    return Response(
        content=u["avatar_data"],
        media_type=content_type,
        headers={"Cache-Control": "public, max-age=86400"},
    )
