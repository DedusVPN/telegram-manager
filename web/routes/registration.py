from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from tam.db.models import RegistrationItem, RegistrationJob
from web.auth import get_current_user
from web.dependencies import get_db, get_registration_service
from web.schemas import (
    RegistrationCodeRequest,
    RegistrationItemResponse,
    RegistrationJobCreateRequest,
    RegistrationJobDetailResponse,
    RegistrationJobResponse,
    RegistrationPasswordRequest,
)

router = APIRouter(
    prefix="/api/registration",
    tags=["registration"],
    dependencies=[Depends(get_current_user)],
)


def _job_to_detail(job: RegistrationJob) -> RegistrationJobDetailResponse:
    success = sum(1 for i in job.items if i.status == "success")
    failed = sum(1 for i in job.items if i.status in ("failed", "skipped"))
    awaiting = sum(1 for i in job.items if i.status in ("code_sent", "password_required"))
    return RegistrationJobDetailResponse(
        id=job.id,
        status=job.status,
        proxy_id=job.proxy_id,
        delay_seconds=job.delay_seconds,
        total_count=job.total_count,
        success_count=success,
        failed_count=failed,
        awaiting_code_count=awaiting,
        created_at=job.created_at,
        completed_at=job.completed_at,
        items=[RegistrationItemResponse.model_validate(i) for i in job.items],
    )


@router.get("/jobs", response_model=list[RegistrationJobResponse])
async def list_jobs(db=Depends(get_db)):
    async with db.session_maker() as session:
        result = await session.execute(
            select(RegistrationJob).order_by(RegistrationJob.created_at.desc()).limit(50)
        )
        jobs = result.scalars().all()
    return [RegistrationJobResponse.model_validate(j) for j in jobs]


@router.get("/jobs/{job_id}", response_model=RegistrationJobDetailResponse)
async def get_job(job_id: int, db=Depends(get_db)):
    async with db.session_maker() as session:
        result = await session.execute(
            select(RegistrationJob)
            .where(RegistrationJob.id == job_id)
            .options(selectinload(RegistrationJob.items))
        )
        job = result.scalar_one_or_none()
        if not job:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Задача не найдена")
    return _job_to_detail(job)


@router.post("/jobs", response_model=RegistrationJobDetailResponse, status_code=status.HTTP_201_CREATED)
async def create_job(
    payload: RegistrationJobCreateRequest,
    db=Depends(get_db),
    registration_service=Depends(get_registration_service),
):
    try:
        async with db.session_maker() as session:
            job = await registration_service.create_job(
                session,
                payload.phones,
                proxy_id=payload.proxy_id,
                delay_seconds=payload.delay_seconds,
                default_2fa_password=payload.default_2fa_password,
            )
            result = await session.execute(
                select(RegistrationJob)
                .where(RegistrationJob.id == job.id)
                .options(selectinload(RegistrationJob.items))
            )
            job = result.scalar_one()
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    return _job_to_detail(job)


@router.post("/jobs/{job_id}/cancel", response_model=RegistrationJobDetailResponse)
async def cancel_job(
    job_id: int,
    db=Depends(get_db),
    registration_service=Depends(get_registration_service),
):
    async with db.session_maker() as session:
        job = await registration_service.cancel_job(session, job_id)
        if not job:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Задача не найдена")
        result = await session.execute(
            select(RegistrationJob)
            .where(RegistrationJob.id == job_id)
            .options(selectinload(RegistrationJob.items))
        )
        job = result.scalar_one()
    return _job_to_detail(job)


@router.post("/items/{item_id}/code", response_model=RegistrationItemResponse)
async def submit_registration_code(
    item_id: int,
    payload: RegistrationCodeRequest,
    db=Depends(get_db),
    registration_service=Depends(get_registration_service),
):
    try:
        async with db.session_maker() as session:
            item, _ = await registration_service.submit_code(
                session,
                item_id,
                payload.code,
                password=payload.password,
            )
            await session.refresh(item)
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    return RegistrationItemResponse.model_validate(item)


@router.post("/items/{item_id}/2fa", response_model=RegistrationItemResponse)
async def submit_registration_2fa(
    item_id: int,
    payload: RegistrationPasswordRequest,
    db=Depends(get_db),
    registration_service=Depends(get_registration_service),
):
    try:
        async with db.session_maker() as session:
            result = await session.execute(
                select(RegistrationItem).where(RegistrationItem.id == item_id)
            )
            item = result.scalar_one_or_none()
            if not item or not item.auth_session_id:
                raise LookupError("Задача не найдена")
            pending = registration_service.pending_auth.get(item.auth_session_id)
            if not pending or not pending.code:
                raise ValueError("Сначала введите код из SMS")

            item, _ = await registration_service.submit_code(
                session,
                item_id,
                pending.code,
                password=payload.password,
            )
            await session.refresh(item)
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    return RegistrationItemResponse.model_validate(item)
