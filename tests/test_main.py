import pytest
from httpx import AsyncClient
import importlib


@pytest.fixture(scope="module")
def app():
    """Import the FastAPI `app` after patching TailAdapter.initialize to avoid loading large resources during tests."""
    # Patch the TailAdapter initialize to be a no-op before importing app.main
    try:
        import app.adapters.tail_adapter as tail_mod

        def _noop_initialize(self=None):
            return None

        # Patch both the class method and the instance (defensive)
        tail_mod.TailAdapter.initialize = _noop_initialize
        try:
            tail_mod.TailAdapterInstance.initialize = lambda: None
        except Exception:
            # If the instance isn't available yet, that's fine.
            pass
    except Exception:
        # If tail_adapter cannot be imported for some reason, continue and let import fail naturally.
        pass

    # Now import the app module (will use the patched initialize)
    import app.main as main_mod
    importlib.reload(main_mod)
    return main_mod.app


@pytest.mark.asyncio
async def test_when_get_root_then_returns_welcome_message(app):
    async with AsyncClient(app=app, base_url="http://test") as ac:
        response = await ac.get("/")
    assert response.status_code == 200
    assert response.json() == {"message": "Welcome to the public GBADs database tables!"}


@pytest.mark.asyncio
async def test_when_head_root_then_returns_200(app):
    async with AsyncClient(app=app, base_url="http://test") as ac:
        response = await ac.head("/")
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_when_get_docs_then_returns_html(app):
    async with AsyncClient(app=app, base_url="http://test") as ac:
        response = await ac.get("/docs")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]


@pytest.mark.asyncio
async def test_when_get_openapi_json_then_returns_json(app):
    async with AsyncClient(app=app, base_url="http://test") as ac:
        response = await ac.get("/openapi.json")
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/json"
