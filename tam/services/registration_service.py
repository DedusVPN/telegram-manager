import asyncio
import logging
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from tam.db.models import Account, Proxy, RegistrationItem, RegistrationJob
from tam.services.account_manager import AccountManager
from tam.services.error_utils import format_exception
from tam.services.proxy_manager import ProxyManager

logger = logging.getLogger(__name__)

ITEM_DELAY_SECONDS = 3


class RegistrationService:
    def __init__(
        self,
        account_manager: AccountManager,
        proxy_manager: ProxyManager,
        pending_auth,
    ):
        self.account_manager = account_manager
        self.proxy_manager = proxy_manager
        self.pending_auth = pending_auth
        self._tasks: dict[int, asyncio.Task] = {}

    def _ensure_worker(self, job_id: int) -> None:
        if job_id in self._tasks and not self._tasks[job_id].done():
            return
        self._tasks[job_id] = asyncio.create_task(self._process_job(job_id))

    async def create_job(
        self,
        session: AsyncSession,
        phones: list[str],
        *,
        proxy_id: int | None = None,
        delay_seconds: int = ITEM_DELAY_SECONDS,
        default_2fa_password: str | None = None,
    ) -> RegistrationJob:
        normalized_phones: list[str] = []
        for phone in phones:
            value = phone.strip()
            if not value:
                continue
            if not value.startswith("+"):
                value = f"+{value}"
            if value not in normalized_phones:
                normalized_phones.append(value)

        if not normalized_phones:
            raise ValueError("Список номеров пуст")

        job = RegistrationJob(
            status="pending",
            proxy_id=proxy_id,
            delay_seconds=max(1, min(delay_seconds, 120)),
            default_2fa_password=default_2fa_password,
            total_count=len(normalized_phones),
        )
        session.add(job)
        await session.flush()

        for phone in normalized_phones:
            session.add(RegistrationItem(job_id=job.id, phone=phone, status="pending"))
        await session.commit()
        await session.refresh(job)
        self._ensure_worker(job.id)
        return job

    async def _process_job(self, job_id: int) -> None:
        from web.dependencies import get_db

        database = get_db()
        try:
            while True:
                async with database.session_maker() as session:
                    job = await self._load_job(session, job_id)
                    if not job or job.status in ("completed", "cancelled"):
                        break

                    job.status = "running"
                    await session.commit()

                    pending_items = [
                        item
                        for item in job.items
                        if item.status == "pending"
                    ]
                    if not pending_items:
                        await self._finalize_job(session, job)
                        break

                    for index, item in enumerate(pending_items):
                        if job.status == "cancelled":
                            break
                        await self._process_item(session, job, item)
                        if index < len(pending_items) - 1:
                            await asyncio.sleep(job.delay_seconds)

                    await session.refresh(job)
                    await self._finalize_job(session, job)
                    break
        except Exception:
            logger.exception("Ошибка фоновой регистрации job_id=%s", job_id)
        finally:
            self._tasks.pop(job_id, None)

    async def _load_job(self, session: AsyncSession, job_id: int) -> RegistrationJob | None:
        result = await session.execute(
            select(RegistrationJob)
            .where(RegistrationJob.id == job_id)
            .options(selectinload(RegistrationJob.items))
        )
        return result.scalar_one_or_none()

    async def _finalize_job(self, session: AsyncSession, job: RegistrationJob) -> None:
        await session.refresh(job, attribute_names=["items"])
        active = [i for i in job.items if i.status not in ("success", "failed", "skipped")]
        if job.status != "cancelled":
            job.status = "completed" if not active else "running"
        job.completed_at = datetime.utcnow()
        await session.commit()

    async def _process_item(
        self,
        session: AsyncSession,
        job: RegistrationJob,
        item: RegistrationItem,
    ) -> None:
        item.status = "sending_code"
        item.error = None
        await session.commit()

        existing = await session.execute(select(Account).where(Account.phone == item.phone))
        if existing.scalar_one_or_none():
            item.status = "skipped"
            item.error = "Аккаунт уже существует"
            await session.commit()
            return

        proxy = await self.proxy_manager.pick_proxy(session, proxy_id=job.proxy_id)
        if not proxy:
            item.status = "failed"
            item.error = "Нет доступных прокси. Добавьте прокси во вкладке «Прокси»."
            await session.commit()
            return

        item.proxy_id = proxy.id
        proxy_dict = self.proxy_manager.proxy_row_to_dict(proxy)
        await self.proxy_manager.mark_proxy_used(session, proxy)

        try:
            client, auth_status = await self.account_manager.add_account(
                item.phone,
                proxy=proxy_dict,
            )
            if auth_status == "authorized":
                await client.disconnect()
                item.status = "failed"
                item.error = "Номер уже авторизован в Telegram"
                await session.commit()
                return

            session_id = self.pending_auth.create(
                client,
                item.phone,
                proxy_id=proxy.id,
                registration_item_id=item.id,
            )
            item.auth_session_id = session_id
            item.status = "code_sent"
            await session.commit()
        except Exception as exc:
            item.status = "failed"
            item.error = format_exception(exc)
            proxy.fail_count = (proxy.fail_count or 0) + 1
            if proxy.fail_count >= 3:
                proxy.is_healthy = False
            await session.commit()

    async def submit_code(
        self,
        session: AsyncSession,
        item_id: int,
        code: str,
        *,
        password: str | None = None,
    ) -> tuple[RegistrationItem, str]:
        result = await session.execute(
            select(RegistrationItem)
            .where(RegistrationItem.id == item_id)
            .options(selectinload(RegistrationItem.job))
        )
        item = result.scalar_one_or_none()
        if not item:
            raise LookupError("Задача регистрации не найдена")

        if item.status not in ("code_sent", "password_required"):
            raise ValueError(f"Нельзя отправить код в статусе {item.status}")

        if not item.auth_session_id:
            raise ValueError("Сессия авторизации отсутствует")

        pending = self.pending_auth.get(item.auth_session_id)
        if not pending:
            item.status = "failed"
            item.error = "Сессия истекла, перезапустите задачу"
            await session.commit()
            raise ValueError(item.error)

        needs_2fa_step = item.status == "password_required"
        item.status = "verifying"
        await session.commit()

        pwd = password if needs_2fa_step else (item.job.default_2fa_password if item.job else None)
        result_data, auth_status = await self.account_manager.verify_code(
            pending.client,
            pending.phone,
            code.strip() if not needs_2fa_step else (pending.code or code.strip()),
            pwd if needs_2fa_step else None,
            skip_sign_in=needs_2fa_step,
        )

        if auth_status == "password_required":
            self.pending_auth.set_code(item.auth_session_id, code.strip())
            item.status = "password_required"
            await session.commit()
            return item, "password_required"

        if auth_status == "invalid_code":
            item.status = "code_sent"
            await session.commit()
            raise ValueError("Неверный код")

        if auth_status != "success" or not result_data:
            item.status = "failed"
            item.error = "Ошибка авторизации"
            await session.commit()
            raise ValueError(item.error)

        existing = await session.execute(
            select(Account).where(Account.phone == result_data["phone"])
        )
        if existing.scalar_one_or_none():
            await self.pending_auth.discard(item.auth_session_id)
            item.status = "skipped"
            item.error = "Аккаунт уже в базе"
            await session.commit()
            await self._maybe_finalize_job(session, item.job_id)
            return item, "skipped"

        account = Account(**result_data, proxy_id=item.proxy_id)
        session.add(account)
        item.status = "success"
        item.error = None
        item.completed_at = datetime.utcnow()
        await session.commit()
        await self.pending_auth.discard(item.auth_session_id)
        await self._maybe_finalize_job(session, item.job_id)
        await session.refresh(item)
        return item, "success"

    async def _maybe_finalize_job(self, session: AsyncSession, job_id: int) -> None:
        job = await self._load_job(session, job_id)
        if not job or job.status == "cancelled":
            return
        terminal = ("success", "failed", "skipped")
        if job.items and all(i.status in terminal for i in job.items):
            job.status = "completed"
            job.completed_at = datetime.utcnow()
            await session.commit()

    async def cancel_job(self, session: AsyncSession, job_id: int) -> RegistrationJob | None:
        job = await self._load_job(session, job_id)
        if not job:
            return None
        job.status = "cancelled"
        job.completed_at = datetime.utcnow()
        for item in job.items:
            if item.status in ("pending", "sending_code"):
                item.status = "skipped"
                item.error = "Отменено"
            if item.auth_session_id:
                await self.pending_auth.discard(item.auth_session_id)
        await session.commit()
        task = self._tasks.pop(job_id, None)
        if task and not task.done():
            task.cancel()
        return job
