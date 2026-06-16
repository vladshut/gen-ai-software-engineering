import pytest
import os
import asyncio
from httpx import AsyncClient, ASGITransport

# Set test DB before importing app
os.environ["DATABASE_URL"] = "test_tickets.db"

from src.main import app
from src.db.database import init_db, get_db


@pytest.fixture(scope="session")
def event_loop():
    """Create a single event loop for the test session."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(autouse=True)
async def setup_db():
    """Initialize fresh DB before each test, cleanup after."""
    await init_db()
    yield
    # Cleanup: drop all data after each test
    async with get_db() as db:
        await db.execute("DELETE FROM tickets")
        await db.commit()


@pytest.fixture
async def client():
    """Async HTTP test client."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.fixture
def sample_ticket_data():
    """Valid ticket creation payload."""
    return {
        "customer_id": "CUST-001",
        "customer_email": "john@example.com",
        "customer_name": "John Doe",
        "subject": "Cannot access my account",
        "description": "I've been unable to log in since yesterday. Getting a 403 error when trying to access my dashboard.",
        "tags": ["login", "access"],
        "metadata": {
            "source": "web_form",
            "browser": "Chrome 120",
            "device_type": "desktop"
        }
    }


@pytest.fixture
def fixtures_path():
    return os.path.join(os.path.dirname(__file__), "fixtures")
