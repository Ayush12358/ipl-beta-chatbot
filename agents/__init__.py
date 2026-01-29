"""
IPL Cricket Chatbot Agents
===========================
Multi-agent system for answering cricket queries.

Agents:
- QueryExpander: Expands and clarifies user queries
- QueryDecomposer: Extracts structured intent from natural language
- CodeGenerator: Generates Python/Pandas code from decomposed queries
- CodeExecutor: Safely executes generated code
- ResponseFormatter: Formats results into user-friendly responses
- CricketChatbot: Complete pipeline combining all agents
"""

from .query_expander import QueryExpander
from .query_decomposer import (
    QueryDecomposer,
    DecomposedQuery,
    QueryType,
    MetricType,
    MatchPhase,
    PlayerFilter,
    TeamFilter,
)

from .code_generator import (
    CodeGenerator,
    GeneratedCode,
)

from .code_executor import (
    CodeExecutor,
    ExecutionResult,
    DataLoader,
)

from .response_formatter import (
    ResponseFormatter,
    FormattedResponse,
    TableData,
    CricketChatbot,
)

__all__ = [
    # Main chatbot
    "CricketChatbot",
    # Agents
    "QueryExpander",
    "QueryDecomposer",
    "CodeGenerator", 
    "CodeExecutor",
    "ResponseFormatter",
    # Models
    "DecomposedQuery",
    "GeneratedCode",
    "ExecutionResult",
    "FormattedResponse",
    "TableData",
    # Enums
    "QueryType",
    "MetricType",
    "MatchPhase",
    # Filters
    "PlayerFilter",
    "TeamFilter",
]
