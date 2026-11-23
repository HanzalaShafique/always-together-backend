import re
from datetime import datetime
from fastapi import APIRouter, HTTPException, Depends, Header
from bson import ObjectId
from services.database import get_users, get_fcm_tokens
from services.auth_service import hash_password, verify_password, create_token, decode_token
from models.schemas import RegisterRequest, LoginRequest

router = APIRouter(prefix="/auth", tags=["auth"])

TAG_PATTERN = re.compile(r"^@[a-zA-Z0-9_]{3,20}$")


def _serialize(doc: dict) -> dict:
    doc["_id"] = str(doc["_id"])
    return doc


async def get_current_user(authorization: str = Header(...)):
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid auth header")
    token = authorization[7:]
    payload = decode_token(token)
    user_id = payload.get("sub")
    users = get_users()
    user = await users.find_one({"_id": ObjectId(user_id)})
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    return _serialize(user)


@router.post("/register")
async def register(req: RegisterRequest):
    # Validate tag format
    tag = req.tag if req.tag.startswith("@") else f"@{req.tag}"
    if not TAG_PATTERN.match(tag):
        raise HTTPException(status_code=400, detail="Invalid tag format. Use @letters_numbers (3-20 chars)")

    users = get_users()

    # Check tag uniqueness
    existing = await users.find_one({"tag": tag})
    if existing:
        raise HTTPException(status_code=400, detail="Tag already taken")

    # Build app email
    email = f"{tag[1:].lower()}@alwaystogether.app"

    # Hash password and insert
    hashed = hash_password(req.password)
    doc = {
        "tag": tag,
        "email": email,
        "display_name": req.display_name,
        "password_hash": hashed,
        "bio": "",
        "avatar_url": None,
        "language": "en",
        "is_online": False,
        "gmail_linked": None,
        "created_at": datetime.utcnow().isoformat(),
    }
    result = await users.insert_one(doc)
    user_id = str(result.inserted_id)
    token = create_token(user_id, tag)

    user_doc = await users.find_one({"_id": result.inserted_id})
    return {"token": token, "user": _serialize(user_doc)}


@router.post("/login")
async def login(req: LoginRequest):
    users = get_users()
    tag_or_email = req.tag_or_email.strip()
    # Try tag first, then email
    if tag_or_email.startswith("@"):
        user = await users.find_one({"tag": tag_or_email})
    else:
        user = await users.find_one({"$or": [{"email": tag_or_email}, {"tag": f"@{tag_or_email}"}]})

    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    if not verify_password(req.password, user.get("password_hash", "")):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    user_id = str(user["_id"])
    token = create_token(user_id, user["tag"])
    # Mark online
    await users.update_one({"_id": user["_id"]}, {"$set": {"is_online": True}})
    return {"token": token, "user": _serialize(user)}


@router.get("/me")
async def get_me(current_user: dict = Depends(get_current_user)):
    return current_user


@router.get("/check-tag")
async def check_tag(tag: str):
    normalized = tag if tag.startswith("@") else f"@{tag}"
    if not TAG_PATTERN.match(normalized):
        return {"available": False, "reason": "Invalid format"}
    users = get_users()
    existing = await users.find_one({"tag": normalized})
    return {"available": existing is None}
