from datetime import UTC, datetime
from typing import Any, cast

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient, Response
from sqlalchemy import select

from uvts_api.adapters.db.models import Document
from uvts_api.adapters.db.models import TestRun as RunModel
from uvts_api.schemas.workspace import (
    QuestionSet,
    QuestionSetSource,
    QuestionSetStatus,
    WorkspaceState,
)


async def create_setup(
    client: AsyncClient,
    *,
    image: tuple[str, bytes, str] = ("speaker.png", b"product-image", "image/png"),
    description: str = "A compact smart speaker for music and voice controls.",
    total_questions: int = 9,
) -> Response:
    await client.post("/api/v1/session")
    return await client.post(
        "/api/v1/tests",
        data={
            "productDescription": description,
            "totalQuestions": str(total_questions),
        },
        files={"productImage": image},
    )


async def save_setup(
    client: AsyncClient,
    test_id: str,
    *,
    image: tuple[str, bytes, str] | None = None,
    description: str = "A compact smart speaker for music and voice controls.",
    total_questions: int = 9,
) -> Response:
    files = {"productImage": image} if image is not None else None
    return await client.put(
        f"/api/v1/tests/{test_id}/configuration",
        data={
            "productDescription": description,
            "totalQuestions": str(total_questions),
        },
        files=files,
    )


async def test_product_setup_creates_a_test_without_a_manual(
    app: FastAPI, client: AsyncClient
) -> None:
    response = await create_setup(
        client,
        description="  A compact smart speaker for music and voice controls.  ",
        total_questions=7,
    )

    assert response.status_code == 201
    body = response.json()
    assert body["schemaVersion"] == 2
    assert body["currentStage"] == "configuration"
    assert body["status"] == "draft"
    assert body["manual"] is None
    assert body["questionSet"] is None
    assert body["configuration"] == {
        "version": 1,
        "totalQuestions": 7,
        "productImage": {
            "id": body["configuration"]["productImage"]["id"],
            "filename": "speaker.png",
            "contentType": "image/png",
            "sizeBytes": len(b"product-image"),
        },
        "productDescription": "A compact smart speaker for music and voice controls.",
    }
    async with app.state.session_factory() as db:
        images = list(
            (
                await db.scalars(
                    select(Document).where(
                        Document.test_run_id == body["id"],
                        Document.role == "product_image",
                    )
                )
            ).all()
        )
        assert len(images) == 1


async def test_update_retains_or_transactionally_replaces_the_product_image(
    app: FastAPI, client: AsyncClient
) -> None:
    created = await create_setup(client)
    test_id = str(created.json()["id"])
    first_image_id = created.json()["configuration"]["productImage"]["id"]
    async with app.state.session_factory() as db:
        first_image = await db.get(Document, first_image_id)
        assert first_image is not None
        first_storage_key = first_image.storage_key

    retained = await save_setup(
        client,
        test_id,
        description="Updated product description",
        total_questions=4,
    )
    assert retained.status_code == 200
    assert retained.json()["configuration"]["productImage"]["id"] == first_image_id
    assert retained.json()["configuration"]["version"] == 2

    replaced = await save_setup(
        client,
        test_id,
        image=("replacement.webp", b"replacement-image", "image/webp"),
    )
    assert replaced.status_code == 200
    assert replaced.json()["configuration"]["productImage"]["id"] != first_image_id
    with pytest.raises(FileNotFoundError):
        await app.state.document_storage.local_path(first_storage_key)


async def test_failed_image_replacement_keeps_the_previous_image(
    app: FastAPI,
    client: AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    created = await create_setup(client)
    test_id = str(created.json()["id"])
    first_image_id = created.json()["configuration"]["productImage"]["id"]

    def fail_state_update(*args: object, **kwargs: object) -> None:
        del args, kwargs
        raise RuntimeError("simulated state write failure")

    monkeypatch.setattr(
        "uvts_api.services.configuration.update_state",
        fail_state_update,
    )
    failed = await save_setup(
        client,
        test_id,
        image=("replacement.png", b"replacement-image", "image/png"),
    )
    assert failed.status_code == 500
    async with app.state.session_factory() as db:
        current = await db.scalar(
            select(Document).where(
                Document.test_run_id == test_id,
                Document.role == "product_image",
            )
        )
        assert current is not None
        assert current.id == first_image_id


async def test_configuration_validation_errors(client: AsyncClient) -> None:
    await client.post("/api/v1/session")
    missing = await client.post(
        "/api/v1/tests",
        data={"productDescription": "A product", "totalQuestions": "9"},
    )
    not_image = await create_setup(client, image=("notes.txt", b"not-image", "text/plain"))
    empty = await create_setup(client, image=("empty.png", b"", "image/png"))
    blank_description = await create_setup(client, description="   ")
    invalid_count = await create_setup(client, total_questions=16)

    assert missing.status_code == 422
    assert not_image.json()["error"]["code"] == "product_image_type"
    assert empty.json()["error"]["code"] == "product_image_empty"
    assert blank_description.json()["error"]["code"] == "product_description_required"
    assert invalid_count.status_code == 422


async def test_configuration_is_private_and_locked_after_confirmation(
    app: FastAPI, client: AsyncClient
) -> None:
    created = await create_setup(client, total_questions=1)
    test_id = str(created.json()["id"])
    async with app.state.session_factory() as db:
        test = await db.get(RunModel, test_id)
        assert test is not None
        state = WorkspaceState.model_validate(test.state)
        state = state.model_copy(
            update={
                "question_set": QuestionSet(
                    id="set-1",
                    status=QuestionSetStatus.CONFIRMED,
                    source=QuestionSetSource.PRODUCT_CONTEXT,
                    configuration_version=state.configuration.version,
                    confirmed_at=datetime.now(UTC),
                    items=[{"id": "q1", "text": "How do I start?"}],
                )
            }
        )
        test.state = state.model_dump(mode="json", by_alias=True)
        await db.commit()

    locked = await save_setup(client, test_id)
    assert locked.status_code == 409
    assert locked.json()["error"]["code"] == "configuration_locked"

    transport = ASGITransport(app=app, raise_app_exceptions=False)
    async with AsyncClient(transport=transport, base_url="http://test") as stranger:
        await stranger.post("/api/v1/session")
        hidden = await save_setup(stranger, test_id)
    assert hidden.status_code == 404
    assert cast(dict[str, Any], hidden.json())["error"]["code"] == "test_not_found"
