import base64
import logging
import operator
from pathlib import Path
from typing import Annotated, Any, TypedDict

from langchain.chat_models import BaseChatModel, init_chat_model
from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import cast
from langgraph.graph.state import CompiledStateGraph
from langgraph.runtime import Runtime
from langgraph.types import Checkpointer, Send
from pydantic import BaseModel

from aigraph import utils
from aigraph.agents import coder

logger = logging.getLogger(__name__)


PROMPT_PLOTTER_CODE = """
## Introduction

You are an AI researcher. You have run an experiment and generated results in
`data_ablation.json`. Your task is to write a Python script to visualize these
results using matplotlib or seaborn.

## Input Variables

- task: Research task with hypothesis and goals for context.
- code: Experiment code that generated the data to plot.
- memory: Historical notes from aigraph.agents.experiment import PROMPT_PLOTTER
  from previous plotting attempts.

## Instructions

- Write a Python script to load `data_ablation.json` and generate plots.
- The `data_ablation.json` file has the following structure:

```json
{{
    "dataset_name_1": {{
        "metrics": {{ "train": [], "val": [] }},
        "losses": {{ "train": [], "val": [] }},
        "predictions": [],
        "ground_truth": [],
    }},
    "dataset_name_2": {{
        "metrics": {{ "train": [], "val": [] }},
        "losses": {{ "train": [], "val": [] }},
        "predictions": [],
        "ground_truth": [],
    }}
}}
```

- Create standard visualizations (learning curves, sample comparisons,
    etc.).
- Save all plots as .png or .pdf files in the current directory.
- Do NOT use `plt.show()`.
- Handle potential missing keys gracefully.

### Response format

Your response should use structured json outputs in the following format:

- plan: A brief outline/sketch of your proposed solution in natural language
    (7-10 sentences)
- code: A python script in plain python. DO NOT USE FENCES. EG:
    \\`\\`\\`python ... \\`\\`\\`
- dependencies: A list of dependencies required for the code to run. EG:
    ["matplotlib", "seaborn", "numpy", "pandas"]. NEVER include Python standard
    library dependencies (e.g., json, os, sys, pathlib). ALWAYS only include
    third-party packages.

### Coding Guidelines

- Import necessary libraries (matplotlib.pyplot, json, os, etc.).
- Load data: `with open('data_ablation.json', 'r') as f: data =
    json.load(f)`
- Iterate through datasets/metrics in the JSON to create relevant plots.
- Save figures with descriptive names, e.g., `loss_curves.png`,
    `predictions_vs_truth.png`.
- Always close figures: `plt.close()`.
- Use try/except blocks for robustness if unsure about data shape.

## Research idea

<RESEARCH_IDEA>
{prompt}
</RESEARCH_IDEA>
"""


PROMPT_PLOTTER_OUTPUT = """
## Introduction

You are an AI researcher. You have executed a plotting script to visualize
experiment results. Evaluate plotting execution, visualization quality,
and scientific interpretability.

## Input Variables

- task: Research task with hypothesis and goals for context.
- code: The plotting code that was executed.
- stdout: Standard output from running the plotting code.
- stderr: Error output from running the plotting code.

## Analysis Requirements

Provide structured analysis covering:

1. **Execution Status**: Success or failure with specific errors
2. **Plot Generation**:
    - Were expected plot files created?
    - All datasets visualized?
    - File naming and formats correct?
3. **Implementation Quality**:
    - Coding errors (matplotlib, data loading issues)
    - Logic flaws (wrong data plotted)
    - Missing visualizations
4. **Visualization Validity**:
    - Do plots accurately represent data?
    - Appropriate plot types chosen?
    - Labels, legends, titles clear?
5. **Scientific Value**:
    - Do visualizations support hypothesis testing?
    - Key trends/patterns visible?
    - Comparisons clearly shown?
6. **Suggestions**: Additional plots needed or visualization improvements

## Research idea

<RESEARCH_IDEA>
{prompt}
</RESEARCH_IDEA>
"""


PROMPT_ANALYZE_PLOTS = """
## Introduction

You are an AI researcher. You have generated plots from your experiment
results. Your task is to analyze these plots to interpret the scientific
findings.

## Instructions

- Analyze the provided plot images.
- Describe the trends you observe (e.g., convergence, overfitting,
    performance comparison).
- Relate the findings back to the hypothesis.
- Conclude if the hypothesis is supported or rejected.
- Provide a relevancy score (integer 0-10) indicating how important this
    plot is for the final paper. 0 means irrelevant, 10 means critical.

## Input Variables

- research_idea: Research idea with hypothesis and goals for context.

## Research idea

<RESEARCH_IDEA>
{prompt}
</RESEARCH_IDEA>
"""


