import re
from fastapi import APIRouter, HTTPException, Depends
from bson import ObjectId
from services.database import get_users
from models.schemas import UpdateProfileRequest
from routes.auth import get_current_user

router = APIRouter(prefix="/users", tags=["users"])


def _s(doc):
    doc["_id"] = str(doc["_id"])
    return doc


@router.get("/search")
async def search_users(tag: str, current_user: dict = Depends(get_current_user)):
    """Search users by @tag prefix — returns up to 20 suggestions."""
    query = tag if tag.startswith("@") else f"@{tag}"
    # Escape special regex chars except @
    safe_query = re.escape(query)
    users = get_users()
    cursor = users.find(
        {
            "tag": {"$regex": f"^{safe_query}", "$options": "i"},
            "_id": {"$ne": ObjectId(current_user["_id"])}
        },
        {"password_hash": 0}
    ).limit(20)
    results = []
    async for u in cursor:
        results.append(_s(u))
    return results


@router.get("/{tag}")
async def get_user(tag: str, current_user: dict = Depends(get_current_user)):
    users = get_users()
    normalized = tag if tag.startswith("@") else f"@{tag}"
    u = await users.find_one({"tag": normalized}, {"password_hash": 0})
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
    u = await users.find_one({"_id": ObjectId(current_user["_id"])}, {"password_hash": 0})
    return _s(u)
