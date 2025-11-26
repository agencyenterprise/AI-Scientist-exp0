import logging
import operator as op
from pathlib import Path
from typing import Annotated, Any, Literal

from langchain.chat_models import BaseChatModel, init_chat_model
from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage
from langgraph.errors import GraphRecursionError
from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph
from langgraph.runtime import Runtime
from langgraph.types import Checkpointer
from pydantic import BaseModel, Field

from aigraph import utils

logger = logging.getLogger(__name__)


class Analysis(BaseModel):
    score: int
    summary: str


class Execution(BaseModel):
    stdout: str
    stderr: str
    returncode: int
    filename: Path


class Code(BaseModel):
    # code generation outputs
    code: str
    dependencies: list[str]


class State(BaseModel):
    # inputs
    cwd: Path
    prompt_code: str  # generic prompt by the user
    prompt_review: str  # generic prompt by the user
    example: str | None = None  # optional example code

    # state
    attempts_code: Annotated[list[Code], op.add] = []
    attempts_analysis: Annotated[list[Analysis], op.add] = []
    attempts_execution: Annotated[list[Execution], op.add] = []

    # outputs
    code: Code | None = None
    analysis: Analysis | None = None
    execution: Execution | None = None


class Context(BaseModel):
    """Configurable context for the coder"""

    filename: Path
    model: str = "gpt-4o-mini"
    temperature: float = 0.0
    max_attempts: int = 5
    score_cutoff: int = 7

    @property
    def llm(self) -> BaseChatModel:
        return init_chat_model(model=self.model, temperature=self.temperature)


async def node_generate_code(state: State, runtime: Runtime[Context]) -> dict[str, Any]:
    logger.info("Starting node_generate_code")

    class Schema(BaseModel):
        code: str
        dependencies: list[str]

    if len(state.attempts_code) >= runtime.context.max_attempts:
        raise GraphRecursionError("Max attempts reached")

    memory = ""
    if state.analysis is not None:
        memory += "Previous analysis:\n\n"
        memory += f"<summary>\n{state.analysis.summary}\n</summary>\n\n"
        memory += "Previous analysis score:\n\n"
        memory += f"<score>\n{state.analysis.score}\n</score>\n\n"
    if state.code is not None:
        memory += "Previous code:\n\n"
        memory += f"<code>\n{state.code.code}\n</code>\n\n"
    if state.execution is not None:
        memory += "Previous stdout:\n\n"
        memory += f"<stdout>\n{state.execution.stdout}\n</stdout>\n\n"
        memory += "Previous stderr:\n\n"
        memory += f"<stderr>\n{state.execution.stderr}\n</stderr>\n\n"
        memory += "Previous return code:\n\n"
        memory += f"<returncode>\n{state.execution.returncode}\n</returncode>\n\n"

    messages: list[BaseMessage] = [SystemMessage(content=state.prompt_code)]
    if memory:
        messages.append(HumanMessage(content=memory))

    llms = runtime.context.llm.with_structured_output(Schema)
    response: Schema = await llms.ainvoke({"messages": messages})  # type: ignore

    logger.debug(f"Generated code length: {len(response.code)}")
    logger.debug(f"Dependencies: {response.dependencies}")

    logger.info("Finished node_generate_code")
    return {
        "code": Code(code=response.code, dependencies=response.dependencies),
        "attempts_code": [Code(code=response.code, dependencies=response.dependencies)],
    }


async def node_execute_code(state: State, runtime: Runtime[Context]) -> dict[str, Any]:
    logger.info("Starting node_execute_code")
    assert state.code is not None, "Code is required"

    response = await utils.exec_code(
        cwd=state.cwd,
        filename=str(runtime.context.filename),
        code=state.code.code,
        deps=state.code.dependencies,
    )

    logger.debug(f"Return code: {response.returncode}")
    logger.debug(f"Filename: {response.filename}")
    logger.debug(f"Stdout: {response.stdout[:32]!r}")
    logger.debug(f"Stderr: {response.stderr[:32]!r}")

    logger.info("Finished node_execute_code")
    return {
        "execution": Execution(
            stdout=response.stdout,
            stderr=response.stderr,
            returncode=response.returncode,
            filename=Path(response.filename),
        ),
        "attempts_execution": [
            Execution(
                stdout=response.stdout,
                stderr=response.stderr,
                returncode=response.returncode,
                filename=Path(response.filename),
            ),
        ],
    }


async def node_check_output(state: State, runtime: Runtime[Context]) -> dict[str, Any]:
    logger.info("Starting node_check_output")
    assert state.code is not None, "Code is required"
    assert state.execution is not None, "Execution is required"

    class Schema(BaseModel):
        score: Annotated[int, Field(ge=0, le=10, description="10 good, 0 bad")]
        summary: str

    memory = ""
    if state.analysis is not None:
        memory += "Previous analysis:\n\n"
        memory += f"<summary>\n{state.analysis.summary}\n</summary>\n\n"
        memory += "Previous analysis score:\n\n"
        memory += f"<score>\n{state.analysis.score}\n</score>\n\n"
    if state.code is not None:
        memory += "Previous code:\n\n"
        memory += f"<code>\n{state.code.code}\n</code>\n\n"
    if state.execution is not None:
        memory += "Previous stdout:\n\n"
        memory += f"<stdout>\n{state.execution.stdout}\n</stdout>\n\n"
        memory += "Previous stderr:\n\n"
        memory += f"<stderr>\n{state.execution.stderr}\n</stderr>\n\n"
        memory += "Previous return code:\n\n"
        memory += f"<returncode>\n{state.execution.returncode}\n</returncode>\n\n"

    messages: list[BaseMessage] = [SystemMessage(content=state.prompt_review)]
    if memory:
        messages.append(HumanMessage(content=memory))

    llms = runtime.context.llm.with_structured_output(Schema)
    response: Schema = await llms.ainvoke({"messages": messages})  # type: ignore

    logger.debug(f"Analysis score: {response.score}")
    logger.debug(f"Analysis summary: {response.summary[:32]!r}")
    logger.info("Finished node_check_output")

    return {
        "analysis": Analysis(score=response.score, summary=response.summary),
        "attempts_analysis": [Analysis(score=response.score, summary=response.summary)],
    }


async def node_should_retry(
    state: State, runtime: Runtime[Context]
) -> Literal["node_generate_code", "__end__"]:
    """Decide if retry needed"""
    logger.info("Starting node_should_retry")
    assert state.analysis is not None, "Analysis is required"

    if state.analysis.score >= runtime.context.score_cutoff:
        logger.info("Sending to `__end__`")
        return "__end__"

    logger.info("Sending to `node_generate_code`")
    return "node_generate_code"


def build(
    checkpointer: Checkpointer = None,
) -> CompiledStateGraph[State, Context, State, State]:
    """Build the generic coder graph"""
    builder = StateGraph(state_schema=State, context_schema=Context)

    builder.add_node("node_generate_code", node_generate_code)
    builder.add_node("node_execute_code", node_execute_code)
    builder.add_node("node_check_output", node_check_output)

    builder.add_edge(START, "node_generate_code")
    builder.add_edge("node_generate_code", "node_execute_code")
    builder.add_edge("node_execute_code", "node_check_output")
    builder.add_conditional_edges(
        "node_check_output",
        node_should_retry,
        ["node_generate_code", END],
    )

    return builder.compile(name="graph_coder", checkpointer=checkpointer)  # type: ignore
