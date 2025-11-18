import logging
from operator import add
from typing import Annotated, Literal

from langchain.chat_models import init_chat_model
from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph
from langgraph.runtime import Runtime
from pydantic import BaseModel

from aigraph import utils

logger = logging.getLogger(__name__)


PROMPT_PROPOSE_HYPERPARAM = """
You are an AI researcher conducting hyperparameter tuning for baseline
experiments. Based on the current implementation and previous hyperparameter
tuning attempts (if any), propose ONE new hyperparameter tuning idea to see if
it improves the performance.

You should first check if simply training longer (more epochs) improves the
performance. Then try tuning common hyperparameters such as learning rate, batch
size, etc. Only propose algorithm-specific and/or model-specific hyperparameters
after you have tried the above.

## Base code you are working on

{base_code}

## Previous Hyperparam Tuning Attempts

{tried_hyperparams}

## Requirements

1. Identify ONE specific hyperparameter to tune
2. Ensure the hyperparameter is different from previous attempts
"""


PROMPT_IMPLEMENT_TUNING = """
You are an experienced AI researcher. You are provided with a previously
developed baseline implementation. Your task is to implement hyperparameter
tuning for the following idea:

**{hyperparam_name}**

{hyperparam_description}

## Base code you are working on

```python
{base_code}
```

## Implementation Guidelines

- The code should be a single-file python program that is self-contained and can
  be executed as-is.
- No parts of the code should be skipped, don't terminate the code execution
  before finishing the script.
- Data saving requirements:
  * Save all plottable data (metrics, losses, predictions, etc.) as numpy arrays
    using np.save()
  * Use the following naming convention for saved files:
    ```python
    # At the start of your code
    experiment_data = {{
        'hyperparam_tuning_type_1': {{
            'dataset_name_1': {{
                'metrics': {{'train': [], 'val': []}},
                'losses': {{'train': [], 'val': []}},
                'predictions': [],
                'ground_truth': [],
            }},
        }},
    }}
    ```
  * Make sure to use a filename 'experiment_data.npy' to save the data. Do not
    use any other filename.
"""


PROMPT_EVALUATE_SUBSTAGE = """
Evaluate if Stage 2 (baseline tuning) sub-stage is complete.

## Evidence

- Datasets tested: {datasets_tested}
- Best metric: {best_metric}
- Return code: {returncode}
- Stderr: {stderr}

## Requirements for completion

{goals}
"""


PROMPT_EVALUATE_STAGE = """
Evaluate if Stage 2 (baseline tuning) is complete based on the following
evidence:

## Evidence

- Datasets tested: {datasets_tested}
- Best metric: {best_metric}
- Hyperparameters tried successfully: {tried_hyperparams}

## Requirements for completion

1. Training curves should show stable convergence
2. Results should be tested on at least two datasets
3. No major instabilities or issues in the plots

Provide a detailed evaluation of completion status.
"""


class ProposeHyperparamSchema(BaseModel):
    name: str
    description: str


class ImplementTuningSchema(BaseModel):
    code: str
    dependencies: list[str]


class EvaluateSchema(BaseModel):
    is_complete: bool
    reasoning: str
    missing_criteria: list[str]


class State(BaseModel):
    # inputs
    idea: str
    base_code: str
    goals: str = (
        "- Change hyperparameters such as learning rate, number of epochs, "
        "batch size, etc. to improve the performance\n"
        "- DO NOT change the model architecture from the previous stage\n"
        "- Introduce additional datasets from HuggingFace to test the model. "
        "Use dataset sizes appropriate to the experiment. "
        "Use streaming=True for very large datasets."
    )

    # tracking - using reducers for lists
    tried_hyperparams: Annotated[list[str], add] = []
    current_hyperparam_name: str | None = None
    current_hyperparam_description: str | None = None
    iteration_count: int = 0
    substage_iteration: int = 0

    # execution results
    code: str | None = None
    dependencies: list[str] | None = None
    returncode: int | None = None
    stdout: str | None = None
    stderr: str | None = None
    datasets_tested: Annotated[list[str], add] = []
    best_metric: float | None = None

    # completion tracking
    substage_complete: bool = False
    stage_complete: bool = False


class Context(BaseModel):
    model: str = "gpt-4o-mini"
    temperature: float = 0.0
    max_iterations: int = 5
    max_substage_iterations: int = 3


async def node_propose_hyperparam(state: State, runtime: Runtime[Context]) -> State:
    """Propose the next hyperparameter to tune."""
    logger.info("Starting node_propose_hyperparam")

    llm = init_chat_model(
        model=runtime.context.model, temperature=runtime.context.temperature
    )
    llms = llm.with_structured_output(ProposeHyperparamSchema)

    tried_list = state.tried_hyperparams or ["Nothing has been tried yet."]
    prompt = PROMPT_PROPOSE_HYPERPARAM.format(
        base_code=state.base_code,
        tried_hyperparams="\n".join(f"- {hp}" for hp in tried_list),
    )

    logger.info("Calling LLM to propose hyperparameter")
    response: ProposeHyperparamSchema = await llms.ainvoke(prompt)  # type: ignore

    state.current_hyperparam_name = response.name
    state.current_hyperparam_description = response.description
    state.substage_iteration = 0

    logger.info(f"Proposed hyperparameter: {response.name}")
    return state


