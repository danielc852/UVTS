from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient


async def test_bootstrap_sets_private_opaque_cookie_and_is_idempotent(client: AsyncClient) -> None:
    first = await client.post("/api/v1/session")
    first_cookie = client.cookies.get("uvts_session")
    second = await client.post("/api/v1/session")

    assert first.status_code == 200
    assert first_cookie
    assert client.cookies.get("uvts_session") == first_cookie
    set_cookie = first.headers["set-cookie"].lower()
    assert "httponly" in set_cookie
    assert "samesite=lax" in set_cookie
    assert "uvts_session=" in set_cookie
    assert "max-age" not in set_cookie
    assert "expires" not in set_cookie
    assert second.json()["authenticated"] is True


async def test_test_reads_are_scoped_to_owning_session(app: FastAPI) -> None:
    transport = ASGITransport(app=app, raise_app_exceptions=False)
    async with (
        AsyncClient(transport=transport, base_url="http://test") as owner,
        AsyncClient(transport=transport, base_url="http://test") as stranger,
    ):
        await owner.post("/api/v1/session")
        created = await owner.post(
            "/api/v1/tests",
            json={"currentStage": "configuration", "questions": [], "evaluation": []},
        )
        test_id = created.json()["id"]
        await stranger.post("/api/v1/session")

        owned = await owner.get(f"/api/v1/tests/{test_id}")
        hidden = await stranger.get(f"/api/v1/tests/{test_id}")
        absent = await stranger.get("/api/v1/tests/not-a-real-id")

    assert owned.status_code == 200
    assert owned.json()["currentStage"] == "configuration"
    assert owned.json()["configuration"]["totalQuestions"] == 9
    assert hidden.status_code == absent.status_code == 404
    assert hidden.json()["error"]["code"] == absent.json()["error"]["code"] == "test_not_found"


async def test_missing_session_and_invalid_body_use_error_envelope(client: AsyncClient) -> None:
    missing = await client.get("/api/v1/tests/anything", headers={"X-Request-ID": "req-7"})
    await client.post("/api/v1/session")
    invalid = await client.post("/api/v1/tests", json={"currentStage": "unknown"})

    assert missing.status_code == 401
    assert missing.json()["request_id"] == "req-7"
    assert missing.json()["error"]["code"] == "session_required"
    assert invalid.status_code == 422
    assert invalid.json()["error"]["code"] == "validation_error"
