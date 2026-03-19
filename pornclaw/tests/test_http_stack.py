from fastapi import Depends, FastAPI
from httpx import ASGITransport, AsyncClient
import pytest


@pytest.mark.anyio
async def test_minimal_async_http_round_trip() -> None:
    app = FastAPI()

    async def async_dep() -> str:
        return "dep-ok"

    @app.get("/")
    async def read_root(dep: str = Depends(async_dep)) -> dict[str, str]:
        return {"ok": dep}

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.get("/")

    assert response.status_code == 200
    assert response.json() == {"ok": "dep-ok"}