async def node_implement_tuning(state: State, runtime: Runtime[Context]) -> State:
    """Generate tuning code based on the proposed hyperparameter."""
    logger.info("Starting node_implement_tuning")

    llm = init_chat_model(
        model=runtime.context.model, temperature=runtime.context.temperature
    )
    llms = llm.with_structured_output(ImplementTuningSchema)

    prompt = PROMPT_IMPLEMENT_TUNING.format(
        hyperparam_name=state.current_hyperparam_name or "unknown",
        hyperparam_description=state.current_hyperparam_description or "",
        base_code=state.base_code,
    )

    logger.info("Calling LLM to implement tuning")
    response: ImplementTuningSchema = await llms.ainvoke(prompt)  # type: ignore

    state.code = response.code
    state.dependencies = response.dependencies

    logger.info(f"Generated {len(response.code)} characters of tuning code")
    return state


async def node_run(state: State, runtime: Runtime[Context]) -> State:
    """Execute the generated tuning code."""
    logger.info("Starting node_run")

    code = state.code or ""
    dependencies = state.dependencies or []

    if not code:
        state.returncode = 1
        state.stderr = "No code to execute"
        state.substage_iteration = state.substage_iteration + 1
        return state

    result = await utils.exec_code(code, dependencies)
    state.stdout = result.stdout
    state.stderr = result.stderr
    state.returncode = result.returncode
    state.substage_iteration = state.substage_iteration + 1

    logger.info(f"node_run completed with returncode: {result.returncode}")
    return state


async def node_evaluate_substage(state: State, runtime: Runtime[Context]) -> State:
    """Evaluate if the current substage is complete."""
    logger.info("Starting node_evaluate_substage")

    llm = init_chat_model(
        model=runtime.context.model, temperature=runtime.context.temperature
    )
    llms = llm.with_structured_output(EvaluateSchema)

    datasets_info = (
        ", ".join(state.datasets_tested) if state.datasets_tested else "Unknown"
    )
    prompt = PROMPT_EVALUATE_SUBSTAGE.format(
        datasets_tested=datasets_info,
        best_metric=state.best_metric or "N/A",
        returncode=state.returncode or "N/A",
        stderr=(state.stderr or "")[:200],
        goals=state.goals,
    )

    logger.info("Calling LLM to evaluate substage completion")
    response: EvaluateSchema = await llms.ainvoke(prompt)  # type: ignore

    state.substage_complete = response.is_complete

    logger.info(f"Substage evaluation: {response.is_complete} - {response.reasoning}")
    return state


async def node_evaluate_stage(state: State, runtime: Runtime[Context]) -> State:
    """Evaluate if the overall stage is complete."""
    logger.info("Starting node_evaluate_stage")

    llm = init_chat_model(
        model=runtime.context.model, temperature=runtime.context.temperature
    )
    llms = llm.with_structured_output(EvaluateSchema)

    datasets_info = (
        ", ".join(state.datasets_tested) if state.datasets_tested else "Unknown"
    )
    tried_info = (
        ", ".join(state.tried_hyperparams) if state.tried_hyperparams else "None"
    )

    prompt = PROMPT_EVALUATE_STAGE.format(
        datasets_tested=datasets_info,
        best_metric=state.best_metric or "N/A",
        tried_hyperparams=tried_info,
    )

    logger.info("Calling LLM to evaluate stage completion")
    response: EvaluateSchema = await llms.ainvoke(prompt)  # type: ignore

    state.stage_complete = response.is_complete
    state.iteration_count += 1

    logger.info(f"Stage evaluation: {response.is_complete} - {response.reasoning}")
    return state


def should_retry_substage(
    state: State, context: Context
) -> Literal["implement", "evaluate_stage"]:
    """Decide whether to retry the current substage or move to stage evaluation."""
    # If substage complete, move to stage evaluation
    if state.substage_complete:
        logger.info("Substage complete, moving to stage evaluation")
        return "evaluate_stage"

    # If max substage iterations reached, move to stage evaluation
    if state.substage_iteration >= context.max_substage_iterations:
        logger.info(
            f"Max substage iterations ({context.max_substage_iterations}) reached"
        )
        return "evaluate_stage"

    # Retry the substage
    logger.info(f"Retrying substage (iteration {state.substage_iteration})")
    return "implement"


def should_continue_stage(state: State, context: Context) -> Literal["propose", "end"]:
    """Decide whether to continue with another hyperparameter or end."""
    # End if stage complete
    if state.stage_complete:
        logger.info("Stage complete - ending")
        return "end"

    # End if max iterations reached
    if state.iteration_count >= context.max_iterations:
        logger.info(f"Max iterations ({context.max_iterations}) reached - ending")
        return "end"

    # Continue with next hyperparameter
    logger.info("Continuing with next hyperparameter")
    return "propose"


def build() -> CompiledStateGraph[State, Context, State, State]:
    """Build the Stage 2 hyperparameter tuning graph."""
    builder = StateGraph(state_schema=State, context_schema=Context)

    # Add nodes
    builder.add_node("propose", node_propose_hyperparam)
    builder.add_node("implement", node_implement_tuning)
    builder.add_node("run", node_run)
    builder.add_node("evaluate_substage", node_evaluate_substage)
    builder.add_node("evaluate_stage", node_evaluate_stage)

    # Add edges
    builder.add_edge(START, "propose")
    builder.add_edge("propose", "implement")
    builder.add_edge("implement", "run")
    builder.add_edge("run", "evaluate_substage")

    # Conditional: retry substage or evaluate stage
    builder.add_conditional_edges(
        "evaluate_substage",
        should_retry_substage,
        {"implement": "implement", "evaluate_stage": "evaluate_stage"},
    )

    # Conditional: continue with next hyperparam or end
    builder.add_conditional_edges(
        "evaluate_stage", 
        should_continue_stage, 
        {"propose": "propose", "end": END}
    )

    return builder.compile()  # type: ignore
