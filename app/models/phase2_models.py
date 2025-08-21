"""Phase 2 models for multi-agent system and session management."""

from enum import Enum
from typing import Any, Dict, List, Optional, Union
from uuid import UUID

from pydantic import BaseModel, Field


class MessageType(str, Enum):
    """Types of messages that can be streamed via WebSocket."""
    THOUGHT = "thought"
    CODE = "code"
    LOG = "log"
    ERROR = "error"
    TABLE = "table"
    CHART = "chart"
    FINAL_RESPONSE = "final_response"
    PLAN = "plan"
    EXECUTION_START = "execution_start"
    EXECUTION_SUCCESS = "execution_success"
    EXECUTION_ERROR = "execution_error"


class StreamMessage(BaseModel):
    """Model for WebSocket streaming messages."""
    type: MessageType = Field(..., description="Type of the message")
    payload: Union[str, Dict[str, Any], List[Any]] = Field(..., description="Message payload")
    timestamp: Optional[str] = Field(None, description="Timestamp of the message")
    step_index: Optional[int] = Field(None, description="Current step index in the plan")


class ConversationTurn(BaseModel):
    """Model for a single conversation turn."""
    user_query: str = Field(..., description="User's query")
    agent_response: str = Field(..., description="Agent's response")
    timestamp: str = Field(..., description="Timestamp of the turn")


class QueryRequest(BaseModel):
    """Request model for /v2/query endpoint."""
    session_id: Optional[str] = Field(None, description="Optional session ID, creates new if null")
    dataset_name: str = Field(..., description="Name of the dataset to query")
    query: str = Field(..., description="Natural language query from user")
    conversation_history: List[ConversationTurn] = Field(default=[], description="Previous conversation turns")


class QueryResponse(BaseModel):
    """Response model for /v2/query endpoint."""
    session_id: str = Field(..., description="Session ID for this query")
    websocket_url: str = Field(..., description="WebSocket URL for streaming")


class SessionInfo(BaseModel):
    """Model for session information."""
    session_id: str = Field(..., description="Unique session identifier")
    dataset_name: str = Field(..., description="Name of the dataset")
    created_at: str = Field(..., description="Session creation timestamp")
    last_activity: str = Field(..., description="Last activity timestamp")
    kernel_id: Optional[str] = Field(None, description="Jupyter kernel ID")
    parquet_path: str = Field(..., description="Path to the session's parquet file")


class ExecutionResult(BaseModel):
    """Model for code execution results."""
    success: bool = Field(..., description="Whether execution was successful")
    stdout: str = Field(default="", description="Standard output from execution")
    stderr: str = Field(default="", description="Standard error from execution")
    display_data: List[Dict[str, Any]] = Field(default=[], description="Rich display data (plots, tables)")
    execution_count: int = Field(..., description="Execution count from kernel")


class AgentStep(BaseModel):
    """Model for a single step in the agent plan."""
    step_index: int = Field(..., description="Index of this step in the plan")
    description: str = Field(..., description="Description of what this step should accomplish")
    completed: bool = Field(default=False, description="Whether this step has been completed")
    code_generated: Optional[str] = Field(None, description="Generated code for this step")
    execution_result: Optional[ExecutionResult] = Field(None, description="Result of code execution")
    error_count: int = Field(default=0, description="Number of errors encountered for this step")


class AgentPlan(BaseModel):
    """Model for the complete agent execution plan."""
    steps: List[str] = Field(..., description="List of step descriptions")
    current_step_index: int = Field(default=0, description="Index of current step being executed")
    completed: bool = Field(default=False, description="Whether the entire plan is completed")


class CodeGenerationRequest(BaseModel):
    """Model for code generation agent input."""
    current_step: str = Field(..., description="Current step to generate code for")
    full_plan: List[str] = Field(..., description="Complete plan for context")
    execution_history: List[str] = Field(default=[], description="Log of previous successful steps")
    metadata: Dict[str, Any] = Field(..., description="Dataset metadata")


class CodeGenerationResponse(BaseModel):
    """Model for code generation agent output."""
    thought: str = Field(..., description="Agent's reasoning process")
    code: str = Field(..., description="Only include the Generated Python code , donot include thought")


class ErrorAnalysisRequest(BaseModel):
    """Model for error analysis agent input."""
    failed_step: str = Field(..., description="Step that failed")
    failed_code: str = Field(..., description="Code that failed to execute")
    error_message: str = Field(..., description="Error message from kernel")
    metadata: Dict[str, Any] = Field(..., description="Dataset metadata for context")


class ErrorAnalysisResponse(BaseModel):
    """Model for error analysis agent output."""
    diagnosis: str = Field(..., description="Detailed explanation of what went wrong")
    suggestion: str = Field(..., description="Clear instruction for fixing the code")


class ChartGenerationRequest(BaseModel):
    """Model for chart generation agent input."""
    user_query: str = Field(..., description="Original user query")
    final_dataframe_json: str = Field(..., description="Final data as JSON for visualization")


class ChartGenerationResponse(BaseModel):
    """Model for chart generation agent output."""
    code: str = Field(..., description="Plotly code to generate the chart")


class FinalResponseRequest(BaseModel):
    """Model for final response agent input."""
    user_query: str = Field(..., description="Original user question")
    final_data_markdown: str = Field(..., description="Final data table as markdown")
    chart_available: bool = Field(..., description="Whether a chart was generated")


class FinalResponseResponse(BaseModel):
    """Model for final response agent output."""
    response: str = Field(..., description="Final human-readable summary")


class AgentState(BaseModel):
    """Model for the overall agent state in LangGraph."""
    session_id: str = Field(..., description="Session identifier")
    user_query: str = Field(..., description="Original user query")
    dataset_metadata: Dict[str, Any] = Field(..., description="Dataset metadata")
    conversation_history: List[ConversationTurn] = Field(default=[], description="Conversation history")
    plan: Optional[AgentPlan] = Field(None, description="Execution plan")
    current_step_index: int = Field(default=0, description="Current step being executed")
    execution_history: List[str] = Field(default=[], description="Log of completed steps")
    execution_context: Dict[str, Any] = Field(default={}, description="Variables and results from previous executions")
    intermediate_results: List[Dict[str, Any]] = Field(default=[], description="Stored intermediate results (tables, charts)")
    available_variables: List[str] = Field(default=["df"], description="List of available variables in Jupyter kernel")
    final_data: Optional[Dict[str, Any]] = Field(None, description="Final analysis result")
    chart_code: Optional[str] = Field(None, description="Generated chart code")
    final_response: Optional[str] = Field(None, description="Final response to user")
    error_count: int = Field(default=0, description="Total number of errors encountered")
    max_retries: int = Field(default=3, description="Maximum number of retries per step")
    current_code: Optional[str] = Field(None, description="Current code being executed")
    current_thought: Optional[str] = Field(None, description="Current thought process")
    last_execution_result: Optional[ExecutionResult] = Field(None, description="Result of last code execution")
    error_analysis: Optional[ErrorAnalysisResponse] = Field(None, description="Analysis of last error")
    class Config:
        arbitrary_types_allowed = True
