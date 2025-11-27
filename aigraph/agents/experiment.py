import logging
import operator as op
from pathlib import Path
from typing import Annotated, Any

from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph
from langgraph.runtime import Runtime
from langgraph.types import Checkpointer
from pydantic import BaseModel

from aigraph import utils
from aigraph.agents import coder, plotter, writer

logger = logging.getLogger(__name__)

PROMPT_EXPERIMENT_CODE = """
## Introduction

You are an expert Python programmer and ML researcher. Your task is to write a
Python script that implements the following experiment.

## Instructions

### Response format

Your response should use structured json outputs in the following format:

- plan: A brief outline/sketch of your proposed solution in natural language
  (7-10 sentences)
- code: A python script in plain python. DO NOT USE FENCES. EG: \\`\\`\\`python
  ... \\`\\`\\`
- dependencies: A list of dependencies required for the code to run. EG:
  ["torch", "torchvision", "numpy", "pandas", "scikit-learn"]. NEVER include
  Python standard library dependencies (e.g., json, os, sys, pathlib). ALWAYS
  only include third-party packages.

### Implementation guidelines

#### CRITICAL GPU REQUIREMENTS

Your code MUST include ALL of these:

- At the start of your code, add these lines to handle GPU/CPU:
  ```python
  device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
  print(f'Using device: {{device}}')
  ```
- ALWAYS move models to device using the `.to(device)` method
- ALWAYS move input tensors to device using the `.to(device)` method
- ALWAYS move model related tensors to device using the `.to(device)` method
- For optimizers, create them AFTER moving model to device
- When using DataLoader, move batch tensors to device in training loop:
  ```python
  batch = {{k: v.to(device) for k, v in batch.items() if isinstance(v, torch.Tensor)}}
  ```

#### CRITICAL MODEL INPUT GUIDELINES

- Always pay extra attention to the input to the model being properly normalized
- This is extremely important because the input to the model's forward pass
  directly affects the output, and the loss function is computed based on the
  output

For generative modeling tasks, you must:

- Generate a set of samples from your model
- Compare these samples with ground truth data using appropriate visualizations

#### CODING GUIDELINES

- Do NOT put any execution code inside 'if __name__ == "__main__":' block
- All code should be at the global scope or in functions that are called from
  the global scope
- The script should execute immediately when run, without requiring any special
  entry point or args. Should be executable by running `python script.py`.
- Store any extra files and outputs in the current directory.
- DO NOT CREATE ANY PLOTS! USING PLOTS IS NOT ALLOWED.

#### Data saving requirements

Save all data (metrics, losses, predictions, etc.) as JSON following the
following structure:

```python
# At the start of your code
experiment_data = {{
    'dataset_name_1': {{
        'metrics': {{'train': [], 'val': []}},
        'losses': {{'train': [], 'val': []}},
        'predictions': [],
        'ground_truth': [],
        # Add other relevant data
    }},
    # Add additional datasets as needed:
    'dataset_name_2': {{
        'metrics': {{'train': [], 'val': []}},
        'losses': {{'train': [], 'val': []}},
        'predictions': [],
        'ground_truth': [],
        # Add other relevant data
    }},
}}
```

CRITICAL: Your experiment_data dictionary MUST ALWAYS include these four
required keys for each dataset:

- 'metrics': Dictionary with 'train' and 'val' lists
- 'losses': Dictionary with 'train' and 'val' lists  
- 'predictions': List of model predictions
- 'ground_truth': List of ground truth values

These keys are MANDATORY and must be present even if some remain empty lists.

YOU MUST APPEND THE DATA TO THE STRUCTURE ABOVE FOR EACH EPOCH. Like so (update
the code to your specific logic):

```python
for epoch in range(num_epochs):
    # logic
    train_metric = ...
    val_metric = ...
    train_loss = ...
    val_loss = ...
    
    # REQUIRED: Always append to these four mandatory keys
    experiment_data['dataset_name_1']['metrics']['train'].append(train_metric)
    experiment_data['dataset_name_1']['metrics']['val'].append(val_metric)
    experiment_data['dataset_name_1']['losses']['train'].append(train_loss)
    experiment_data['dataset_name_1']['losses']['val'].append(val_loss)
    
    # Update predictions and ground_truth as appropriate for your experiment
    if predictions_available:
        experiment_data['dataset_name_1']['predictions'].extend(batch_predictions)
    if ground_truth_available:
        experiment_data['dataset_name_1']['ground_truth'].extend(batch_ground_truth)
```

#### CRITICAL EVALUATION REQUIREMENTS

Your code MUST include ALL of these:

1. ALWAYS print the dataset name at the start of training for that dataset:
   ```python
   print(f'Training on dataset: {{dataset_name}}')
   ```
2. ALWAYS print epoch number, validation loss, and ALL metrics at EACH epoch:
   ```python
   print(f'Epoch {{epoch}}: val_loss={{val_loss:.4f}}, val_metric={{val_metric:.4f}}')
   ```
3. Track and update ALL metrics passed below
4. Update metrics at EACH epoch
5. Save ALL metrics at the end. You must use the filename `results.json`:
   ```python
   import os
   import json
   with open(os.path.join(os.getcwd(), 'results.json'), 'w') as f:
       json.dump(experiment_data, f)
   ```

YOUR CODE MUST SAVE THE DATA IN THE `results.json` FILE.

## Experiment Description

<experiment_description>
{prompt}
</experiment_description>
"""

