import os
import tempfile

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.main import app


@pytest.fixture(scope="session")
def client() -> TestClient:
    with tempfile.TemporaryDirectory() as tmp:
        storage_path = os.path.join(tmp, "storage")
        vectors_path = os.path.join(tmp, "vectors")

        from app.core.config import settings
        from app.db import session as db_session

        settings.LOCAL_STORAGE_PATH = storage_path
        settings.VECTOR_INDEX_PATH = vectors_path
        settings.EMBEDDING_BACKEND = "hash"
        settings.RERANKER_ENABLED = False
        settings.LLM_BACKEND = "fake"

        db_session.engine = create_engine(
            f"sqlite:///{os.path.join(tmp, 'test.db')}",
            connect_args={"check_same_thread": False},
        )
        db_session.SessionLocal = sessionmaker(
            autocommit=False, autoflush=False, bind=db_session.engine
        )
        db_session.create_all_tables()

        with TestClient(app) as test_client:
            from app.core.security import hash_password
            from app.models import User

            with db_session.SessionLocal() as session:
                session.add(
                    User(
                        username="testadmin",
                        email="admin@test.local",
                        password_hash=hash_password("testpass"),
                        role="admin",
                    )
                )
                session.commit()

            login = test_client.post(
                "/api/v1/auth/login",
                json={"username": "testadmin", "password": "testpass"},
            )
            assert login.status_code == 200, login.text
            test_client.headers["Authorization"] = (
                f"Bearer {login.json()['access_token']}"
            )
            yield test_client

        db_session.engine.dispose()