class State(BaseModel):
    # inputs
    cwd: Path
    prompt: str

    # coder subgraph outputs
    plotting_code: str | None = None
    plotting_deps: list[str] = []

    # plots output
    plots: Annotated[list[utils.Plot], operator.add] = []


class Context(BaseModel):
    model: str = "gpt-4o-mini"
    temperature: float = 0.0
    max_attempts: int = 5

    @property
    def llm(self) -> BaseChatModel:
        return init_chat_model(model=self.model, temperature=self.temperature)


async def node_generate_plotting_code(
    state: State, runtime: Runtime[Context]
) -> dict[str, Any]:
    logger.info("Starting node_generate_plotting_code")

    # Create coder state
    coder_state = coder.State(
        cwd=state.cwd,
        prompt_code=PROMPT_PLOTTER_CODE.format(prompt=state.prompt),
        prompt_review=PROMPT_PLOTTER_OUTPUT.format(prompt=state.prompt),
    )

    # Create coder context
    coder_context = coder.Context(
        filename=Path("plotting.py"),
        model=runtime.context.model,
        temperature=runtime.context.temperature,
        max_attempts=runtime.context.max_attempts,
    )

    # Build and run coder graph
    graph = coder.build(checkpointer=True)
    result = await graph.ainvoke(coder_state, context=coder_context)
    result = coder.State.model_validate(result)

    assert result.code is not None, "Code is required"

    logger.debug(f"plotting_code: {result.code.code[:32]!r}")
    logger.debug(f"plotting_deps: {result.code.dependencies}")

    logger.info("Finished node_generate_plotting_code")
    return {
        "plotting_code": result.code.code,
        "plotting_deps": result.code.dependencies,
    }


class StateSinglePlot(TypedDict, total=False):
    cwd: Path
    image: Path
    prompt: str


async def node_dispatch_plot_analysis(
    state: State, runtime: Runtime[Context]
) -> list[Send]:
    logger.info("Starting node_dispatch_plot_analysis")

    pngs = sorted(list(state.cwd.glob("*.png")))
    for png in pngs:
        logger.debug(f"Found PNG: {png}")

    sends: list[Send] = []
    for png in pngs:
        st = StateSinglePlot(cwd=state.cwd, image=png, prompt=state.prompt)
        sends.append(Send("node_analyze_single_plot", st))

    return sends


async def node_analyze_single_plot(
    state: StateSinglePlot, runtime: Runtime[Context]
) -> dict:
    logger.info("Starting node_analyze_single_plot")

    image = state.get("image")
    assert image is not None, "Image is required"

    class Schema(BaseModel):
        analysis: str
        relevancy_score: int

    messages: list[BaseMessage] = [
        SystemMessage(
            PROMPT_ANALYZE_PLOTS.format(
                prompt=state.get("prompt", "NA"),
            )
        ),
        HumanMessage(
            content=[
                {
                    "type": "text",
                    "text": f"Analyze: {image.name}",
                },
                {
                    "type": "image",
                    "base64": base64.b64encode(image.read_bytes()).decode("utf-8"),
                    "mime_type": "image/png",
                },
            ]
        ),
    ]

    llms = runtime.context.llm.with_structured_output(Schema)
    response = await llms.ainvoke(messages)
    response = cast(Schema, response)

    logger.debug(f"image: {image}")
    logger.debug(f"analysis: {response.analysis[:32]!r}")
    logger.debug(f"relevancy_score: {response.relevancy_score}")

    logger.info("Finished node_analyze_single_plot")
    return {
        "plots": [
            utils.Plot(
                path=image,
                analysis=response.analysis,
                relevancy_score=response.relevancy_score,
            )
        ]
    }


def build(checkpointer: Checkpointer = None) -> CompiledStateGraph[State, Context]:
    builder = StateGraph(State, Context)

    builder.add_node("node_generate_plotting_code", node_generate_plotting_code)
    builder.add_node("node_analyze_single_plot", node_analyze_single_plot)

    builder.add_edge(START, "node_generate_plotting_code")
    builder.add_conditional_edges(
        "node_generate_plotting_code",
        node_dispatch_plot_analysis,
        ["node_analyze_single_plot"],
    )
    builder.add_edge("node_analyze_single_plot", END)

    return builder.compile(name="graph_plotter", checkpointer=checkpointer)  # type: ignore