PROMPT_EXPERIMENT_CODE_REVIEW = """
## Introduction

You are an experienced AI researcher. You have written code for your
research experiment and now need to evaluate the output of the code
execution. Provide comprehensive analysis of implementation quality,
experimental validity, and actionable suggestions.

## Input Variables

- prompt: Research task with hypothesis and goals for context.
- code: The experiment code that was executed.
- stdout: Standard output from running the experiment code.
- stderr: Error output from running the experiment code.

## Analysis Requirements

Provide structured analysis covering:

1. **Execution Status**: Success or failure with specific errors
2. **Implementation Quality**:
   - Coding errors (syntax, runtime, exceptions)
   - Logic flaws (incorrect formulas, missing steps)
   - Design issues (doesn't match research hypothesis)
3. **Output Validity**:
   - Do metrics show reasonable convergence patterns?
   - Are loss values in expected ranges (not NaN/inf)?
   - Do predictions align with ground truth distributions?
   - Are multiple datasets properly evaluated?
4. **Experimental Soundness**:
   - Proper data splits and evaluation?
   - Sufficient training epochs/iterations?
   - All required metrics tracked correctly?
   - Data saved in correct format?
5. **Hypothesis Alignment**:
   - Does implementation test the stated hypothesis?
   - Are results interpretable for research goals?
6. **Suggestions**: Concrete improvements for next iteration

## Research idea

<RESEARCH_IDEA>
{prompt}
</RESEARCH_IDEA>
"""

PROMPT_EXPERIMENT_PARSER = """
## Introduction

You are an AI researcher analyzing experimental results stored in a JSON
file. Write code to load and analyze the metrics from a file named
'results.json'. It has the following structure:

## Input Variables

- prompt: Experiment description for context on expected outputs.
- code: Original experiment code to understand data structure.
- stdout: Standard output from running the experiment code.

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
    }},
}}
```

### Response format

Your response should use structured json outputs in the following format:

- plan: A brief outline/sketch of your proposed solution in natural language
  (7-10 sentences)
- code: A python script in plain python. DO NOT USE FENCES. EG:
  \\`\\`\\`python ... \\`\\`\\`
- dependencies: A list of dependencies required for the code to run. EG:
  ["torch", "torchvision", "numpy", "pandas", "scikit-learn"]. NEVER
  include Python standard library dependencies (e.g., json, os, sys, pathlib).
  ALWAYS only include third-party packages.

## Instructions

- Load the `results.json` file, which is located in the current
  directory
- Extract metrics for each dataset. Refer to the original code to understand
  the data structure.
- Always print the name of the dataset before printing the metrics
- Always print the name of the metric before printing the value with precise
  labels (e.g., 'train accuracy', 'validation loss', 'test F1 score').
- Only print the best or final value for each metric for each dataset
- DO NOT CREATE ANY PLOTS. PLOTS ARE NOT ALLOWED.

### CODING GUIDELINES

- Do NOT put any execution code inside 'if __name__ == "__main__":' block
- All code should be at the global scope or in functions that are called
  from the global scope
- The script should execute immediately when run, without requiring any
  special entry point or args. Should be executable py running `python
  script.py`.
- Store any extra files and outputs in the current directory.

## Example data loading code

```python
import os
import json
with open(os.path.join(os.getcwd(), 'results.json')) as f:
    experiment_data = json.load(f)
```

## Experiment Description

<EXPERIMENT_DESCRIPTION>
{prompt}
</EXPERIMENT_DESCRIPTION>

## Context

Here is the original code that was used to generate the `results.json`
file:

<ORIGINAL_CODE>
{experiment_code}
</ORIGINAL_CODE>

## Stdout

<STDOUT>
{experiment_stdout}
</STDOUT>

## Stderr

<STDERR>
{experiment_stderr}
</STDERR>
"""

