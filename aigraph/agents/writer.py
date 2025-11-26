import logging
import operator as op
from typing import Annotated, Any, Literal, cast

from langchain.chat_models import BaseChatModel, init_chat_model
from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage
from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph
from langgraph.runtime import Runtime
from langgraph.types import Checkpointer
from pydantic import BaseModel

from aigraph import utils

logger = logging.getLogger(__name__)


class State(BaseModel):
    # inputs
    prompt_write: str
    prompt_review: str

    # state
    reviews: Annotated[list[utils.Review], op.add] = []

    # output
    report: str | None = None
    review: utils.Review | None = None


class Context(BaseModel):
    model: str = "gpt-4o-mini"
    temperature: float = 0.0
    max_attempts: int = 5

    @property
    def llm(self) -> BaseChatModel:
        return init_chat_model(model=self.model, temperature=self.temperature)


async def node_write(state: State, runtime: Runtime[Context]) -> dict[str, Any]:
    logger.info("Starting node_write")

    class Schema(BaseModel):
        content: str

    memory = ""
    for i, review in enumerate(state.reviews):
        memory += f"Review {i}:\n\n"
        memory += "Summary:\n\n"
        memory += f"<summary>\n{review.summary}\n</summary>\n\n"
        memory += "Strengths:\n\n"
        memory += f"<strengths>\n{review.strengths}\n</strengths>\n\n"
        memory += "Weaknesses:\n\n"
        memory += f"<weaknesses>\n{review.weaknesses}\n</weaknesses>\n\n"
        memory += "Decision:\n\n"
        memory += f"<decision>\n{review.decision}\n</decision>\n\n"
        memory += "========================================\n\n"

    messages: list[BaseMessage] = [SystemMessage(state.prompt_write)]
    if memory:
        messages.append(HumanMessage(f"Previous reviews:\n\n{memory}"))

    llms = runtime.context.llm.with_structured_output(Schema)
    response = await llms.ainvoke(messages)
    response = cast(Schema, response)

    logger.debug(f"report length: {len(response.content)}")
    logger.debug(f"report: {response.content[:32]!r}")

    logger.info("Finished node_write")
    return {"report": response.content}


async def node_review(state: State, runtime: Runtime[Context]) -> dict[str, Any]:
    logger.info("Starting node_review")
    assert state.report, "Report is required"

    messages: list[BaseMessage] = [
        SystemMessage(state.prompt_review),
        HumanMessage(state.report),
    ]

    llms = runtime.context.llm.with_structured_output(utils.Review)
    response = await llms.ainvoke(messages)
    response = cast(utils.Review, response)

    logger.debug(f"Review decision: {response.decision}")
    logger.debug(f"Review summary: {response.summary[:32]!r}")

    logger.info("Finished node_review")
    return {"reviews": [response], "review": response}


async def node_should_retry(
    state: State, runtime: Runtime[Context]
) -> Literal["node_write", "__end__"]:
    logger.info("Starting node_should_retry")

    if len(state.reviews) >= runtime.context.max_attempts:
        logger.info("Max retries reached, going to `__end__`")
        return "__end__"

    if state.reviews[-1].decision == "Accept":
        logger.info("Review accepted, going to `__end__`")
        return "__end__"

    logger.info("Going to `node_write`")
    return "node_write"


def build(
    checkpointer: Checkpointer = None,
) -> CompiledStateGraph[State, Context, State, State]:
    builder = StateGraph(state_schema=State, context_schema=Context)

    builder.add_node("node_write", node_write)
    builder.add_node("node_review", node_review)

    builder.add_edge(START, "node_write")
    builder.add_edge("node_write", "node_review")
    builder.add_conditional_edges(
        "node_review",
        node_should_retry,
        ["node_write", END],
    )

    return builder.compile(name="graph_writer", checkpointer=checkpointer)  # type: ignore
