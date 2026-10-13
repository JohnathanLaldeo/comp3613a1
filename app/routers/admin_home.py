from fastapi import Form, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse

from app.dependencies.auth import AdminDep
from app.dependencies.session import SessionDep
from app.repositories.awards import AwardRepository
from app.services.awards_service import AwardService
from app.utilities.flash import flash
from . import router, templates


@router.get("/admin", response_class=HTMLResponse)
async def admin_home_view(
    request: Request,
    user: AdminDep,
    db: SessionDep,
):
    award_service = AwardService(AwardRepository(db))
    context = award_service.get_admin_dashboard()
    context["user"] = user
    return templates.TemplateResponse(
        request=request,
        name="admin_dashboard.html",
        context=context,
    )


@router.get("/admin/reviews", response_class=HTMLResponse)
async def admin_review_queue_view(
    request: Request,
    user: AdminDep,
    db: SessionDep,
):
    award_service = AwardService(AwardRepository(db))
    context = award_service.get_admin_queue()
    context["user"] = user
    return templates.TemplateResponse(
        request=request,
        name="admin_queue.html",
        context=context,
    )


@router.get("/admin/review/{log_id}", response_class=HTMLResponse)
async def admin_review_detail(
    request: Request,
    user: AdminDep,
    db: SessionDep,
    log_id: int,
):
    award_service = AwardService(AwardRepository(db))
    log = award_service.get_log_for_review(log_id)
    if log is None:
        flash(request, "Volunteer log not found", "danger")
        return RedirectResponse(url=request.url_for("admin_review_queue_view"), status_code=status.HTTP_303_SEE_OTHER)

    return templates.TemplateResponse(
        request=request,
        name="admin_review.html",
        context={"user": user, "log": log},
    )


@router.post("/admin/review/{log_id}/approve", response_class=HTMLResponse)
async def admin_approve_log(
    request: Request,
    user: AdminDep,
    db: SessionDep,
    log_id: int,
    admin_notes: str = Form(default=""),
):
    award_service = AwardService(AwardRepository(db))
    award_service.decide_log(
        log_id=log_id,
        admin_id=user.id,
        action="approved",
        admin_notes=admin_notes,
    )
    flash(request, "Volunteer hours approved.")
    return RedirectResponse(url=request.url_for("admin_review_queue_view"), status_code=status.HTTP_303_SEE_OTHER)


@router.post("/admin/review/{log_id}/reject", response_class=HTMLResponse)
async def admin_reject_log(
    request: Request,
    user: AdminDep,
    db: SessionDep,
    log_id: int,
    admin_notes: str = Form(default=""),
):
    award_service = AwardService(AwardRepository(db))
    try:
        award_service.decide_log(
            log_id=log_id,
            admin_id=user.id,
            action="rejected",
            admin_notes=admin_notes,
        )
    except ValueError as exc:
        flash(request, str(exc), "danger")
        return RedirectResponse(
            url=request.url_for("admin_review_detail", log_id=log_id),
            status_code=status.HTTP_303_SEE_OTHER,
        )
    flash(request, "Volunteer hours rejected.")
    return RedirectResponse(url=request.url_for("admin_review_queue_view"), status_code=status.HTTP_303_SEE_OTHER)
