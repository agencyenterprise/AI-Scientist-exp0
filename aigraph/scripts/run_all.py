import json
import logging
import uuid
from pathlib import Path
from typing import Annotated, Any

import aiosqlite
from langchain_core.runnables import RunnableConfig
from langfuse.langchain import CallbackHandler
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph
from langgraph.runtime import Runtime
from pydantic import AliasChoices, BaseModel, Field
from pydantic_settings import BaseSettings, CliApp, CliImplicitFlag, CliPositionalArg

from aigraph import log, utils
from aigraph.agents import ablation, baseline, plotting, prepare, tuning, writeup

logger = logging.getLogger(__name__)


class State(BaseModel):
    # inputs
    cwd: Path
    task: utils.Task

    # outputs from prepare
    research: str = ""  # research report from prepare
    metrics: list[utils.Metric] = []
    experiment_plan_structured: str = ""  # structured experiment plan

    # outputs from downstream nodes
    cumulative_summary: str = ""
    baseline_results: str = ""  # baseline parser stdout for comparison

    state_prepare: prepare.State | None = None
    state_baseline: baseline.State | None = None
    state_tuning: tuning.State | None = None
    state_ablation: ablation.State | None = None
    state_plotting: plotting.State | None = None
    state_writeup: writeup.State | None = None


class Context(BaseModel):
    model: str = "gpt-4o-mini"
    temperature: float = 0.0


async def node_prepare(state: State, runtime: Runtime[Context]) -> dict[str, Any]:
    """Run prepare phase: research + metrics + plan."""
    prepare_state = prepare.State(
        cwd=state.cwd,
        task=state.task,
    )
    prepare_context = prepare.Context(
        model=runtime.context.model,
        temperature=runtime.context.temperature,
    )

    graph = prepare.build(checkpointer=True)
    result = await graph.ainvoke(input=prepare_state, context=prepare_context)

    return {
        "state_prepare": result,
        "research": result.get("research", ""),
        "metrics": result.get("metrics", []),
        "experiment_plan_structured": result.get("experiment_plan_structured", ""),
    }


async def node_baseline(state: State, runtime: Runtime[Context]) -> dict[str, Any]:
    baseline_state = baseline.State(
        cwd=state.cwd,
        task=state.task,
        research=state.research,
        metrics=state.metrics,
        experiment_plan_structured=state.experiment_plan_structured,
        cumulative_summary=state.cumulative_summary,
    )
    baseline_context = baseline.Context(
        model=runtime.context.model,
        temperature=runtime.context.temperature,
    )

    graph = baseline.build(checkpointer=True)
    result = await graph.ainvoke(
        input=baseline_state,
        context=baseline_context,
    )

    return {
        "state_baseline": result,
        "cumulative_summary": result.get("cumulative_summary", ""),
        "baseline_results": result.get("parse_stdout", ""),
    }


async def node_tuning(state: State, runtime: Runtime[Context]) -> dict[str, Any]:
    assert state.state_baseline
    assert state.state_baseline.experiment_code

    tuning_state = tuning.State(
        cwd=state.cwd,
        task=state.task,
        research=state.research,
        code=state.state_baseline.experiment_code,
        metrics=state.metrics,
        cumulative_summary=state.cumulative_summary,
        baseline_results=state.baseline_results,
        experiment_plan_structured=state.experiment_plan_structured,
    )
    tuning_context = tuning.Context(
        model=runtime.context.model,
        temperature=runtime.context.temperature,
    )

    graph = tuning.build(checkpointer=True)
    result = await graph.ainvoke(
        input=tuning_state,
        context=tuning_context,
    )

    return {
        "state_tuning": result,
        "cumulative_summary": result.get(
            "cumulative_summary", state.cumulative_summary
        ),
    }


async def node_ablation(state: State, runtime: Runtime[Context]) -> dict[str, Any]:
    assert state.state_tuning
    assert state.state_tuning.tuning_code
    assert state.state_baseline
    assert state.state_baseline.experiment_code

    ablation_state = ablation.State(
        cwd=state.cwd,
        task=state.task,
        research=state.research,
        code=state.state_tuning.tuning_code,
        baseline_code=state.state_baseline.experiment_code,
        metrics=state.metrics,
        cumulative_summary=state.cumulative_summary,
        baseline_results=state.baseline_results,
        experiment_plan_structured=state.experiment_plan_structured,
    )
    ablation_context = ablation.Context(
        model=runtime.context.model,
        temperature=runtime.context.temperature,
    )

    graph = ablation.build(checkpointer=True)
    result = await graph.ainvoke(
        input=ablation_state,
        context=ablation_context,
    )

    return {
        "state_ablation": result,
        "cumulative_summary": result.get(
            "cumulative_summary", state.cumulative_summary
        ),
    }


