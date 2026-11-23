from fastapi import APIRouter, Depends
from services.database import get_fcm_tokens
from services.ws_manager import manager
from models.schemas import FcmTokenRequest, CallSignalRequest
from routes.auth import get_current_user

router = APIRouter(prefix="/notifications", tags=["notifications"])

@router.post("/register-token")
async def register_fcm_token(req: FcmTokenRequest, current_user: dict = Depends(get_current_user)):
    tokens = get_fcm_tokens()
    await tokens.update_one(
        {"user_id": current_user["_id"]},
        {"$set": {"user_id": current_user["_id"], "token": req.token}},
        upsert=True
    )
    return {"success": True}


calls_router = APIRouter(prefix="/calls", tags=["calls"])

@calls_router.post("/offer")
async def call_offer(req: CallSignalRequest, current_user: dict = Depends(get_current_user)):
    await manager.send_to(req.target_user_id, "call_offer", {
        "from_user_id": current_user["_id"],
        "from_tag": current_user["tag"],
        "from_name": current_user.get("display_name", ""),
        "is_video": req.is_video,
        "signal": req.signal_data,
    })
    return {"success": True}

@calls_router.post("/answer")
async def call_answer(req: CallSignalRequest, current_user: dict = Depends(get_current_user)):
    await manager.send_to(req.target_user_id, "call_answer", {
        "from_user_id": current_user["_id"],
        "signal": req.signal_data,
    })
    return {"success": True}

@calls_router.post("/ice-candidate")
async def ice_candidate(req: CallSignalRequest, current_user: dict = Depends(get_current_user)):
    await manager.send_to(req.target_user_id, "call_ice_candidate", {
        "from_user_id": current_user["_id"],
        "candidate": req.signal_data,
    })
    return {"success": True}

@calls_router.post("/end")
async def end_call(req: CallSignalRequest, current_user: dict = Depends(get_current_user)):
    await manager.send_to(req.target_user_id, "call_ended", {
        "from_user_id": current_user["_id"],
    })
    return {"success": True}
