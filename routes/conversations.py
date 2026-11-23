from datetime import datetime
from fastapi import APIRouter, HTTPException, Depends
from bson import ObjectId
from services.database import get_conversations, get_users, get_messages
from models.schemas import CreateConversationRequest
from routes.auth import get_current_user

router = APIRouter(prefix="/conversations", tags=["conversations"])


def _s(doc):
    doc["_id"] = str(doc["_id"])
    return doc


async def _enrich_conversation(conv: dict, my_id: str) -> dict:
    """Add participant info and last message preview."""
    conv = _s(conv)
    conv["participant_ids"] = conv.get("participants", [])
    participants = []
    users = get_users()
    for uid in conv.get("participants", []):
        try:
            u = await users.find_one({"_id": ObjectId(uid)}, {"password_hash": 0})
            if u:
                u["_id"] = str(u["_id"])
                participants.append(u)
        except Exception:
            pass
    conv["participants"] = participants
    return conv


@router.get("")
async def list_conversations(current_user: dict = Depends(get_current_user)):
    convs = get_conversations()
    cursor = convs.find({"participants": current_user["_id"]}).sort("updated_at", -1).limit(50)
    results = []
    async for c in cursor:
        results.append(await _enrich_conversation(c, current_user["_id"]))
    return results


@router.post("/create")
async def create_conversation(req: CreateConversationRequest, current_user: dict = Depends(get_current_user)):
    users = get_users()
    target_tag = req.target_tag if req.target_tag.startswith("@") else f"@{req.target_tag}"
    target = await users.find_one({"tag": target_tag})
    if not target:
        raise HTTPException(status_code=404, detail="User not found")

    target_id = str(target["_id"])
    my_id = current_user["_id"]

    if target_id == my_id:
        raise HTTPException(status_code=400, detail="Cannot chat with yourself")

    convs = get_conversations()
    # Check if conversation already exists
    existing = await convs.find_one({
        "participants": {"$all": [my_id, target_id], "$size": 2}
    })
    if existing:
        return await _enrich_conversation(existing, my_id)

    # Create new
    now = datetime.utcnow().isoformat()
    doc = {
        "participants": [my_id, target_id],
        "last_message": None,
        "last_message_type": None,
        "last_message_at": None,
        "last_message_sender_id": None,
        "unread_count": 0,
        "created_at": now,
        "updated_at": now,
    }
    result = await convs.insert_one(doc)
    created = await convs.find_one({"_id": result.inserted_id})
    return await _enrich_conversation(created, my_id)
