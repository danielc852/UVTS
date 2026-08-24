from fastapi import FastAPI


def test_openapi_exposes_the_manual_independent_transition_contract(app: FastAPI) -> None:
    contract = app.openapi()
    paths = contract["paths"]
    schemas = contract["components"]["schemas"]

    assert "/api/v1/tests/manual" not in paths
    assert "/api/v1/tests/{test_id}/question-configuration" not in paths
    assert set(paths["/api/v1/tests"]) == {"post"}
    assert set(paths["/api/v1/tests/{test_id}/configuration"]) == {"put"}
    assert set(paths["/api/v1/tests/{test_id}/questions/confirm"]) == {"post"}
    assert set(paths["/api/v1/tests/{test_id}/start-over"]) == {"post"}
    assert set(paths["/api/v1/tests/{test_id}/manual"]) == {"put", "delete"}

    create_body = paths["/api/v1/tests"]["post"]["requestBody"]["content"]
    update_body = paths["/api/v1/tests/{test_id}/configuration"]["put"]["requestBody"][
        "content"
    ]
    assert set(create_body) == {"multipart/form-data"}
    assert set(update_body) == {"multipart/form-data"}
    assert "requestBody" not in paths["/api/v1/tests/{test_id}/questions"]["post"]

    create_schema_name = create_body["multipart/form-data"]["schema"]["$ref"].rsplit(
        "/", 1
    )[1]
    update_schema_name = update_body["multipart/form-data"]["schema"]["$ref"].rsplit(
        "/", 1
    )[1]
    assert set(schemas[create_schema_name]["required"]) == {
        "productImage",
        "productDescription",
        "totalQuestions",
    }
    assert set(schemas[update_schema_name]["required"]) == {
        "productDescription",
        "totalQuestions",
    }
    assert schemas[create_schema_name]["properties"]["totalQuestions"] == {
        "maximum": 15,
        "minimum": 1,
        "title": "Totalquestions",
        "type": "integer",
    }


def test_openapi_publishes_the_new_stages_statuses_and_source_models(app: FastAPI) -> None:
    schemas = app.openapi()["components"]["schemas"]

    assert schemas["WorkflowStage"]["enum"] == [
        "configuration",
        "questions",
        "upload",
        "evaluation",
        "report",
    ]
    assert schemas["TestStatus"]["enum"] == [
        "draft",
        "generating",
        "questions_ready",
        "questions_confirmed",
        "ready",
        "evaluating",
        "complete",
        "incomplete",
        "failed",
    ]
    assert schemas["QuestionSetStatus"]["enum"] == ["draft", "confirmed"]
    assert set(schemas["Question"]["properties"]) == {"id", "text"}
    assert set(schemas["QuestionSet"]["required"]) == {"id", "status", "source", "items"}
    assert set(schemas["EvaluationSource"]["required"]) == {"questionSetId", "manualId"}
    assert "source" in schemas["Report"]["properties"]
    assert "questionSet" in schemas["TestResponse"]["properties"]
    assert "evaluationSource" in schemas["TestResponse"]["properties"]
