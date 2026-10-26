import os
import tempfile
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

os.environ["DATABASE_URL"] = "sqlite:///./ignored-by-test.db"
from app.db.base import Base
from app.db.session import get_db
import app.models  # noqa: F401
from app.main import app as fastapi_app


@pytest.fixture()
def client():
    fd, path = tempfile.mkstemp(suffix=".sqlite3")
    os.close(fd)
    engine = create_engine(f"sqlite:///{path}", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine, expire_on_commit=False)
    def override_db():
        db = Session()
        try:
            yield db
        finally:
            db.close()
    fastapi_app.dependency_overrides[get_db] = override_db
    with TestClient(fastapi_app) as test_client:
        yield test_client
    fastapi_app.dependency_overrides.clear()
    engine.dispose()
    os.unlink(path)


def create_account(client, name="Ada"):
    response = client.post("/api/v1/accounts", json={"name": name})
    assert response.status_code == 201
    return response.json()
