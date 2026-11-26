from datetime import datetime
from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, Response
from bson import ObjectId
from services.database import get_messages, get_conversations, get_fcm_tokens, get_media
from services.translation_service import translate_text
from services.notification_service import send_push
from services.ws_manager import manager
from models.schemas import SendMessageRequest, ReactRequest
from routes.auth import get_current_user

router = APIRouter(prefix="/messages", tags=["messages"])


def _s(doc):
    doc["_id"] = str(doc["_id"])
    return doc


@router.post("/upload-media")
async def upload_media(file: UploadFile = File(...), current_user: dict = Depends(get_current_user)):
    data = await file.read()
    if len(data) > 15 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="File too large (max 15MB)")

    media = get_media()
    doc = {
        "uploader_id": current_user["_id"],
        "content_type": file.content_type or "image/jpeg",
        "filename": file.filename or "media",
        "data": data,
        "created_at": datetime.utcnow().isoformat() + "Z",
    }
    result = await media.insert_one(doc)
    media_id = str(result.inserted_id)
    url = f"https://always-together-backend.onrender.com/messages/media/{media_id}"
    return {"url": url, "media_id": media_id}


@router.get("/media/{media_id}")
async def get_chat_media(media_id: str):
    media = get_media()
    try:
        oid = ObjectId(media_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid media ID")

    doc = await media.find_one({"_id": oid})
    if not doc or "data" not in doc:
        raise HTTPException(status_code=404, detail="Media not found")

    content_type = doc.get("content_type", "image/jpeg")
    return Response(
        content=doc["data"],
        media_type=content_type,
        headers={"Cache-Control": "public, max-age=2592000"},
    )


@router.get("/{conversation_id}")
async def get_messages_route(conversation_id: str, page: int = 1,
                              current_user: dict = Depends(get_current_user)):
    msgs = get_messages()
    skip = (page - 1) * 30
    cursor = msgs.find(
        {"conversation_id": conversation_id, "is_deleted": {"$ne": True}},
    ).sort("created_at", -1).skip(skip).limit(30)
    results = []
    async for m in cursor:
        results.append(_s(m))
    return list(reversed(results))


@router.post("/send")
async def send_message(req: SendMessageRequest, current_user: dict = Depends(get_current_user)):
    now = datetime.utcnow().isoformat() + "Z"
    doc = {
        "conversation_id": req.conversation_id,
        "sender_id": current_user["_id"],
        "sender_tag": current_user["tag"],
        "sender_name": current_user.get("display_name", ""),
        "content": req.content,
        "type": req.type,
        "reply_to_id": req.reply_to_id,
        "reply_to_content": req.reply_to_content,
        "reply_to_sender": req.reply_to_sender,
        "reactions": [],
        "created_at": now,
        "deleted_at": None,
        "is_deleted": False,
        "is_delivered": False,
        "is_seen": False,
    }
    msgs = get_messages()
    result = await msgs.insert_one(doc)
    msg_doc = await msgs.find_one({"_id": result.inserted_id})
    msg_doc = _s(msg_doc)

    # Update conversation last message
    convs = get_conversations()
    await convs.update_one(
        {"_id": ObjectId(req.conversation_id)},
        {"$set": {"last_message": req.content, "last_message_type": req.type,
                  "last_message_at": now, "last_message_sender_id": current_user["_id"],
                  "updated_at": now}}
    )

    # Broadcast via WebSocket to all participants
    conv = await convs.find_one({"_id": ObjectId(req.conversation_id)})
    if conv:
        for uid in conv.get("participants", []):
            if uid != current_user["_id"]:
                await manager.send_to(uid, "new_message", msg_doc)
                # FCM if offline
                if not manager.is_online(uid):
                    tokens = get_fcm_tokens()
                    token_doc = await tokens.find_one({"user_id": uid})
                    if token_doc:
                        await send_push(
                            token_doc["token"],
                            title=f"{current_user['display_name']} ({current_user['tag']})",
                            body=req.content if req.type == "text" else f"Sent a {req.type}",
                            data={"conversation_id": req.conversation_id, "type": "new_message"}
                        )
    return msg_doc


@router.delete("/{message_id}")
async def delete_message(message_id: str, current_user: dict = Depends(get_current_user)):
    msgs = get_messages()
    msg = await msgs.find_one({"_id": ObjectId(message_id)})
    if not msg:
        raise HTTPException(status_code=404, detail="Message not found")
    if msg["sender_id"] != current_user["_id"]:
        raise HTTPException(status_code=403, detail="Not your message")

    now = datetime.utcnow().isoformat()
    await msgs.update_one(
        {"_id": ObjectId(message_id)},
        {"$set": {"is_deleted": True, "deleted_at": now, "content": "This message was deleted"}}
    )
    # Notify other participant
    convs = get_conversations()
    conv = await convs.find_one({"_id": ObjectId(msg["conversation_id"])})
    if conv:
        for uid in conv.get("participants", []):
            await manager.send_to(uid, "message_deleted", {"message_id": message_id})
    return {"success": True}


@router.post("/{message_id}/undo-delete")
async def undo_delete(message_id: str, current_user: dict = Depends(get_current_user)):
    msgs = get_messages()
    msg = await msgs.find_one({"_id": ObjectId(message_id)})
    if not msg:
        raise HTTPException(status_code=404, detail="Message not found")
    if msg["sender_id"] != current_user["_id"]:
        raise HTTPException(status_code=403, detail="Not your message")
    if not msg.get("is_deleted"):
        raise HTTPException(status_code=400, detail="Message not deleted")

    # Check 24h window
    deleted_at = datetime.fromisoformat(msg["deleted_at"]) if msg.get("deleted_at") else None
    if deleted_at and (datetime.utcnow() - deleted_at).total_seconds() > 86400:
        raise HTTPException(status_code=400, detail="Undo window expired (24h)")

    await msgs.update_one(
        {"_id": ObjectId(message_id)},
        {"$set": {"is_deleted": False, "deleted_at": None}}
    )
    return {"success": True}


@router.post("/{message_id}/react")
async def react_to_message(message_id: str, req: ReactRequest,
                            current_user: dict = Depends(get_current_user)):
    msgs = get_messages()
    msg = await msgs.find_one({"_id": ObjectId(message_id)})
    if not msg:
        raise HTTPException(status_code=404, detail="Message not found")

    reactions = msg.get("reactions", [])
    # Find or create reaction entry
    found = False
    for r in reactions:
        if r["emoji"] == req.emoji:
            if current_user["_id"] in r["user_ids"]:
                r["user_ids"].remove(current_user["_id"])  # toggle off
            else:
                r["user_ids"].append(current_user["_id"])
            found = True
            break
    if not found:
        reactions.append({"emoji": req.emoji, "user_ids": [current_user["_id"]]})

    # Remove empty reactions
    reactions = [r for r in reactions if r["user_ids"]]
    await msgs.update_one({"_id": ObjectId(message_id)}, {"$set": {"reactions": reactions}})

    # Notify participants
    convs = get_conversations()
    conv = await convs.find_one({"_id": ObjectId(msg["conversation_id"])})
    if conv:
        for uid in conv.get("participants", []):
            await manager.send_to(uid, "message_reaction",
                                  {"message_id": message_id, "reactions": reactions})
    return {"reactions": reactions}


@router.get("/{message_id}/translate")
async def translate_message(message_id: str, lang: str = "en",
                             current_user: dict = Depends(get_current_user)):
    msgs = get_messages()
    msg = await msgs.find_one({"_id": ObjectId(message_id)})
    if not msg:
        raise HTTPException(status_code=404, detail="Message not found")
    if msg.get("type") != "text":
        return {
            "translated": msg.get("content", ""),
            "original": msg.get("content", ""),
            "detected_lang": "",
            "target_lang": lang,
        }
    result = translate_text(msg.get("content", ""), lang)
    return {
        "translated": result.get("translated", ""),
        "original": msg.get("content", ""),
        "detected_lang": result.get("detected_lang", ""),
        "target_lang": result.get("target_lang", lang),
    }


@router.post("/{conversation_id}/seen")
async def mark_seen(conversation_id: str, current_user: dict = Depends(get_current_user)):
    msgs = get_messages()
    await msgs.update_many(
        {"conversation_id": conversation_id,
         "sender_id": {"$ne": current_user["_id"]},
         "is_seen": False},
        {"$set": {"is_seen": True}}
    )
    # Notify sender(s)
    convs = get_conversations()
    conv = await convs.find_one({"_id": ObjectId(conversation_id)})
    if conv:
        for uid in conv.get("participants", []):
            if uid != current_user["_id"]:
                await manager.send_to(uid, "message_seen",
                                      {"conversation_id": conversation_id, "seen_by": current_user["_id"]})
    return {"success": True}
