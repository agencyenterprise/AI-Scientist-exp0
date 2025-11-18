import asyncio

from langfuse.langchain import CallbackHandler
from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import RunnableConfig
from pydantic import BaseModel

from aigraph import agent_step_1, agent_step_2


class State(BaseModel):
    idea: str

    stage1: agent_step_1.State | None = None
    stage2: agent_step_2.State | None = None


async def node_stage_1(state: State) -> State:
    input = agent_step_1.State(idea="Minimal hello world")
    context = agent_step_1.Context(model="gpt-4o-mini", temperature=0.0)
    config = RunnableConfig(callbacks=[CallbackHandler()])

    graph = agent_step_1.build()
    result: agent_step_1.State = await graph.ainvoke(
        input, config=config, context=context
    )  # type: ignore

    state.stage1 = result
    return state


async def node_stage_2(state: State) -> State:
    code = state.stage1.code if state.stage1 else ""
    code = code or ""

    input = agent_step_2.State(idea=state.idea, base_code=code)
    context = agent_step_2.Context(model="gpt-4o-mini", temperature=0.0)
    config = RunnableConfig(callbacks=[CallbackHandler()])

    graph = agent_step_2.build()
    result: agent_step_2.State = await graph.ainvoke(
        input, config=config, context=context
    )  # type: ignore

    state.stage2 = result
    return state


async def main() -> None:
    builder = StateGraph(State)

    builder.add_node("stage_1", node_stage_1)
    builder.add_node("stage_2", node_stage_2)
    builder.add_edge(START, "stage_1")
    builder.add_edge("stage_1", "stage_2")
    builder.add_edge("stage_2", END)

    graph = builder.compile()

    config = RunnableConfig(callbacks=[CallbackHandler()])

    state = State(idea="Minimal hello world")
    result: State = await graph.ainvoke(state, config=config)  # type: ignore
    print(result)


if __name__ == "__main__":
    asyncio.run(main())
