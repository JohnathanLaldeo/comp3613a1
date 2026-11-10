"""Shared pytest fixtures for the Student Awards app.

Unit tests (test_unit_awards.py) use a fake repository and never touch a
database. Integration tests (test_integration_awards.py) run the real FastAPI
app through TestClient against a fresh SQLite file database per test.
"""

import os
import sys
import tempfile
from pathlib import Path

# --- Environment must be set before any `app` import reads settings. --------
ROOT = Path(__file__).resolve().parent.parent
os.chdir(ROOT)  # templates/static are loaded from relative "app/..." paths
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# Never let tests point at the real (Postgres) database from .env.
_unused_db = (Path(tempfile.gettempdir()) / "comp3613_pytest_unused.db").as_posix()
os.environ["DATABASE_URI"] = f"sqlite:///{_unused_db}"
os.environ["ENV"] = "testing"
os.environ.setdefault("SECRET_KEY", "pytest-secret-key-at-least-32-bytes-long")

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlmodel import Session, SQLModel, create_engine  # noqa: E402

import app.models  # noqa: E402,F401  (registers every table on the metadata)
from app.database import get_session  # noqa: E402
from app.main import app as fastapi_app  # noqa: E402
from app.models.user import User  # noqa: E402
from app.utilities.security import encrypt_password  # noqa: E402

STUDENT_USERNAME = "student1"
STUDENT_PASSWORD = "studentpass"
ADMIN_USERNAME = "admin1"
ADMIN_PASSWORD = "adminpass"


@pytest.fixture
def engine(tmp_path):
    """A brand-new SQLite database for each test."""
    test_engine = create_engine(
        f"sqlite:///{(tmp_path / 'test.db').as_posix()}",
        connect_args={"check_same_thread": False},
    )
    SQLModel.metadata.create_all(test_engine)
    yield test_engine
    test_engine.dispose()


@pytest.fixture
def db(engine):
    """Session the test uses to seed data and check results."""
    with Session(engine) as session:
        yield session


@pytest.fixture
def app(engine):
    """The real FastAPI app, with its DB session swapped for the test database."""

    def _get_test_session():
        with Session(engine) as session:
            yield session

    fastapi_app.dependency_overrides[get_session] = _get_test_session
    yield fastapi_app
    fastapi_app.dependency_overrides.clear()


def _create_user(db: Session, username: str, password: str, role: str) -> User:
    user = User(
        username=username,
        email=f"{username}@example.com",
        password=encrypt_password(password),
        role=role,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture
def student_user(db):
    return _create_user(db, STUDENT_USERNAME, STUDENT_PASSWORD, "regular_user")


@pytest.fixture
def admin_user(db):
    return _create_user(db, ADMIN_USERNAME, ADMIN_PASSWORD, "admin")


def _login(app, username: str, password: str) -> TestClient:
    """Log in through the real /login form; the client keeps the access_token cookie."""
    client = TestClient(app)
    response = client.post(
        "/login",
        data={"username": username, "password": password},
        follow_redirects=False,
    )
    assert response.status_code == 303, response.text
    assert client.cookies.get("access_token"), "login did not set access_token cookie"
    return client


@pytest.fixture
def anon_client(app):
    return TestClient(app)


@pytest.fixture
def student_client(app, student_user):
    return _login(app, STUDENT_USERNAME, STUDENT_PASSWORD)


@pytest.fixture
def admin_client(app, admin_user):
    return _login(app, ADMIN_USERNAME, ADMIN_PASSWORD)
