"""WebRTC signaling routes: offer, answer, ICE candidate."""

from __future__ import annotations

from typing import Any, Dict

from fastapi import APIRouter, Depends, HTTPException

from models.schemas import ICECandidate, WebRTCAnswer, WebRTCOffer
from routes.auth import get_current_user

router = APIRouter(prefix="/calls", tags=["calls"])


def _get_ws_manager():
    """Import lazily to avoid circular imports."""
    from main import manager
    return manager


@router.post("/offer")
async def call_offer(
    payload: WebRTCOffer,
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """Forward a WebRTC offer to the target user via WebSocket."""
    from services.database import get_users
    from bson import ObjectId
    users = get_users()
    if ObjectId.is_valid(payload.to_user_id):
        target = await users.find_one({"_id": ObjectId(payload.to_user_id)})
        if target and str(current_user["_id"]) in target.get("blocked_users", []):
            raise HTTPException(status_code=403, detail="User is not accepting calls from you")

    manager = _get_ws_manager()
    event = {
        "type": "webrtc_offer",
        "from_user_id": str(current_user["_id"]),
        "conversation_id": payload.conversation_id,
        "sdp": payload.sdp,
        "call_type": payload.call_type,
    }
    delivered = await manager.send_to_user(payload.to_user_id, event)
    if not delivered:
        raise HTTPException(status_code=404, detail="Target user is not connected")
    return {"status": "offer_sent"}


@router.post("/answer")
async def call_answer(
    payload: WebRTCAnswer,
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """Forward a WebRTC answer to the caller via WebSocket."""
    manager = _get_ws_manager()
    event = {
        "type": "webrtc_answer",
        "from_user_id": str(current_user["_id"]),
        "conversation_id": payload.conversation_id,
        "sdp": payload.sdp,
    }
    delivered = await manager.send_to_user(payload.to_user_id, event)
    if not delivered:
        raise HTTPException(status_code=404, detail="Target user is not connected")
    return {"status": "answer_sent"}


@router.post("/ice-candidate")
async def ice_candidate(
    payload: ICECandidate,
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """Forward an ICE candidate to the peer via WebSocket."""
    manager = _get_ws_manager()
    event = {
        "type": "ice_candidate",
        "from_user_id": str(current_user["_id"]),
        "conversation_id": payload.conversation_id,
        "candidate": payload.candidate,
    }
    delivered = await manager.send_to_user(payload.to_user_id, event)
    if not delivered:
        raise HTTPException(status_code=404, detail="Target user is not connected")
    return {"status": "candidate_sent"}
