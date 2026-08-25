from collections.abc import Sequence

from langchain_core.language_models.chat_models import BaseChatModel

from uvts_api.agents.manual_evaluation import ManualEvaluationAgent
from uvts_api.agents.manual_evaluation.validation import ManualPage
from uvts_api.agents.report_synthesis import ReportSynthesisAgent
from uvts_api.agents.schemas import QuestionEvaluationOutput, ReportSynthesisOutput
from uvts_api.ports.question_generator import AgentProductImage
from uvts_api.schemas.workspace import Question, QuestionResult


class EvaluationAgentSuite:
    """Compose independent evaluation and report agents for one workflow operation."""

    def __init__(self, model: BaseChatModel) -> None:
        self._manual_evaluation = ManualEvaluationAgent(model)
        self._report_synthesis = ReportSynthesisAgent(model)

    async def evaluate_question(
        self,
        *,
        question: Question,
        manual_pages: Sequence[ManualPage],
        product_image: AgentProductImage | None = None,
        product_description: str = "",
    ) -> QuestionEvaluationOutput:
        return await self._manual_evaluation.evaluate_question(
            question=question,
            manual_pages=manual_pages,
            product_image=product_image,
            product_description=product_description,
        )

    async def synthesize_report(
        self,
        *,
        results: Sequence[QuestionResult],
    ) -> ReportSynthesisOutput:
        return await self._report_synthesis.synthesize_report(results=results)
