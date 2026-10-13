from fastapi import Form, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse

from app.dependencies.auth import AuthDep
from app.dependencies.session import SessionDep
from app.repositories.awards import AwardRepository
from app.services.awards_service import AwardService
from app.utilities.flash import flash
from . import router, templates


@router.get("/app", response_class=HTMLResponse)
async def user_home_view(
    request: Request,
    user: AuthDep,
    db: SessionDep,
):
    award_service = AwardService(AwardRepository(db))
    context = award_service.get_student_dashboard(user.id)
    context["user"] = user
    return templates.TemplateResponse(
        request=request,
        name="student_dashboard.html",
        context=context,
    )


@router.get("/app/hours", response_class=HTMLResponse)
async def user_hours_view(
    request: Request,
    user: AuthDep,
    db: SessionDep,
):
    award_service = AwardService(AwardRepository(db))
    context = award_service.get_student_hours(user.id)
    context["user"] = user
    return templates.TemplateResponse(
        request=request,
        name="student_hours.html",
        context=context,
    )


@router.get("/app/hours/new", response_class=HTMLResponse)
async def user_hours_new_view(
    request: Request,
    user: AuthDep,
):
    return templates.TemplateResponse(
        request=request,
        name="student_hours_form.html",
        context={"user": user},
    )


@router.post("/app/hours/new", response_class=HTMLResponse)
async def user_hours_create(
    request: Request,
    user: AuthDep,
    db: SessionDep,
    event_date: str = Form(...),
    hours: int = Form(...),
    activity: str = Form(...),
    notes: str = Form(""),
):
    award_service = AwardService(AwardRepository(db))
    try:
        award_service.create_log(
            student_id=user.id,
            event_date=__import__("datetime").date.fromisoformat(event_date),
            hours=hours,
            activity=activity,
            notes=notes,
        )
        flash(request, "Volunteer hours submitted for approval.")
    except ValueError as exc:
        flash(request, str(exc), "danger")
    return RedirectResponse(url=request.url_for("user_hours_view"), status_code=status.HTTP_303_SEE_OTHER)


@router.get("/app/prizes", response_class=HTMLResponse)
async def user_prizes_view(
    request: Request,
    user: AuthDep,
    db: SessionDep,
):
    award_service = AwardService(AwardRepository(db))
    context = award_service.get_prize_catalog(user.id)
    context["user"] = user
    return templates.TemplateResponse(
        request=request,
        name="student_prizes.html",
        context=context,
    )


@router.get("/app/prizes/{prize_id}/confirm", response_class=HTMLResponse)
async def user_prize_confirm_view(
    request: Request,
    user: AuthDep,
    db: SessionDep,
    prize_id: int,
):
    service = AwardService(AwardRepository(db))
    try:
        context = service.get_prize_confirmation(
            student_id=user.id,
            prize_id=prize_id,
        )
        context["user"] = user
        return templates.TemplateResponse(
            request=request,
            name="student_prize_confirm.html",
            context=context,
        )
    except ValueError as exc:
        flash(request, str(exc), "danger")
        return RedirectResponse(
            url=request.url_for("user_prizes_view"),
            status_code=status.HTTP_303_SEE_OTHER,
        )


@router.post("/app/prizes/{prize_id}/redeem", response_class=HTMLResponse)
async def user_prize_redeem(
    request: Request,
    user: AuthDep,
    db: SessionDep,
    prize_id: int,
):
    award_service = AwardService(AwardRepository(db))
    try:
        award_service.redeem_prize(student_id=user.id, prize_id=prize_id)
        flash(request, "Prize redeemed successfully.")
    except ValueError as exc:
        flash(request, str(exc), "danger")
    return RedirectResponse(url=request.url_for("user_prizes_view"), status_code=status.HTTP_303_SEE_OTHER)