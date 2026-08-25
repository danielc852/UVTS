"""Report-synthesis model contract.

The schema is re-exported from its established location so callers and persisted/public report
assembly retain the exact same Pydantic contract during the agent-layer reorganization.
"""

from uvts_api.agents.schemas import (
    ReportSynthesisOutput,
    SynthesizedGap,
    SynthesizedRecommendation,
)

__all__ = [
    "ReportSynthesisOutput",
    "SynthesizedGap",
    "SynthesizedRecommendation",
]
