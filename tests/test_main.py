from app.main import app
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_when_get_root_then_returns_welcome_message():
    async with AsyncClient(app=app, base_url="http://test") as ac:
        response = await ac.get("/")
    assert response.status_code == 200
    assert response.json() == {"message": "Welcome to the public GBADs database tables!"}


@pytest.mark.asyncio
async def test_when_head_root_then_returns_200():
    async with AsyncClient(app=app, base_url="http://test") as ac:
        response = await ac.head("/")
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_when_get_docs_then_returns_html():
    async with AsyncClient(app=app, base_url="http://test") as ac:
        response = await ac.get("/docs")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]


@pytest.mark.asyncio
async def test_when_get_openapi_json_then_returns_json():
    async with AsyncClient(app=app, base_url="http://test") as ac:
        response = await ac.get("/openapi.json")
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/json"
