#!/usr/bin/env python3
"""FastStarter project CLI - stdlib argparse (no extra CLI library).

From the project root (venv active, deps installed; ``.env`` optional - falls back to ``.env.example``):

    python manage.py init
    python manage.py run
    python manage.py users
    python manage.py report --name "Student Name" --id "816000000"
    python manage.py usecase
    python manage.py skills-verify
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


def _ensure_models_loaded() -> None:
    import app.models  # noqa: F401


def cmd_init(args: argparse.Namespace) -> None:
    """Create database tables (drops existing by default) and seed demo users."""
    from app.config import get_settings
    from app.database import drop_all, ensure_db_and_tables

    _ensure_models_loaded()
    if args.drop:
        print("Dropping all tables")
        try:
            drop_all()
        except Exception as exc:  # noqa: BLE001
            from app.database import is_db_not_ready_error

            if not is_db_not_ready_error(exc):
                raise
            print(f"Database not ready yet while dropping ({exc}); continuing")
    print("Creating tables")
    ensure_db_and_tables()
    print(f"Database ready ({get_settings().database_uri}).")
    if getattr(args, "seed", True):
        cmd_seed(args)


def cmd_seed(args: argparse.Namespace) -> None:
    """Insert demo users.

    bob / bobpass       (regular_user)
    admin / adminpass   (admin)
    """
    from app.database import ensure_db_and_tables, get_cli_session
    from app.models.awards import Prize, VolunteerLog
    from app.repositories.awards import AwardRepository
    from app.repositories.user import UserRepository
    from app.schemas.user import AdminCreate, RegularUserCreate
    from sqlmodel import select

    _ensure_models_loaded()
    ensure_db_and_tables()

    demo_users = [
        ("bob", "bob@example.com", "bobpass", "regular_user"),
        ("admin", "admin@example.com", "adminpass", "admin"),
    ]

    created = 0
    skipped = 0
    with get_cli_session() as session:
        repo = UserRepository(session)
        award_repo = AwardRepository(session)
        for username, email, password, role in demo_users:
            if repo.get_by_username(username):
                print(f"  skip  {username} (already exists)")
                skipped += 1
                continue
            payload_cls = AdminCreate if role == "admin" else RegularUserCreate
            repo.create(
                payload_cls(
                    username=username,
                    email=email,
                    password=password,
                    role=role,
                )
            )
            print(f"  create {username} ({role})")
            created += 1

        prize_rows = [
            {
                "name": "Campus Coffee Card",
                "description": "A warm treat for volunteering at campus events.",
                "points_required": 4,
                "category": "Wellbeing",
                "active": True,
                "stock_available": 5,
            },
            {
                "name": "Library Study Pack",
                "description": "A set of stationery essentials for active student leaders.",
                "points_required": 8,
                "category": "Academic",
                "active": True,
                "stock_available": 3,
            },
            {
                "name": "Festival Pass",
                "description": "A free pass to the student festival weekend.",
                "points_required": 12,
                "category": "Community",
                "active": True,
                "stock_available": 2,
            },
        ]
        for prize_data in prize_rows:
            existing = session.exec(select(Prize).where(Prize.name == prize_data["name"])).first()
            if existing is None:
                award_repo.create_prize(**prize_data)
                print(f"  create prize {prize_data['name']}")

        bob_user = repo.get_by_username("bob")
        admin_user = repo.get_by_username("admin")
        if bob_user and admin_user and not session.exec(select(VolunteerLog).where(VolunteerLog.student_id == bob_user.id)).all():
            award_repo.create_volunteer_log(
                student_id=bob_user.id,
                event_date="2026-09-12",
                hours=6,
                description="Mentored first-year students during orientation week.",
            )
            award_repo.create_volunteer_log(
                student_id=bob_user.id,
                event_date="2026-09-18",
                hours=4,
                description="Supported the student food drive and checked in with volunteers.",
            )
            first_log = session.exec(
                select(VolunteerLog)
                .where(VolunteerLog.student_id == bob_user.id)
                .order_by(VolunteerLog.event_date.asc())
            ).first()
            if first_log:
                award_repo.update_log_status(
                    log_id=first_log.id,
                    status="approved",
                    admin_id=admin_user.id,
                    admin_notes="Great initiative and clear service record.",
                )

    print(f"Seed done - created {created}, skipped {skipped}.")
    print("Login with bob/bobpass or admin/adminpass")


def cmd_run(args: argparse.Namespace) -> None:
    """Start the FastAPI app with Uvicorn."""
    import uvicorn

    from app.config import get_settings

    settings = get_settings()
    bind_host = args.host or settings.app_host
    bind_port = args.port or settings.app_port
    if args.reload is None:
        use_reload = settings.env.lower() != "production"
    else:
        use_reload = args.reload
    print(f"Starting FastStarter on http://{bind_host}:{bind_port} (reload={use_reload})")
    uvicorn.run(
        "app.main:app",
        host=bind_host,
        port=bind_port,
        reload=use_reload,
    )


def cmd_report(args: argparse.Namespace) -> None:
    """Build the submission package: merge judge, package transcripts, write PDF.

    Guide must (1) write ``docs/judge.md`` and (2) pull every Guide chat into
    ``docs/transcripts/*.md`` before this command. Report only packages those files.
    """
    from app.report_pdf import export_report
    from app.skill_integrity import format_report, verify

    result = export_report(
        name=args.name,
        student_id=args.student_id,
        source=None if args.src is None else Path(args.src),
        output=None if args.output is None else Path(args.output),
    )
    print()
    print("Report package:")
    print(
        f"  Judge:       {'merged docs/judge.md' if result.judge_merged else 'MISSING - Guide must run student-judge first'}"
    )
    print(
        f"  Transcripts: {result.transcript_count} chat(s) in docs/transcripts/"
        + (
            ""
            if result.transcript_count
            else " (EMPTY - Guide must pull Copilot/Cursor/OpenCode chats first)"
        )
    )
    if result.transcript_zip:
        print(f"  Zip:         {result.transcript_zip.as_posix()}")
    print(f"  PDF:         {result.pdf_path.as_posix()}")
    print(format_report(verify()))


def cmd_transcripts(args: argparse.Namespace) -> None:
    """Package agent-written markdown under docs/transcripts/ (+ zip)."""
    from app.transcript_export import package_transcripts

    result = package_transcripts(make_zip=not args.no_zip)
    if result.found == 0:
        print(
            "Warning: no chat markdown in docs/transcripts/. "
            "The Guide agent must pull every Guide chat for this project "
            "(Copilot Agent, Cursor, or OpenCode) into docs/transcripts/<slug>.md first."
        )
        raise SystemExit(2)
    print(f"Submission package ready: {result.out_dir}")
    if result.zip_path:
        print(f"Zip ready: {result.zip_path.as_posix()}")


def cmd_users(args: argparse.Namespace) -> None:
    """Print all users in the database."""
    from app.database import get_cli_session
    from app.models.user import User
    from sqlmodel import select

    with get_cli_session() as session:
        users = session.exec(select(User)).all()
        print("Users:")
        for user in users:
            print(f"  - {user.id}: {user.username} ({user.role})")


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="FastStarter CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)

    init_parser = subparsers.add_parser("init", help="Create DB tables and seed demo users")
    init_parser.add_argument("--drop", action="store_true", help="Drop tables before creating them")
    init_parser.add_argument("--no-drop", action="store_false", dest="drop", help="Keep existing tables")
    init_parser.set_defaults(drop=True)
    init_parser.add_argument("--no-seed", action="store_false", dest="seed", help="Skip seeding demo users")
    init_parser.set_defaults(seed=True)
    init_parser.set_defaults(func=cmd_init)

    seed_parser = subparsers.add_parser("seed", help="Insert demo users")
    seed_parser.set_defaults(func=cmd_seed)

    run_parser = subparsers.add_parser("run", help="Run the app with uvicorn")
    run_parser.add_argument("--host", default=None)
    run_parser.add_argument("--port", type=int, default=None)
    run_parser.add_argument("--reload", action="store_true")
    run_parser.add_argument("--no-reload", action="store_false", dest="reload")
    run_parser.set_defaults(reload=None)
    run_parser.set_defaults(func=cmd_run)

    report_parser = subparsers.add_parser("report", help="Build report package")
    report_parser.add_argument("--name", required=True)
    report_parser.add_argument("--id", dest="student_id", required=True)
    report_parser.add_argument("--src", default=None)
    report_parser.add_argument("--output", default=None)
    report_parser.set_defaults(func=cmd_report)

    transcripts_parser = subparsers.add_parser("transcripts", help="Package transcript markdown")
    transcripts_parser.add_argument("--no-zip", action="store_true", help="Do not create zip archive")
    transcripts_parser.set_defaults(func=cmd_transcripts)

    users_parser = subparsers.add_parser("users", help="List users")
    users_parser.set_defaults(func=cmd_users)

    return parser


def main() -> None:
    parser = _build_parser()
    args = parser.parse_args()
    if hasattr(args, "func"):
        args.func(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()

