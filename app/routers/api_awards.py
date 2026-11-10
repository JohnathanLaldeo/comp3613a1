"""Student Awards JSON API (used by Postman and API tests).

Routes stay thin: bind the request, call AwardService, map domain errors to
HTTP status codes. All persistence lives in AwardRepository.
"""

from typing import Literal, Optional

from fastapi import HTTPException, Query, status

from app.dependencies.auth import ApiAdminDep, ApiUserDep
from app.dependencies.session import SessionDep
from app.repositories.awards import AwardRepository
from app.repositories.user import UserRepository
from app.schemas.awards import (
    BalanceRead,
    DashboardRead,
    LogCreate,
    LogDecision,
    LogRead,
    LoginRequest,
    PrizeRead,
    RedemptionRead,
    TokenResponse,
)
from app.services.auth_service import AuthService
from app.services.awards_service import AwardService
from app.utilities.errors import ConflictError, NotFoundError
from . import api_router


def _service(db) -> AwardService:
    return AwardService(AwardRepository(db))


def _http_error(exc: ValueError) -> HTTPException:
    if isinstance(exc, NotFoundError):
        code = status.HTTP_404_NOT_FOUND
    elif isinstance(exc, ConflictError):
        code = status.HTTP_409_CONFLICT
    else:
        code = status.HTTP_400_BAD_REQUEST
    return HTTPException(status_code=code, detail=str(exc))


# --- auth -------------------------------------------------------------------


@api_router.post("/login", response_model=TokenResponse)
async def api_login(body: LoginRequest, db: SessionDep):
    user_repo = UserRepository(db)
    token = AuthService(user_repo).authenticate_user(body.username, body.password)
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
        )
    user = user_repo.get_by_username(body.username)
    return TokenResponse(access_token=token, role=user.role)


# --- student ----------------------------------------------------------------


@api_router.get("/logs", response_model=list[LogRead])
async def api_list_my_logs(user: ApiUserDep, db: SessionDep):
    return _service(db).list_student_logs(user.id)


@api_router.post("/logs", response_model=LogRead, status_code=status.HTTP_201_CREATED)
async def api_create_log(body: LogCreate, user: ApiUserDep, db: SessionDep):
    try:
        return _service(db).create_log(
            student_id=user.id,
            event_date=body.event_date,
            hours=body.hours,
            activity=body.activity,
            notes=body.notes,
        )
    except ValueError as exc:
        raise _http_error(exc)


@api_router.get("/me/balance", response_model=BalanceRead)
async def api_my_balance(user: ApiUserDep, db: SessionDep):
    return _service(db).get_balance(user.id)


@api_router.get("/prizes", response_model=list[PrizeRead])
async def api_list_prizes(user: ApiUserDep, db: SessionDep):
    return _service(db).list_prizes()


@api_router.get("/redemptions", response_model=list[RedemptionRead])
async def api_list_my_redemptions(user: ApiUserDep, db: SessionDep):
    return _service(db).list_student_redemptions(user.id)


@api_router.post(
    "/prizes/{prize_id}/redemptions",
    response_model=RedemptionRead,
    status_code=status.HTTP_201_CREATED,
)
async def api_redeem_prize(prize_id: int, user: ApiUserDep, db: SessionDep):
    try:
        return _service(db).redeem_prize(student_id=user.id, prize_id=prize_id)
    except ValueError as exc:
        raise _http_error(exc)


# --- admin ------------------------------------------------------------------


@api_router.get("/admin/logs", response_model=list[LogRead])
async def api_admin_list_logs(
    admin: ApiAdminDep,
    db: SessionDep,
    log_status: Optional[Literal["pending", "approved", "rejected"]] = Query(default=None, alias="status"),
):
    return _service(db).list_logs(log_status)


@api_router.patch("/admin/logs/{log_id}", response_model=LogRead)
async def api_admin_decide_log(log_id: int, body: LogDecision, admin: ApiAdminDep, db: SessionDep):
    try:
        return _service(db).decide_log(
            log_id=log_id,
            admin_id=admin.id,
            action=body.status,
            admin_notes=body.admin_notes,
        )
    except ValueError as exc:
        raise _http_error(exc)


@api_router.get("/admin/dashboard", response_model=DashboardRead)
async def api_admin_dashboard(admin: ApiAdminDep, db: SessionDep):
    return _service(db).get_admin_dashboard()
