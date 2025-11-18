import logging
from typing import Literal

from langchain.chat_models import init_chat_model
from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph
from langgraph.runtime import Runtime
from pydantic import BaseModel

from aigraph import utils

logger = logging.getLogger(__name__)


PROMPT_DRAFT = """
## Introduction

You are an AI researcher who is looking to publish a paper that will contribute
significantly to the field. Your first task is to write a python code to
implement a solid baseline based on your research idea provided below, from data
preparation to model training, as well as evaluation and visualization. Focus on
getting a simple but working implementation first, before any sophisticated
improvements. We will explore more advanced variations in later stages.

## Research idea

{idea}

## Memory

{memory}

## Instructions

### Experiment design sketch guideline

- This first experiment design should be relatively simple, without extensive
  hyper-parameter optimization.
- Take the Memory section into consideration when proposing the design.
- The solution sketch should be 6-10 sentences.
- Don't suggest to do EDA.
- Prioritize using real public datasets (e.g., from HuggingFace) when they suit
  the task, and only fall back to synthetic data if no suitable dataset is
  available or synthetic generation is essential to the proposed experiment.

### Goals

- Focus on getting basic working implementation
- Use a dataset appropriate to the experiment
- Aim for basic functional correctness
- If you are given "Code To Use", you can directly use it as a starting point.
"""


PROMPT_IMPROVE = """
## Introduction

You are an experienced AI researcher. You are provided with a previously
developed implementation. Your task is to improve it based on the current
experimental stage.

## Research idea

{idea}

## Memory

{memory}

## Previous solution

### Code

```python {previous_code} ```

## Feedback

{feedback}

## Instructions

Focus on addressing the feedback and improving the implementation while
maintaining the core functionality.
"""


PROMPT_CHECK_COMPLETION = """
Evaluate if the current stage is complete.

## Evidence

- Best metric: {metric}
- Has working code: {has_code}
- Return code: {returncode}
- Error output: {stderr}

## Requirements for completion

- {goals}

Determine if these requirements are met.
"""


class State(BaseModel):
    # inputs
    idea: str
    memory: str = ""
    goals: str = "Focus on getting basic working implementation"
    
    # iteration tracking
    iteration: int = 0
    max_iterations: int = 3
    
    # code and execution
    plan: str | None = None
    code: str | None = None
    dependencies: list[str] | None = None
    returncode: int | None = None
    stdout: str | None = None
    stderr: str | None = None
    
    # completion tracking
    is_complete: bool = False
    completion_reason: str = ""
    metric_value: float | None = None


class Context(BaseModel):
    model: str = "gpt-4o-mini"
    temperature: float = 0.0


async def node_draft(state: State, runtime: Runtime[Context]) -> State:
    """Generate initial baseline implementation."""
    logger.info("Starting node_draft")

    class Schema(BaseModel):
        plan: str
        code: str
        dependencies: list[str]

    llm = init_chat_model(model=runtime.context.model, temperature=runtime.context.temperature)
    llms = llm.with_structured_output(Schema)
    prompt = PROMPT_DRAFT.format(idea=state.idea, memory=state.memory)
    
    logger.info("Calling LLM for draft")
    response: Schema = await llms.ainvoke(prompt)  # type: ignore

    state.plan = response.plan
    state.code = response.code
    state.dependencies = response.dependencies
    state.iteration = 1

    logger.info("node_draft completed")
    return state


async def node_improve(state: State, runtime: Runtime[Context]) -> State:
    """Improve existing implementation based on feedback."""
    logger.info("Starting node_improve")

    class Schema(BaseModel):
        plan: str
        code: str
        dependencies: list[str]

    # Construct feedback from previous execution
    feedback = f"Return code: {state.returncode}\n"
    if state.stderr:
        feedback += f"Errors: {state.stderr}\n"
    if state.stdout:
        feedback += f"Output: {state.stdout[:500]}\n"

    llm = init_chat_model(model=runtime.context.model, temperature=runtime.context.temperature)
    llms = llm.with_structured_output(Schema)
    prompt = PROMPT_IMPROVE.format(
        idea=state.idea,
        memory=state.memory,
        previous_code=state.code or "",
        feedback=feedback
    )
    
    logger.info("Calling LLM for improvement")
    response: Schema = await llms.ainvoke(prompt)  # type: ignore

    state.plan = response.plan
    state.code = response.code
    state.dependencies = response.dependencies
    state.iteration += 1

    logger.info("node_improve completed")
    return state


async def node_run(state: State, runtime: Runtime[Context]) -> State:
    """Execute the generated code."""
    logger.info("Starting node_run")

    code = state.code or ""
    dependencies = state.dependencies or []

    if not code:
        state.returncode = -1
        state.stderr = "No code to execute"
        state.stdout = "No code to execute"
        return state

    result = await utils.exec_code(code, dependencies)
    state.stdout = result.stdout
    state.stderr = result.stderr
    state.returncode = result.returncode

    logger.info(f"node_run completed with return code: {state.returncode}")
    return state


async def node_check_completion(state: State, runtime: Runtime[Context]) -> State:
    """Check if the stage is complete."""
    logger.info("Starting node_check_completion")

    class Schema(BaseModel):
        is_complete: bool
        reasoning: str
        missing_criteria: list[str]

    llm = init_chat_model(model=runtime.context.model, temperature=runtime.context.temperature)
    llms = llm.with_structured_output(Schema)
    
    prompt = PROMPT_CHECK_COMPLETION.format(
        metric=state.metric_value or "N/A",
        has_code=bool(state.code),
        returncode=state.returncode,
        stderr=state.stderr[:200] if state.stderr else "None",
        goals=state.goals
    )
    
    logger.info("Calling LLM for completion check")
    response: Schema = await llms.ainvoke(prompt)  # type: ignore

    state.is_complete = response.is_complete
    state.completion_reason = response.reasoning

    if not response.is_complete and response.missing_criteria:
        state.completion_reason += f" Missing: {', '.join(response.missing_criteria)}"

    logger.info(f"Completion check: {state.is_complete} - {state.completion_reason}")
    return state


def should_continue(state: State) -> Literal["improve", "end"]:
    """Decide whether to continue improving or end."""
    # End if complete
    if state.is_complete:
        logger.info("Stage complete, ending")
        return "end"
    
    # End if max iterations reached
    if state.iteration >= state.max_iterations:
        logger.info(f"Max iterations ({state.max_iterations}) reached, ending")
        return "end"
    
    # Continue improving
    logger.info(f"Continuing to improve (iteration {state.iteration})")
    return "improve"


def build() -> CompiledStateGraph[State, Context, State, State]:
    builder = StateGraph(state_schema=State, context_schema=Context)

    # Add nodes
    builder.add_node("draft", node_draft)
    builder.add_node("improve", node_improve)
    builder.add_node("run", node_run)
    builder.add_node("check_completion", node_check_completion)
    
    # Add edges
    builder.add_edge(START, "draft")
    builder.add_edge("draft", "run")
    builder.add_edge("run", "check_completion")
    builder.add_edge("improve", "run")

    builder.add_conditional_edges(
        "check_completion",
        should_continue,
        {"improve": "improve", "end": END}
    )

    return builder.compile()  # type: ignore
