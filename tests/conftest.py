import os
import tempfile
import uuid
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import sessionmaker
from sqlalchemy.engine import make_url
from app.db.base import Base
from app.db.session import get_db
from app.core.config import get_settings
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


@pytest.fixture()
def postgres_client():
    """Provide an API client whose tables exist only in a newly-created test schema."""
    database_url = get_settings().database_url

    url = make_url(database_url)
    if not url.drivername.startswith("postgresql"):
        pytest.skip("DATABASE_URL is not PostgreSQL; PostgreSQL integration tests were not run.")

    # The generated identifier is never derived from user or connection input.
    # A translated engine directs metadata, ORM queries, foreign keys, and DDL
    # for schema-less models to this schema rather than public.
    schema = f"ledger_test_{uuid.uuid4().hex}"
    admin_engine = create_engine(database_url, pool_pre_ping=True)
    try:
        with admin_engine.connect() as connection:
            connection.execute(text("SELECT 1"))
    except SQLAlchemyError:
        admin_engine.dispose()
        pytest.skip("PostgreSQL integration tests were not run: DATABASE_URL is unreachable from this runtime.")
    engine = admin_engine
    created_schema = False
    try:
        with admin_engine.begin() as connection:
            connection.execute(text(f'CREATE SCHEMA "{schema}"'))
            created_schema = True

        engine = admin_engine.execution_options(schema_translate_map={None: schema})
        Base.metadata.create_all(engine)

        # Prove the exact test tables were created in the isolated schema before
        # any API request is permitted. No public table is inspected or altered.
        with admin_engine.connect() as connection:
            tables = set(connection.execute(text("""
                SELECT table_name
                FROM information_schema.tables
                WHERE table_schema = :schema AND table_name IN ('accounts', 'transactions')
            """), {"schema": schema}).scalars())
        if tables != {"accounts", "transactions"}:
            pytest.fail("Test schema isolation could not be verified; no API operations were run.")

        TestSession = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)

        def override_db():
            db = TestSession()
            try:
                yield db
            finally:
                db.close()

        fastapi_app.dependency_overrides[get_db] = override_db

        with TestClient(fastapi_app) as test_client:
            yield test_client
    finally:
        fastapi_app.dependency_overrides.pop(get_db, None)
        if created_schema:
            # This schema was created above with a random name in this fixture;
            # dropping it cannot affect existing public-schema data or tables.
            with admin_engine.begin() as connection:
                connection.execute(text(f'DROP SCHEMA "{schema}" CASCADE'))
        engine.dispose()
        admin_engine.dispose()
