import io
from datetime import datetime

from cryptography.fernet import Fernet
from telethon import TelegramClient
from telethon.errors import (
    ChatWriteForbiddenError,
    FloodWaitError,
    PhoneCodeInvalidError,
    SessionPasswordNeededError,
    UserBannedInChannelError,
    UsernameInvalidError,
    UsernameNotOccupiedError,
)
from telethon.sessions import StringSession
from telethon.tl.types import Channel, Chat, User

from tam.services.proxy_utils import proxy_to_telethon
from tam.telegram.serialize import message_to_dict, pick_active_reply_keyboard


class AccountManager:
    def __init__(self, api_id: int, api_hash: str, encryption_key: str):
        self.api_id = api_id
        self.api_hash = api_hash
        self.cipher = Fernet(encryption_key.encode())
        self.clients: dict[int, TelegramClient] = {}

    def encrypt_session(self, session_string: str) -> str:
        return self.cipher.encrypt(session_string.encode()).decode()

    def decrypt_session(self, encrypted_session: str) -> str:
        return self.cipher.decrypt(encrypted_session.encode()).decode()

    def create_client(
        self,
        session_string: str | None = None,
        *,
        proxy: dict | None = None,
    ) -> TelegramClient:
        session = StringSession(session_string) if session_string else StringSession()
        kwargs: dict = {
            "connection_retries": 2,
            "retry_delay": 2,
        }
        if proxy:
            kwargs["proxy"] = proxy_to_telethon(proxy)
        return TelegramClient(session, self.api_id, self.api_hash, **kwargs)

    async def add_account(self, phone: str, *, proxy: dict | None = None):
        client = self.create_client(proxy=proxy)
        await client.connect()

        if not await client.is_user_authorized():
            await client.send_code_request(phone)
            return client, "code_sent"

        return client, "authorized"

    async def verify_code(
        self,
        client: TelegramClient,
        phone: str,
        code: str,
        password: str | None = None,
        *,
        skip_sign_in: bool = False,
    ):
        try:
            if not skip_sign_in:
                await client.sign_in(phone, code)
        except SessionPasswordNeededError:
            if password:
                await client.sign_in(password=password)
            else:
                return None, "password_required"
        except PhoneCodeInvalidError:
            return None, "invalid_code"

        me = await client.get_me()
        session_string = client.session.save()
        encrypted_session = self.encrypt_session(session_string)

        return {
            "phone": phone,
            "username": me.username,
            "first_name": me.first_name,
            "last_name": me.last_name,
            "session_string": encrypted_session,
        }, "success"

    async def load_account(
        self,
        encrypted_session: str,
        *,
        proxy: dict | None = None,
    ):
        session_string = self.decrypt_session(encrypted_session)
        client = self.create_client(session_string, proxy=proxy)
        await client.connect()
        return client

    async def get_client(
        self,
        account_id: int,
        encrypted_session: str,
        *,
        proxy: dict | None = None,
    ):
        if account_id not in self.clients:
            self.clients[account_id] = await self.load_account(
                encrypted_session,
                proxy=proxy,
            )
        return self.clients[account_id]

    async def remove_account(self, account_id: int):
        if account_id in self.clients:
            await self.clients[account_id].disconnect()
            del self.clients[account_id]

    async def close_all(self):
        for client in self.clients.values():
            await client.disconnect()
        self.clients.clear()

    @staticmethod
    def normalize_username(username: str) -> str:
        value = username.strip()
        if value.startswith("https://t.me/"):
            value = value.rstrip("/").split("/")[-1]
        if value.startswith("@"):
            value = value[1:]
        return value

    @staticmethod
    def _entity_has_photo(entity) -> bool:
        photo = getattr(entity, "photo", None)
        if photo is None:
            return False
        photo_id = getattr(photo, "photo_id", 0)
        return bool(photo_id)

    @staticmethod
    def _entity_to_dialog(entity) -> dict:
        if isinstance(entity, User):
            title = " ".join(filter(None, [entity.first_name, entity.last_name])).strip()
            if not title:
                title = entity.username or "Без имени"
            is_user, is_group, is_channel = True, False, False
        elif isinstance(entity, Chat):
            title = entity.title or "Без названия"
            is_user, is_group, is_channel = False, True, False
        elif isinstance(entity, Channel):
            title = entity.title or "Без названия"
            is_user = False
            is_group = entity.megagroup
            is_channel = entity.broadcast or not entity.megagroup
        else:
            title = getattr(entity, "title", None) or getattr(entity, "first_name", None) or "Без названия"
            is_user = getattr(entity, "bot", False) or hasattr(entity, "phone")
            is_group = False
            is_channel = False

        return {
            "id": str(entity.id),
            "title": title,
            "unread_count": 0,
            "is_user": is_user,
            "is_group": is_group,
            "is_channel": is_channel,
            "is_bot": bool(getattr(entity, "bot", False)),
            "has_avatar": AccountManager._entity_has_photo(entity),
            "username": getattr(entity, "username", None),
            "last_message": None,
        }

    async def _resolve_chat(self, client: TelegramClient, chat_ref: str):
        ref = chat_ref.strip()
        if ref.lstrip("-").isdigit():
            peer_id = int(ref)
            try:
                return await client.get_entity(peer_id)
            except ValueError:
                async for dialog in client.iter_dialogs():
                    if dialog.entity.id == peer_id:
                        return dialog.entity
                raise ValueError(f"Чат {ref} не найден. Откройте список диалогов и попробуйте снова.")
        return await client.get_entity(self.normalize_username(ref))

    async def search_by_username(
        self,
        account_id: int,
        encrypted_session: str,
        username: str,
        *,
        proxy: dict | None = None,
    ) -> dict:
        client = await self.get_client(account_id, encrypted_session, proxy=proxy)
        normalized = self.normalize_username(username)
        if not normalized:
            raise ValueError("Username не указан")

        try:
            entity = await client.get_entity(normalized)
        except (UsernameInvalidError, UsernameNotOccupiedError, ValueError) as exc:
            raise LookupError(f"Username @{normalized} не найден") from exc

        return self._entity_to_dialog(entity)

    async def get_dialogs(
        self,
        account_id: int,
        encrypted_session: str,
        limit: int = 50,
        search: str | None = None,
        *,
        proxy: dict | None = None,
    ) -> list[dict]:
        client = await self.get_client(account_id, encrypted_session, proxy=proxy)
        dialogs = await client.get_dialogs(limit=limit)
        result = []

        for dialog in dialogs:
            entity = dialog.entity
            last_message = None
            if dialog.message:
                last_message = {
                    "id": dialog.message.id,
                    "text": dialog.message.message or "",
                    "date": dialog.message.date.isoformat() if dialog.message.date else None,
                    "out": dialog.message.out,
                }

            result.append(
                {
                    "id": str(entity.id),
                    "title": dialog.title or dialog.name or "Без названия",
                    "unread_count": dialog.unread_count,
                    "is_user": dialog.is_user,
                    "is_group": dialog.is_group,
                    "is_channel": dialog.is_channel,
                    "is_bot": bool(getattr(entity, "bot", False)),
                    "has_avatar": self._entity_has_photo(entity),
                    "username": getattr(entity, "username", None),
                    "last_message": last_message,
                }
            )

        if search:
            query = self.normalize_username(search).lower()
            result = [
                dialog
                for dialog in result
                if query in dialog["title"].lower()
                or (dialog["username"] and query in dialog["username"].lower())
            ]

        return result

    async def get_chat_avatar(
        self,
        account_id: int,
        encrypted_session: str,
        chat_id: str,
        *,
        proxy: dict | None = None,
    ) -> bytes | None:
        client = await self.get_client(account_id, encrypted_session, proxy=proxy)
        entity = await self._resolve_chat(client, chat_id)
        if not self._entity_has_photo(entity):
            return None

        buffer = io.BytesIO()
        downloaded = await client.download_profile_photo(entity, file=buffer)
        if not downloaded:
            return None

        data = buffer.getvalue()
        return data or None

    async def get_messages(
        self,
        account_id: int,
        encrypted_session: str,
        chat_id: str,
        limit: int = 50,
        offset_id: int = 0,
        *,
        proxy: dict | None = None,
    ) -> list[dict]:
        client = await self.get_client(account_id, encrypted_session, proxy=proxy)
        entity = await self._resolve_chat(client, chat_id)
        kwargs = {"limit": limit}
        if offset_id:
            kwargs["offset_id"] = offset_id

        messages = await client.get_messages(entity, **kwargs)
        return [message_to_dict(message) for message in messages if message is not None]

    async def mark_chat_read(
        self,
        account_id: int,
        encrypted_session: str,
        chat_id: str,
        *,
        proxy: dict | None = None,
    ) -> dict:
        client = await self.get_client(account_id, encrypted_session, proxy=proxy)
        entity = await self._resolve_chat(client, chat_id)
        await client.send_read_acknowledge(entity)
        return {"status": "success"}

    async def get_bot_commands(
        self,
        account_id: int,
        encrypted_session: str,
        chat_id: str,
        *,
        proxy: dict | None = None,
    ) -> list[dict]:
        from telethon.tl.functions.users import GetFullUserRequest

        client = await self.get_client(account_id, encrypted_session, proxy=proxy)
        entity = await self._resolve_chat(client, chat_id)
        if not getattr(entity, "bot", False):
            return []

        try:
            full = await client(GetFullUserRequest(entity))
        except Exception:
            return []

        bot_info = getattr(full.full_user, "bot_info", None)
        if not bot_info or not bot_info.commands:
            return []

        return [
            {"command": command.command, "description": command.description or ""}
            for command in bot_info.commands
        ]

    async def get_active_reply_keyboard(
        self,
        account_id: int,
        encrypted_session: str,
        chat_id: str,
        limit: int = 100,
        *,
        proxy: dict | None = None,
    ) -> dict | None:
        client = await self.get_client(account_id, encrypted_session, proxy=proxy)
        entity = await self._resolve_chat(client, chat_id)
        messages = await client.get_messages(entity, limit=limit)
        serialized = [message_to_dict(message) for message in messages if message is not None]
        return pick_active_reply_keyboard(serialized)

    async def click_message_button(
        self,
        account_id: int,
        encrypted_session: str,
        chat_id: str,
        message_id: int,
        *,
        row: int | None = None,
        col: int | None = None,
        text: str | None = None,
        proxy: dict | None = None,
    ) -> dict:
        client = await self.get_client(account_id, encrypted_session, proxy=proxy)
        entity = await self._resolve_chat(client, chat_id)
        message = await client.get_messages(entity, ids=message_id)
        if not message:
            raise ValueError("Сообщение не найдено")

        target = message[0] if isinstance(message, list) else message
        if text:
            await target.click(text=text)
        elif row is not None and col is not None:
            await target.click(i=row, j=col)
        else:
            raise ValueError("Укажите text или row/col")

        return {"status": "success"}

    async def send_chat_message(
        self,
        account_id: int,
        encrypted_session: str,
        chat_id: str,
        text: str,
        *,
        parse_mode: str | None = None,
        proxy: dict | None = None,
    ) -> dict:
        try:
            client = await self.get_client(account_id, encrypted_session, proxy=proxy)
            entity = await self._resolve_chat(client, chat_id)
            message = await client.send_message(entity, text, parse_mode=parse_mode)
            return {
                "status": "success",
                "message_id": message.id,
                "date": message.date.isoformat() if message.date else datetime.utcnow().isoformat(),
                "error": None,
            }
        except FloodWaitError as exc:
            return {
                "status": "flood_wait",
                "message_id": None,
                "date": None,
                "error": f"Flood wait {exc.seconds} seconds",
            }
        except (UserBannedInChannelError, ChatWriteForbiddenError) as exc:
            return {"status": "forbidden", "message_id": None, "date": None, "error": str(exc)}
        except Exception as exc:
            return {"status": "error", "message_id": None, "date": None, "error": str(exc)}
