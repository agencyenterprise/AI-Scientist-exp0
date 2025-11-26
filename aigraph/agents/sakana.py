import logging
from pathlib import Path
from typing import Any, Literal

from langchain.chat_models import BaseChatModel, init_chat_model
from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph
from langgraph.runtime import Runtime
from langgraph.types import Checkpointer
from pydantic import BaseModel

from aigraph import utils

logger = logging.getLogger(__name__)


class State(BaseModel):
    """State for the complete Sakana AI Scientist workflow."""

    # inputs
    cwd: Path
    task: utils.Task

    # Phase 1: Idea Generation
    idea_plan: str | None = None
    novelty_score: float | None = None
    idea_archived: bool = False

    # Phase 2: Experiment Iteration
    experiment_template: str | None = None
    code_delta: str | None = None
    experiment_results: str | None = None
    numerical_data: str | None = None
    plots: list[str] = []
    updated_plan: str | None = None
    iteration_count: int = 0
    max_iterations: int = 5
    experiments_complete: bool = False

    # Phase 3: Paper Write-Up
    manuscript_template: str | None = None
    text_delta: str | None = None
    manuscript: str | None = None
    paper_review: str | None = None
    paper_approved: bool = False

    # Control flow
    restart_from_beginning: bool = False


class Context(BaseModel):
    model: str = "gpt-4o-mini"
    temperature: float = 0.0

    @property
    def llm(self) -> BaseChatModel:
        return init_chat_model(model=self.model, temperature=self.temperature)


# ============================================================================
# Phase 1: Idea Generation Nodes
# ============================================================================


async def node_generate_idea_plan(
    state: State, runtime: Runtime[Context]
) -> dict[str, Any]:
    """LLM generates research idea/plan innovation."""
    logger.info("Starting node_generate_idea_plan")

    # TODO: Implement idea generation

    logger.info("Finished node_generate_idea_plan")
    return {"idea_plan": "Generated idea plan"}


async def node_novelty_check(state: State, runtime: Runtime[Context]) -> dict[str, Any]:
    """Check novelty using Semantic Scholar."""
    logger.info("Starting node_novelty_check")

    # TODO: Implement novelty check via Semantic Scholar

    logger.info("Finished node_novelty_check")
    return {"novelty_score": 0.8}


async def node_score_archive_idea(
    state: State, runtime: Runtime[Context]
) -> dict[str, Any]:
    """Score and archive the idea."""
    logger.info("Starting node_score_archive_idea")

    # TODO: Implement idea scoring and archiving

    logger.info("Finished node_score_archive_idea")
    return {"idea_archived": True}


# ============================================================================
# Phase 2: Experiment Iteration Nodes
# ============================================================================


async def node_create_experiment_template(
    state: State, runtime: Runtime[Context]
) -> dict[str, Any]:
    """Create experiment template from the idea."""
    logger.info("Starting node_create_experiment_template")

    # TODO: Implement experiment template creation

    logger.info("Finished node_create_experiment_template")
    return {"experiment_template": "Template created"}


async def node_code_delta(state: State, runtime: Runtime[Context]) -> dict[str, Any]:
    """Generate code changes via LLM & aider."""
    logger.info("Starting node_code_delta")

    # TODO: Implement code delta generation using LLM + aider

    logger.info("Finished node_code_delta")
    return {"code_delta": "Code changes generated"}


async def node_exec_experiment(
    state: State, runtime: Runtime[Context]
) -> dict[str, Any]:
    """Execute the experiment script."""
    logger.info("Starting node_exec_experiment")

    # TODO: Implement experiment execution

    logger.info("Finished node_exec_experiment")
    return {
        "experiment_results": "Experiment completed",
        "iteration_count": state.iteration_count + 1,
    }


async def node_update_plan(state: State, runtime: Runtime[Context]) -> dict[str, Any]:
    """Update the experiment plan based on results."""
    logger.info("Starting node_update_plan")

    # TODO: Implement plan updates based on experiment results

    logger.info("Finished node_update_plan")
    return {"updated_plan": "Plan updated"}


async def node_generate_plots(
    state: State, runtime: Runtime[Context]
) -> dict[str, Any]:
    """Generate numerical data and plots."""
    logger.info("Starting node_generate_plots")

    # TODO: Implement plotting and data visualization

    logger.info("Finished node_generate_plots")
    return {"numerical_data": "Data generated", "plots": ["plot1.png", "plot2.png"]}


