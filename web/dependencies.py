from tam.config import Settings, get_settings
from tam.db import Database
from tam.services import AccountManager, MessageSender
from tam.services.proxy_manager import ProxyManager
from tam.services.registration_service import RegistrationService
from web.pending_auth import PendingAuthStore

db: Database | None = None
account_manager: AccountManager | None = None
message_sender: MessageSender | None = None
pending_auth: PendingAuthStore | None = None
proxy_manager: ProxyManager | None = None
registration_service: RegistrationService | None = None


def init_services(settings: Settings) -> None:
    global db, account_manager, message_sender, pending_auth, proxy_manager, registration_service

    db = Database(settings.database_url)
    account_manager = AccountManager(settings.api_id, settings.api_hash, settings.encryption_key)
    message_sender = MessageSender(account_manager, db)
    pending_auth = PendingAuthStore()
    proxy_manager = ProxyManager(settings.api_id, settings.api_hash)
    registration_service = RegistrationService(account_manager, proxy_manager, pending_auth)


async def shutdown_services() -> None:
    if account_manager:
        await account_manager.close_all()


def get_db() -> Database:
    if db is None:
        raise RuntimeError("Database не инициализирована")
    return db


def get_account_manager() -> AccountManager:
    if account_manager is None:
        raise RuntimeError("AccountManager не инициализирован")
    return account_manager


def get_message_sender() -> MessageSender:
    if message_sender is None:
        raise RuntimeError("MessageSender не инициализирован")
    return message_sender


def get_pending_auth() -> PendingAuthStore:
    if pending_auth is None:
        raise RuntimeError("PendingAuthStore не инициализирован")
    return pending_auth


def get_proxy_manager() -> ProxyManager:
    if proxy_manager is None:
        raise RuntimeError("ProxyManager не инициализирован")
    return proxy_manager


def get_registration_service() -> RegistrationService:
    if registration_service is None:
        raise RuntimeError("RegistrationService не инициализирован")
    return registration_service
