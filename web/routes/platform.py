import asyncio

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select

from tam.db.models import Account, Message as DBMessage, Task
from web.auth import get_current_user
from web.dependencies import get_db, get_message_sender
from web.schemas import HistoryMessageResponse, StatsResponse, TaskCreateRequest, TaskResponse

router = APIRouter(prefix="/api", tags=["platform"], dependencies=[Depends(get_current_user)])


@router.get("/stats", response_model=StatsResponse)
async def get_stats(message_sender=Depends(get_message_sender)):
    stats = await message_sender.get_statistics()
    return StatsResponse(**{key: stats.get(key, 0) for key in StatsResponse.model_fields})


@router.get("/messages/history", response_model=list[HistoryMessageResponse])
async def get_history(limit: int = Query(default=50, ge=1, le=200), db=Depends(get_db)):
    async with db.session_maker() as session:
        result = await session.execute(
            select(DBMessage).order_by(DBMessage.created_at.desc()).limit(limit)
        )
        messages = result.scalars().all()
        return [HistoryMessageResponse.model_validate(message) for message in messages]


@router.get("/tasks", response_model=list[TaskResponse])
async def list_tasks(db=Depends(get_db)):
    async with db.session_maker() as session:
        result = await session.execute(select(Task).order_by(Task.created_at.desc()).limit(100))
        tasks = result.scalars().all()
        return [TaskResponse.model_validate(task) for task in tasks]


@router.post("/tasks", response_model=TaskResponse)
async def create_task(
    payload: TaskCreateRequest,
    db=Depends(get_db),
    message_sender=Depends(get_message_sender),
):
    async with db.session_maker() as session:
        result = await session.execute(
            select(Account).where(Account.id.in_(payload.account_ids), Account.is_active == True)
        )
        accounts = result.scalars().all()
        if len(accounts) != len(payload.account_ids):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Некоторые аккаунты не найдены",
            )

        task = Task(
            target_chat=payload.target_chat,
            message_text=payload.message_text,
            account_ids=",".join(map(str, payload.account_ids)),
            repeat_count=payload.repeat_count,
            interval=payload.interval,
            account_delay=payload.account_delay,
            status="running",
        )
        session.add(task)
        await session.commit()
        await session.refresh(task)

    asyncio.create_task(
        message_sender.execute_task(
            task.id,
            accounts,
            payload.target_chat,
            payload.message_text,
            payload.repeat_count,
            payload.interval,
            payload.account_delay,
        )
    )
    return TaskResponse.model_validate(task)