def should_continue_experiments(state: State) -> Literal["continue", "complete"]:
    """Decide whether to continue iterating or move to paper write-up."""
    if state.experiments_complete or state.iteration_count >= state.max_iterations:
        return "complete"
    return "continue"


# ============================================================================
# Phase 3: Paper Write-Up Nodes
# ============================================================================


async def node_create_manuscript_template(
    state: State, runtime: Runtime[Context]
) -> dict[str, Any]:
    """Create manuscript template."""
    logger.info("Starting node_create_manuscript_template")

    # TODO: Implement manuscript template creation

    logger.info("Finished node_create_manuscript_template")
    return {"manuscript_template": "Manuscript template created"}


async def node_text_delta(state: State, runtime: Runtime[Context]) -> dict[str, Any]:
    """Generate text changes via LLM & aider."""
    logger.info("Starting node_text_delta")

    # TODO: Implement text delta generation using LLM + aider

    logger.info("Finished node_text_delta")
    return {"text_delta": "Text changes generated"}


async def node_generate_manuscript(
    state: State, runtime: Runtime[Context]
) -> dict[str, Any]:
    """Generate the full manuscript."""
    logger.info("Starting node_generate_manuscript")

    # TODO: Implement manuscript generation

    logger.info("Finished node_generate_manuscript")
    return {"manuscript": "Manuscript generated"}


async def node_review_paper(state: State, runtime: Runtime[Context]) -> dict[str, Any]:
    """LLM reviews the paper."""
    logger.info("Starting node_review_paper")

    # TODO: Implement paper review

    logger.info("Finished node_review_paper")
    return {"paper_review": "Review completed", "paper_approved": True}


def should_restart(state: State) -> Literal["restart", "end"]:
    """Decide whether to restart from beginning or end."""
    if state.restart_from_beginning:
        return "restart"
    return "end"


# ============================================================================
# Graph Builder
# ============================================================================


def build(
    checkpointer: Checkpointer = None,
) -> CompiledStateGraph[State, Context, State, State]:
    """Build the complete Sakana AI Scientist graph."""
    builder = StateGraph(state_schema=State, context_schema=Context)

    # Phase 1: Idea Generation
    builder.add_node("node_generate_idea_plan", node_generate_idea_plan)
    builder.add_node("node_novelty_check", node_novelty_check)
    builder.add_node("node_score_archive_idea", node_score_archive_idea)

    # Phase 2: Experiment Iteration
    builder.add_node("node_create_experiment_template", node_create_experiment_template)
    builder.add_node("node_code_delta", node_code_delta)
    builder.add_node("node_exec_experiment", node_exec_experiment)
    builder.add_node("node_update_plan", node_update_plan)
    builder.add_node("node_generate_plots", node_generate_plots)

    # Phase 3: Paper Write-Up
    builder.add_node("node_create_manuscript_template", node_create_manuscript_template)
    builder.add_node("node_text_delta", node_text_delta)
    builder.add_node("node_generate_manuscript", node_generate_manuscript)
    builder.add_node("node_review_paper", node_review_paper)

    # Phase 1 Flow
    builder.add_edge(START, "node_generate_idea_plan")
    builder.add_edge("node_generate_idea_plan", "node_novelty_check")
    builder.add_edge("node_novelty_check", "node_score_archive_idea")

    # Transition to Phase 2
    builder.add_edge("node_score_archive_idea", "node_create_experiment_template")
    builder.add_edge("node_create_experiment_template", "node_code_delta")
    builder.add_edge("node_code_delta", "node_exec_experiment")
    builder.add_edge("node_exec_experiment", "node_generate_plots")
    builder.add_edge("node_generate_plots", "node_update_plan")

    # Experiment iteration loop
    builder.add_conditional_edges(
        "node_update_plan",
        should_continue_experiments,
        {
            "continue": "node_code_delta",  # Loop back to experiments
            "complete": "node_create_manuscript_template",  # Move to Phase 3
        },
    )

    # Phase 3 Flow
    builder.add_edge("node_create_manuscript_template", "node_text_delta")
    builder.add_edge("node_text_delta", "node_generate_manuscript")
    builder.add_edge("node_generate_manuscript", "node_review_paper")

    # Optional restart or end
    builder.add_conditional_edges(
        "node_review_paper",
        should_restart,
        {
            "restart": "node_generate_idea_plan",  # Feedback loop to start
            "end": END,
        },
    )

    return builder.compile(name="graph_sakana", checkpointer=checkpointer)  # type: ignore
