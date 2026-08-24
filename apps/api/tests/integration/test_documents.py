from copy import deepcopy
from pathlib import Path

from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select

from tests.pdf_helpers import write_pdf
from uvts_api.adapters.db.models import Document
from uvts_api.adapters.db.models import TestRun as RunModel


async def test_upload_view_range_and_delete_manual(
    client: AsyncClient, app: FastAPI, tmp_path: Path
) -> None:
    source = write_pdf(tmp_path / "guide.pdf", pages=2)
    await client.post("/api/v1/session")

    with source.open("rb") as pdf:
        uploaded = await client.post(
            "/api/v1/tests/manual",
            files={"file": ("guide.pdf", pdf, "application/pdf")},
        )

    assert uploaded.status_code == 202
    body = uploaded.json()
    test_id = body["id"]
    assert body["currentStage"] == "configuration"
    assert body["manual"]["filename"] == "guide.pdf"
    assert body["manual"]["pageCount"] == 2
    assert body["manualUpload"] is None

    content = await client.get(f"/api/v1/tests/{test_id}/manual/content")
    partial = await client.get(
        f"/api/v1/tests/{test_id}/manual/content", headers={"Range": "bytes=0-7"}
    )
    assert content.status_code == 200
    assert content.headers["content-type"] == "application/pdf"
    assert content.headers["content-disposition"].startswith("inline")
    assert content.headers["cache-control"] == "private, no-store"
    assert partial.status_code == 206
    assert len(partial.content) == 8

    deleted = await client.delete(f"/api/v1/tests/{test_id}/manual")
    assert deleted.status_code == 200
    assert deleted.json()["currentStage"] == "upload"
    assert deleted.json()["manual"] is None
    async with app.state.session_factory() as db:
        assert list((await db.scalars(select(Document))).all()) == []


async def test_upload_type_and_owner_are_private(
    app: FastAPI, client: AsyncClient, tmp_path: Path
) -> None:
    await client.post("/api/v1/session")
    wrong = await client.post(
        "/api/v1/tests/manual",
        files={"file": ("notes.txt", b"not a pdf", "text/plain")},
    )
    assert wrong.status_code == 422
    assert wrong.json()["error"]["message"] == "Upload a PDF file."

    source = write_pdf(tmp_path / "private.pdf")
    with source.open("rb") as pdf:
        uploaded = await client.post(
            "/api/v1/tests/manual",
            files={"file": ("private.pdf", pdf, "application/pdf")},
        )
    test_id = uploaded.json()["id"]

    transport = ASGITransport(app=app, raise_app_exceptions=False)
    async with AsyncClient(transport=transport, base_url="http://test") as stranger:
        await stranger.post("/api/v1/session")
        hidden = await stranger.get(f"/api/v1/tests/{test_id}/manual/content")
    assert hidden.status_code == 404
    assert hidden.json()["error"]["code"] == "test_not_found"


async def test_failed_replacement_preserves_active_manual(
    client: AsyncClient, tmp_path: Path
) -> None:
    valid = write_pdf(tmp_path / "valid.pdf")
    locked = write_pdf(tmp_path / "locked.pdf", encrypted=True)
    await client.post("/api/v1/session")
    with valid.open("rb") as pdf:
        created = await client.post(
            "/api/v1/tests/manual",
            files={"file": ("valid.pdf", pdf, "application/pdf")},
        )
    original = created.json()["manual"]
    test_id = created.json()["id"]

    with locked.open("rb") as pdf:
        replaced = await client.put(
            f"/api/v1/tests/{test_id}/manual",
            files={"file": ("locked.pdf", pdf, "application/pdf")},
        )

    assert replaced.status_code == 202
    assert replaced.json()["manual"] == original
    assert replaced.json()["manualUpload"] is None
    assert replaced.json()["error"]["code"] == "manual_password_protected"
    still_available = await client.get(f"/api/v1/tests/{test_id}/manual/content")
    assert still_available.status_code == 200
    assert len(list((tmp_path / "documents").glob("*.pdf"))) == 1


async def test_initial_processing_failure_stays_on_upload_and_cleans_storage(
    client: AsyncClient, tmp_path: Path
) -> None:
    scanned = write_pdf(tmp_path / "scan.pdf", with_text=False)
    await client.post("/api/v1/session")

    with scanned.open("rb") as pdf:
        uploaded = await client.post(
            "/api/v1/tests/manual",
            files={"file": ("scan.pdf", pdf, "application/pdf")},
        )

    assert uploaded.status_code == 202
    body = uploaded.json()
    assert body["currentStage"] == "upload"
    assert body["manual"] is None
    assert body["manualUpload"] is None
    assert body["error"] == {
        "code": "manual_no_readable_text",
        "title": "The manual was not added",
        "message": (
            "UVTS could not read the text in this PDF. "
            "Scanned documents are not supported yet."
        ),
        "stage": "upload",
        "retryable": False,
    }
    content = await client.get(f"/api/v1/tests/{body['id']}/manual/content")
    assert content.status_code == 404
    assert list((tmp_path / "documents").glob("*.pdf")) == []


async def test_successful_replacement_preserves_configuration_and_clears_results(
    app: FastAPI, client: AsyncClient, tmp_path: Path
) -> None:
    original_path = write_pdf(tmp_path / "original.pdf")
    replacement_path = write_pdf(tmp_path / "replacement.pdf", pages=2)
    await client.post("/api/v1/session")
    with original_path.open("rb") as pdf:
        created = await client.post(
            "/api/v1/tests/manual",
            files={"file": ("original.pdf", pdf, "application/pdf")},
        )
    test_id = created.json()["id"]
    original_manual_id = created.json()["manual"]["id"]

    async with app.state.session_factory() as db:
        test = await db.get(RunModel, test_id)
        assert test is not None
        state = deepcopy(test.state)
        state["currentStage"] = "report"
        state["configuration"]["topics"] = ["Custom retained topic"]
        question = {
            "id": "q1",
            "text": "Can setup resume?",
            "type": "Basic",
            "topic": "Custom retained topic",
            "viewpoint": "Beginner",
        }
        state["questions"] = [question]
        state["evaluation"] = [{"questionId": "q1", "status": "complete", "error": None}]
        state["report"] = {
            "isComplete": True,
            "counts": {
                "found": 1,
                "partly_found": 0,
                "not_found": 0,
                "failed": 0,
            },
            "results": [
                {
                    "question": question,
                    "status": "found",
                    "informationNeeded": "Resume instructions",
                    "informationFound": "Resume setup from the device list.",
                    "informationMissing": None,
                    "evidence": [{"page": 1, "extract": "Resume setup."}],
                }
            ],
            "gaps": [],
            "recommendations": [],
            "followUpQuestions": [],
        }
        test.state = state
        await db.commit()

    with replacement_path.open("rb") as pdf:
        replaced = await client.put(
            f"/api/v1/tests/{test_id}/manual",
            files={"file": ("replacement.pdf", pdf, "application/pdf")},
        )

    assert replaced.status_code == 202
    body = replaced.json()
    assert body["currentStage"] == "configuration"
    assert body["manual"]["id"] != original_manual_id
    assert body["manual"]["filename"] == "replacement.pdf"
    assert body["manual"]["pageCount"] == 2
    assert body["configuration"]["topics"] == ["Custom retained topic"]
    assert body["questions"] == []
    assert body["evaluation"] == []
    assert body["report"] is None
    content = await client.get(f"/api/v1/tests/{test_id}/manual/content")
    assert content.content == replacement_path.read_bytes()
    assert len(list((tmp_path / "documents").glob("*.pdf"))) == 1
