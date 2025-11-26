import logging
from typing import Any

from langchain.chat_models import BaseChatModel, init_chat_model
from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph
from langgraph.runtime import Runtime
from langgraph.types import Checkpointer
from pydantic import BaseModel

from aigraph import utils
from aigraph.agents import summary_prompts as prompts

logger = logging.getLogger(__name__)


class State(BaseModel):
    task: utils.Task
    metrics: list[utils.Metric]
    code: str
    stdout: str
    stderr: str
    existing_summary: str
    parsed_summary: str = ""

    # output
    new_summary: str = ""


class Context(BaseModel):
    model: str = "gpt-4o-mini"
    temperature: float = 0.0

    @property
    def llm(self) -> BaseChatModel:
        return init_chat_model(model=self.model, temperature=self.temperature)


async def node_generate_summary(
    state: State, runtime: Runtime[Context]
) -> dict[str, Any]:
    prompt = prompts.build_prompt_summary(
        task=state.task,
        metrics=state.metrics,
        code=state.code,
        stdout=state.stdout,
        stderr=state.stderr,
        existing_summary=state.existing_summary,
        parsed_summary=state.parsed_summary,
    )

    response = await runtime.context.llm.ainvoke(prompt)
    new_summary = response.content
    if isinstance(new_summary, str):
        new_summary = new_summary.strip()
    else:
        new_summary = str(new_summary).strip()

    return {"new_summary": new_summary}


def build(
    checkpointer: Checkpointer = None,
) -> CompiledStateGraph[State, Context, State, State]:
    builder = StateGraph(state_schema=State, context_schema=Context)

    builder.add_node("node_generate_summary", node_generate_summary)
    builder.add_edge(START, "node_generate_summary")
    builder.add_edge("node_generate_summary", END)

    return builder.compile(name="graph_summary", checkpointer=checkpointer)  # type: ignore
