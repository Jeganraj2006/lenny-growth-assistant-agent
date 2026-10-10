import pytest
import pytest_asyncio
from app.db.session import init_db, engine

@pytest_asyncio.fixture(scope="session", autouse=True)
async def initialize_test_database():
    """Ensure DB extensions, tables, and column migrations are initialized for tests."""
    await init_db()
    yield
    await engine.dispose()