PROMPT_EXPERIMENT_PARSER_REVIEW = """
## Introduction

You are an experienced AI researcher. You have written code to parse and
analyze the results of your research experiment. Evaluate the parser
execution, data extraction quality, and result interpretation validity.

## Input Variables

- code: Parser code that was executed to analyze results.
- stdout: Standard output from running the parser code.
- stderr: Error output from running the parser code.
- original_code: Original baseline experiment code for reference.

## Analysis Requirements

Provide structured analysis covering:

1. **Parsing Success**: Were all expected metrics extracted?
2. **Data Consistency**: 
    - Do extracted values match experiment logs?
    - Are all datasets represented?
    - Correct identification of best/final values?
3. **Result Interpretation**:
    - Are reported metrics meaningful?
    - Do values make scientific sense?
    - Are trends/patterns correctly identified?
4. **Completeness Check**:
    - All required metrics reported?
    - Missing comparisons or analysis?
    - Dataset-specific results shown?
5. **Presentation Quality**:
    - Clear labeling of metrics?
    - Proper formatting of values?
6. **Suggestions**: Better presentation or additional metrics to report

## Original Experiment Code

<ORIGINAL_CODE>
{original_code}
</ORIGINAL_CODE>

## Parser Implementation

<PARSER_IMPLEMENTATION>
{code}
</PARSER_IMPLEMENTATION>

## Stdout

<STDOUT>
{stdout}
</STDOUT>

## Stderr

<STDERR>
{stderr}
</STDERR>
"""


PROMPT_PLOTTER = """Create plots for this experiment:

{prompt}

Read data from results.json"""

PROMPT_WRITER_WRITE = """Write a concise research report based on this experiment.

{context}

Include:
- Brief summary of the experiment
- Key findings from the results
- Mention any plots generated
"""

PROMPT_WRITER_REVIEW = """Review this research report.

Check:
- Clarity and conciseness
- Accurate representation of results
- Proper structure

Provide summary, strengths, weaknesses, and decision (Accept/Reject)."""


class State(BaseModel):
    # inputs
    cwd: Path
    prompt: str

    # outputs
    experiment_code: coder.Code | None = None
    experiment_execution: coder.Execution | None = None
    parser_code: coder.Code | None = None
    parser_execution: coder.Execution | None = None
    plots: Annotated[list[utils.Plot], op.add] = []
    report: str | None = None


class Context(BaseModel):
    model: str = "gpt-4o-mini"
    temperature: float = 0.0
    max_attempts: int = 5


async def node_generate_experiment(
    state: State, runtime: Runtime[Context]
) -> dict[str, Any]:
    logger.info("Starting node_generate_experiment")

    coder_state = coder.State(
        cwd=state.cwd,
        prompt_code=PROMPT_EXPERIMENT_CODE.format(prompt=state.prompt),
        prompt_review=PROMPT_EXPERIMENT_CODE_REVIEW.format(prompt=state.prompt),
    )

    coder_context = coder.Context(
        filename=Path("experiment.py"),
        model=runtime.context.model,
    )

    graph = coder.build(checkpointer=True)
    result = await graph.ainvoke(coder_state, context=coder_context)
    result = coder.State.model_validate(result)

    assert result.code is not None, "Code is required"
    assert result.execution is not None, "Execution is required"

    logger.debug(f"Experiment code: {result.code.code[:32]!r}")
    logger.debug(f"Experiment dependencies: {result.code.dependencies}")
    logger.debug(f"Experiment return code: {result.execution.returncode}")
    logger.debug(f"Experiment stdout: {result.execution.stdout[:32]!r}")
    logger.debug(f"Experiment stderr: {result.execution.stderr[:32]!r}")
    logger.debug(f"Experiment filename: {result.execution.filename}")

    logger.info("Finished node_generate_experiment")
    return {
        "experiment_code": result.code,
        "experiment_execution": result.execution,
    }


