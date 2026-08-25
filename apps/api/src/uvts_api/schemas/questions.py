from pydantic import Field

from uvts_api.schemas.workspace import ApiModel


class ConfirmQuestionItem(ApiModel):
    id: str | None = None
    text: str


class ConfirmQuestionsRequest(ApiModel):
    items: list[ConfirmQuestionItem] = Field(min_length=1, max_length=15)


class QuestionSuggestionRequest(ApiModel):
    direction: str = Field(min_length=1, max_length=1_000)
    existing_questions: list[str] = Field(
        default_factory=list,
        alias="existingQuestions",
        max_length=15,
    )


class QuestionSuggestionResponse(ApiModel):
    text: str
