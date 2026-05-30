from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class LoginRequest(BaseModel):
    password: str


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class AccountResponse(ORMModel):
    id: int
    phone: str
    username: str | None = None
    first_name: str | None = None
    last_name: str | None = None
    is_active: bool
    created_at: datetime


class AccountAuthStartRequest(BaseModel):
    phone: str = Field(min_length=5, max_length=20)


class AccountAuthStartResponse(BaseModel):
    session_id: str
    status: str


class AccountAuthVerifyRequest(BaseModel):
    session_id: str
    code: str = Field(min_length=1, max_length=10)


class AccountAuth2FARequest(BaseModel):
    session_id: str
    password: str = Field(min_length=1)


class AccountAuthResponse(BaseModel):
    status: str
    account: AccountResponse | None = None
    message: str | None = None


class DialogLastMessage(BaseModel):
    id: int
    text: str
    date: str | None = None
    out: bool


class DialogResponse(BaseModel):
    id: str
    title: str
    unread_count: int
    is_user: bool
    is_group: bool
    is_channel: bool
    is_bot: bool = False
    has_avatar: bool = False
    username: str | None = None
    last_message: DialogLastMessage | None = None


class BotCommandResponse(BaseModel):
    command: str
    description: str = ""


class MessageButtonResponse(BaseModel):
    text: str
    url: str | None = None
    callback_data: str | None = None
    switch_inline_query: str | None = None
    copy_text: str | None = None


class MessageKeyboardResponse(BaseModel):
    type: str
    rows: list[list[MessageButtonResponse]]
    resize: bool | None = None
    one_time: bool | None = None
    persistent: bool | None = None


class ChatMessageResponse(BaseModel):
    id: int
    text: str
    text_html: str = ""
    date: str | None = None
    out: bool
    sender_id: int | None = None
    sender_name: str | None = None
    reply_markup: MessageKeyboardResponse | None = None
    edit_date: str | None = None


class MessageClickRequest(BaseModel):
    row: int | None = Field(default=None, ge=0)
    col: int | None = Field(default=None, ge=0)
    text: str | None = Field(default=None, min_length=1, max_length=256)


class SendMessageRequest(BaseModel):
    text: str = Field(min_length=1, max_length=4096)
    parse_mode: str | None = None


class SendMessageResponse(BaseModel):
    status: str
    message_id: int | None = None
    date: str | None = None
    error: str | None = None


class StatsResponse(BaseModel):
    success: int = 0
    pending: int = 0
    error: int = 0
    flood_wait: int = 0
    forbidden: int = 0


class HistoryMessageResponse(ORMModel):
    id: int
    account_id: int
    target_chat: str
    text: str
    status: str
    sent_at: datetime | None = None
    error: str | None = None
    created_at: datetime


class TaskCreateRequest(BaseModel):
    target_chat: str
    message_text: str
    account_ids: list[int] = Field(min_length=1)
    repeat_count: int = Field(default=1, ge=1, le=100)
    interval: int = Field(default=30, ge=10, le=3600)
    account_delay: int = Field(default=10, ge=1, le=600)


class TaskResponse(ORMModel):
    id: int
    target_chat: str
    message_text: str
    account_ids: str
    repeat_count: int
    interval: int
    account_delay: int
    status: str
    created_at: datetime