async def node_generate_parser(
    state: State, runtime: Runtime[Context]
) -> dict[str, Any]:
    logger.info("Starting node_generate_parser")
    assert state.experiment_code, "Experiment code required"
    assert state.experiment_execution, "Experiment execution required"

    coder_state = coder.State(
        cwd=state.cwd,
        prompt_code=PROMPT_EXPERIMENT_PARSER.format(
            prompt=state.prompt,
            experiment_code=state.experiment_code.code,
            experiment_stdout=state.experiment_execution.stdout,
        ),
        prompt_review=PROMPT_EXPERIMENT_PARSER_REVIEW.format(
            code=state.experiment_code.code,
            stdout=state.experiment_execution.stdout,
            stderr=state.experiment_execution.stderr,
            original_code=state.experiment_code.code,
        ),
    )

    coder_context = coder.Context(
        filename=Path("parser.py"),
        model=runtime.context.model,
    )

    graph = coder.build(checkpointer=True)
    result = await graph.ainvoke(coder_state, context=coder_context)
    result = coder.State.model_validate(result)

    assert result.code is not None, "Code is required"
    assert result.execution is not None, "Execution is required"

    logger.debug(f"Parser code: {result.code.code[:32]!r}")
    logger.debug(f"Parser dependencies: {result.code.dependencies}")
    logger.debug(f"Parser return code: {result.execution.returncode}")
    logger.debug(f"Parser stdout: {result.execution.stdout[:32]!r}")
    logger.debug(f"Parser stderr: {result.execution.stderr[:32]!r}")
    logger.debug(f"Parser filename: {result.execution.filename}")

    logger.info("Finished node_generate_parser")
    return {
        "parser_code": result.code,
        "parser_execution": result.execution,
    }


async def node_generate_plotter(
    state: State, runtime: Runtime[Context]
) -> dict[str, Any]:
    logger.info("Starting node_generate_plotter")

    plotter_state = plotter.State(
        cwd=state.cwd,
        prompt=PROMPT_PLOTTER.format(prompt=state.prompt),
    )

    plotter_context = plotter.Context(
        model=runtime.context.model,
        temperature=runtime.context.temperature,
        max_attempts=runtime.context.max_attempts,
    )

    graph = plotter.build()
    result = await graph.ainvoke(
        plotter_state, config={"configurable": plotter_context.model_dump()}
    )

    logger.debug(f"Generated {len(result.get('plots', []))} plots")

    logger.info("Finished node_generate_plotter")
    return {"plots": result.get("plots", [])}


async def node_generate_writer(
    state: State, runtime: Runtime[Context]
) -> dict[str, Any]:
    logger.info("Starting node_generate_writer")

    # Build context from experiment results
    context = """Experiment Description:
{prompt}

Experiment Code:
```python
{experiment_code}
```

Parser Output:
{parser_output}

Plots Generated: {num_plots}
""".format(
        prompt=state.prompt,
        experiment_code=state.experiment_code.code if state.experiment_code else "N/A",
        parser_output=state.parser_execution.stdout
        if state.parser_execution
        else "N/A",
        num_plots=len(state.plots),
    )

    writer_state = writer.State(
        prompt_write=PROMPT_WRITER_WRITE.format(context=context),
        prompt_review=PROMPT_WRITER_REVIEW,
    )

    writer_context = writer.Context(
        model=runtime.context.model,
        temperature=runtime.context.temperature,
        max_attempts=runtime.context.max_attempts,
    )

    graph = writer.build()
    result = await graph.ainvoke(
        writer_state, config={"configurable": writer_context.model_dump()}
    )

    logger.debug(f"Report length: {len(result.get('report', ''))}")

    logger.info("Finished node_generate_writer")
    return {"report": result.get("report", "")}


def build(
    checkpointer: Checkpointer = None,
) -> CompiledStateGraph[State, Context, State, State]:
    """Build the experiment agent graph"""
    builder = StateGraph(state_schema=State, context_schema=Context)

    builder.add_node("node_generate_experiment", node_generate_experiment)
    builder.add_node("node_generate_parser", node_generate_parser)
    builder.add_node("node_generate_plotter", node_generate_plotter)
    builder.add_node("node_generate_writer", node_generate_writer)

    builder.add_edge(START, "node_generate_experiment")
    builder.add_edge("node_generate_experiment", "node_generate_parser")
    builder.add_edge("node_generate_parser", "node_generate_plotter")
    builder.add_edge("node_generate_plotter", "node_generate_writer")
    builder.add_edge("node_generate_writer", END)

    return builder.compile(name="graph_experiment", checkpointer=checkpointer)  # type: ignore
