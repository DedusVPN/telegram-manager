from telethon import TelegramClient
from telethon.sessions import StringSession
from telethon.errors import SessionPasswordNeededError, PhoneCodeInvalidError
from cryptography.fernet import Fernet
import os

class AccountManager:
    def __init__(self, api_id: int, api_hash: str, encryption_key: str):
        self.api_id = api_id
        self.api_hash = api_hash
        self.cipher = Fernet(encryption_key.encode())
        self.clients = {}

    def encrypt_session(self, session_string: str) -> str:
        return self.cipher.encrypt(session_string.encode()).decode()

    def decrypt_session(self, encrypted_session: str) -> str:
        return self.cipher.decrypt(encrypted_session.encode()).decode()

    async def add_account(self, phone: str):
        client = TelegramClient(StringSession(), self.api_id, self.api_hash)
        await client.connect()

        if not await client.is_user_authorized():
            await client.send_code_request(phone)
            return client, 'code_sent'

        return client, 'authorized'

    async def verify_code(self, client: TelegramClient, phone: str, code: str, password: str = None):
        try:
            await client.sign_in(phone, code)
        except SessionPasswordNeededError:
            if password:
                await client.sign_in(password=password)
            else:
                return None, 'password_required'
        except PhoneCodeInvalidError:
            return None, 'invalid_code'

        me = await client.get_me()
        session_string = client.session.save()
        encrypted_session = self.encrypt_session(session_string)

        return {
            'phone': phone,
            'username': me.username,
            'first_name': me.first_name,
            'last_name': me.last_name,
            'session_string': encrypted_session
        }, 'success'

    async def load_account(self, encrypted_session: str):
        session_string = self.decrypt_session(encrypted_session)
        client = TelegramClient(StringSession(session_string), self.api_id, self.api_hash)
        await client.connect()
        return client

    async def get_client(self, account_id: int, encrypted_session: str):
        if account_id not in self.clients:
            self.clients[account_id] = await self.load_account(encrypted_session)
        return self.clients[account_id]

    async def remove_account(self, account_id: int):
        if account_id in self.clients:
            await self.clients[account_id].disconnect()
            del self.clients[account_id]

    async def close_all(self):
        for client in self.clients.values():
            await client.disconnect()
        self.clients.clear()
