from pydantic import BaseModel
from typing import Optional

class RegisterRequest(BaseModel):
    display_name: str
    tag: str
    password: str

class LoginRequest(BaseModel):
    tag_or_email: str
    password: str

class UpdateProfileRequest(BaseModel):
    display_name: Optional[str] = None
    bio: Optional[str] = None
    language: Optional[str] = None
    avatar_url: Optional[str] = None

class SendMessageRequest(BaseModel):
    conversation_id: str
    content: str
    type: str = "text"
    reply_to_id: Optional[str] = None
    reply_to_content: Optional[str] = None
    reply_to_sender: Optional[str] = None
    caption: Optional[str] = None
    file_name: Optional[str] = None
    file_size: Optional[int] = None

class ReactRequest(BaseModel):
    emoji: str

class CreateConversationRequest(BaseModel):
    target_tag: str

class FcmTokenRequest(BaseModel):
    token: str

class CallSignalRequest(BaseModel):
    target_user_id: str
    signal_data: dict
    is_video: bool = False