async def node_plotting(state: State, runtime: Runtime[Context]) -> dict[str, Any]:
    assert state.state_ablation
    assert state.state_ablation.ablation_code
    assert state.state_baseline
    assert state.state_baseline.experiment_code

    plotting_state = plotting.State(
        cwd=state.cwd,
        task=state.task,
        code=state.state_ablation.ablation_code,
        baseline_code=state.state_baseline.experiment_code,
    )
    plotting_context = plotting.Context(
        model=runtime.context.model,
        temperature=runtime.context.temperature,
    )

    graph = plotting.build(checkpointer=True)
    result = await graph.ainvoke(
        input=plotting_state,
        context=plotting_context,
    )

    return {"state_plotting": result}


async def node_writeup(state: State, runtime: Runtime[Context]) -> dict[str, Any]:
    assert state.state_plotting
    assert state.state_ablation
    assert state.state_ablation.ablation_code
    assert state.state_ablation.parser_code
    assert state.state_ablation.parser_stdout

    writeup_state = writeup.State(
        cwd=state.cwd,
        task=state.task,
        experiment_code=state.state_ablation.ablation_code,
        parser_code=state.state_ablation.parser_code,
        parser_stdout=state.state_ablation.parser_stdout,
        baseline_results=state.baseline_results,
        plots=list(state.state_plotting.plots),
        research=state.research,
        experiment_plan_structured=state.experiment_plan_structured,
    )
    writeup_context = writeup.Context(
        model=runtime.context.model,
        temperature=runtime.context.temperature,
    )

    graph = writeup.build(checkpointer=True)
    result = await graph.ainvoke(
        input=writeup_state,
        context=writeup_context,
    )

    return {"state_writeup": result}


def build(
    conn: aiosqlite.Connection,
) -> CompiledStateGraph[State, Context, State, State]:
    builder = StateGraph(state_schema=State, context_schema=Context)

    # Add nodes
    builder.add_node("node_prepare", node_prepare)
    builder.add_node("node_baseline", node_baseline)
    builder.add_node("node_tuning", node_tuning)
    builder.add_node("node_ablation", node_ablation)
    builder.add_node("node_plotting", node_plotting)
    builder.add_node("node_writeup", node_writeup)

    # Add edges
    # Prepare runs first (research + metrics + plan)
    builder.add_edge(START, "node_prepare")
    # Sequential flow: prepare → baseline → tuning → ablation → plotting → writeup
    builder.add_edge("node_prepare", "node_baseline")
    builder.add_edge("node_baseline", "node_tuning")
    builder.add_edge("node_tuning", "node_ablation")
    builder.add_edge("node_ablation", "node_plotting")
    builder.add_edge("node_plotting", "node_writeup")
    builder.add_edge("node_writeup", END)

    checkpointer = AsyncSqliteSaver(conn=conn)
    return builder.compile(name="graph_all", checkpointer=checkpointer)  # type: ignore


class Args(BaseSettings):
    cwd: CliPositionalArg[Path]
    task: CliPositionalArg[Path]
    thread_id: Annotated[
        str,
        Field(default_factory=lambda: str(uuid.uuid4())),
    ]
    checkpoint_id: Annotated[
        str | None,
        Field(default=None),
    ]
    checkpoint_db: Annotated[
        Path,
        Field(default=Path("checkpoints.db")),
    ]
    model: Annotated[
        str,
        Field(default="gpt-4o-mini"),
    ]
    temperature: Annotated[
        float,
        Field(default=0.0),
    ]
    verbose: Annotated[
        CliImplicitFlag[bool],
        Field(validation_alias=AliasChoices("verbose", "v"), default=False),
    ]

    async def cli_cmd(self) -> None:
        self.cwd.mkdir(parents=True, exist_ok=True)

        if self.verbose:
            log.init()

        logger.info("thread_id:", self.thread_id)
        if self.checkpoint_id:
            logger.info("checkpoint_id:", self.checkpoint_id)

        configurable = {"thread_id": self.thread_id}
        if self.checkpoint_id:
            configurable["checkpoint_id"] = self.checkpoint_id

        config = RunnableConfig(
            callbacks=[CallbackHandler()],
            configurable=configurable,
            recursion_limit=1_000,
        )

        task = utils.Task.model_validate_json(self.task.read_text())
        state = State(cwd=self.cwd, task=task)
        context = Context(model=self.model, temperature=self.temperature)

        async with aiosqlite.connect(self.checkpoint_db) as conn:
            graph = build(conn)
            result = await graph.ainvoke(input=state, context=context, config=config)
            print(json.dumps(result, indent=2, sort_keys=True, default=str))


if __name__ == "__main__":
    CliApp.run(Args)
