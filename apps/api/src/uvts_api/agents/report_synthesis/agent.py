import json
from collections.abc import Sequence

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage

from uvts_api.agents.errors import (
    EvaluatorOutputError,
    EvaluatorStructuredOutputError,
)
from uvts_api.agents.report_synthesis.prompts import (
    REPORT_SYNTHESIS_REPAIR_PROMPT,
    REPORT_SYNTHESIS_SYSTEM_PROMPT,
)
from uvts_api.agents.report_synthesis.schemas import ReportSynthesisOutput
from uvts_api.agents.report_synthesis.validation import validate_synthesis
from uvts_api.agents.structured_output import invoke_structured_output
from uvts_api.schemas.workspace import CoverageStatus, QuestionResult


class ReportSynthesisAgent:
    """Create a complete, validated writing report from uncovered manual needs."""

    def __init__(self, model: BaseChatModel) -> None:
        self._model = model

    async def synthesize_report(
        self,
        *,
        results: Sequence[QuestionResult],
    ) -> ReportSynthesisOutput:
        eligible_results = [
            result
            for result in results
            if result.status in {CoverageStatus.PARTLY_FOUND, CoverageStatus.NOT_FOUND}
        ]
        if not eligible_results:
            return ReportSynthesisOutput(
                gaps=[], recommendations=[], follow_up_questions=[]
            )

        messages: list[BaseMessage] = [
            SystemMessage(content=REPORT_SYNTHESIS_SYSTEM_PROMPT),
            HumanMessage(content=_synthesis_prompt(eligible_results)),
        ]
        try:
            first = await self._request(messages)
            return validate_synthesis(first, eligible_results)
        except (EvaluatorStructuredOutputError, EvaluatorOutputError):
            repaired = await self._request(
                [*messages, HumanMessage(content=REPORT_SYNTHESIS_REPAIR_PROMPT)]
            )
            return validate_synthesis(repaired, eligible_results)

    async def synthesize(
        self,
        *,
        results: Sequence[QuestionResult],
    ) -> ReportSynthesisOutput:
        return await self.synthesize_report(results=results)

    async def _request(self, messages: list[BaseMessage]) -> ReportSynthesisOutput:
        return await invoke_structured_output(
            self._model,
            ReportSynthesisOutput,
            messages,
        )


def _synthesis_prompt(results: Sequence[QuestionResult]) -> str:
    persisted = [result.model_dump(mode="json", by_alias=True) for result in results]
    return "UNTRUSTED ELIGIBLE QUESTION RESULTS\n" + json.dumps(
        persisted, ensure_ascii=False, separators=(",", ":")
    )
