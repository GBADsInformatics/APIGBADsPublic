# tests/test_main.py

import pytest
from httpx import AsyncClient
from app.main import app

@pytest.mark.asyncio
async def test_root_get():
    async with AsyncClient(app=app, base_url="http://test") as ac:
        response = await ac.get("/")
    assert response.status_code == 200
    assert response.json() == {"message": "Welcome to the public GBADs database tables!"}

@pytest.mark.asyncio
async def test_root_head():
    async with AsyncClient(app=app, base_url="http://test") as ac:
        response = await ac.head("/")
    assert response.status_code == 200

@pytest.mark.asyncio
async def test_docs_available():
    async with AsyncClient(app=app, base_url="http://test") as ac:
        response = await ac.get("/docs")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]

@pytest.mark.asyncio
async def test_openapi_json():
    async with AsyncClient(app=app, base_url="http://test") as ac:
        response = await ac.get("/openapi.json")
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/json"