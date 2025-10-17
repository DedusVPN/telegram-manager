import asyncio
from datetime import datetime
from random import uniform
from telethon.errors import FloodWaitError, UserBannedInChannelError, ChatWriteForbiddenError
from database import Message

class MessageSender:
    def __init__(self, account_manager, db):
        self.account_manager = account_manager
        self.db = db

    async def send_message(self, account_id: int, encrypted_session: str, target_chat: str, text: str):
        try:
            client = await self.account_manager.get_client(account_id, encrypted_session)
            await client.send_message(target_chat, text, parse_mode='markdown')
            return {'status': 'success', 'error': None}
        except FloodWaitError as e:
            return {'status': 'flood_wait', 'error': f'Flood wait {e.seconds} seconds'}
        except (UserBannedInChannelError, ChatWriteForbiddenError) as e:
            return {'status': 'forbidden', 'error': str(e)}
        except Exception as e:
            return {'status': 'error', 'error': str(e)}

    async def execute_task(self, task_id: int, accounts: list, target_chat: str, message_text: str,
                          repeat_count: int, interval: int, account_delay: int):
        for repeat in range(repeat_count):
            for account in accounts:
                result = await self.send_message(
                    account.id,
                    account.session_string,
                    target_chat,
                    message_text
                )

                async with self.db.session_maker() as session:
                    message = Message(
                        account_id=account.id,
                        target_chat=target_chat,
                        text=message_text,
                        status=result['status'],
                        sent_at=datetime.utcnow() if result['status'] == 'success' else None,
                        error=result['error']
                    )
                    session.add(message)
                    await session.commit()

                if result['status'] == 'flood_wait':
                    await asyncio.sleep(int(result['error'].split()[2]))

                randomized_delay = account_delay + uniform(-2, 2)
                await asyncio.sleep(max(1, randomized_delay))

            if repeat < repeat_count - 1:
                randomized_interval = interval + uniform(-5, 5)
                await asyncio.sleep(max(10, randomized_interval))

    async def get_statistics(self):
        async with self.db.session_maker() as session:
            from sqlalchemy import select, func
            result = await session.execute(
                select(
                    Message.status,
                    func.count(Message.id)
                ).group_by(Message.status)
            )
            stats = dict(result.all())
            return stats
