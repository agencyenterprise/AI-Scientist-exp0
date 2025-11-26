from typing import Iterable

from aigraph.utils import DATA_DIR, Metric, Task


def _task_to_prompt(task: Task) -> str:
    prompt = f"""
    You are an ambitious AI researcher who is looking to publish a paper that
    will contribute significantly to the field.

    You have an idea and you want to conduct creative experiments to gain
    scientific insights.

    Your aim is to run experiments to gather sufficient results for a top
    conference paper.

    Your research idea:

    Name:
    {task.name}

    Title:
    {task.title}

    Abstract:
    {task.abstract}

    Hypothesis:
    {task.short_hypothesis}

    Related Work:
    {task.related_work}

    Experiments:
    {"\n".join(f"- {exp}" for exp in task.experiments)}

    Risk Factors and Limitations:
    {"\n".join(f"- {risk}" for risk in task.risk_factors_and_limitations)}

    """

    if task.code:
        code = f"```python\n{task.code}\n```"
        return prompt + f"Code To Use:\n{code}\n"

    example = DATA_DIR / "code.py.txt"
    if not example.exists():
        return prompt

    code = example.read_text()
    code = f"```python\n{code}\n```"
    return prompt + f"Code To Use:\n{code}\n"


def build_prompt_propose_ablation(code: str, ablations: list[str]) -> str:
    attempted = ablations or ["Nothing has been tried yet."]

    return f"""
    You are an AI researcher conducting ablation studies. Based on the current
    implementation and previous ablations (if any), propose ONE new ablation
    study that tests a different aspect of the model.

    ## Input Variables

    - code: The baseline implementation code that will be modified for ablation studies.
    - ablations: List of previously attempted ablation studies to avoid duplication.

    ## Base code you are working on

    <CODE>
    ```python
    {code}
    ```
    </CODE>

    ## Previous Ablations

    <PREVIOUS_ABLATIONS>
    {"\n".join(f"- {i}" for i in attempted)}
    </PREVIOUS_ABLATIONS>

    ## Requirements

    1. Identify ONE specific component/feature to ablate
    2. Ensure the ablation is different from previous completed or running
       attempts
    3. The ablation should be a new idea, not a variation of previous ideas
    4. If you have only used a single synthetic dataset throughout the
       experiment, one of your ablations should be to use multiple synthetic
       datasets (at least 3 different datasets)

    ## Response format

    Your response should start with 'ABLATION NAME: <ablation name>' on the
    first line to represent the name of the ablation. The second line should
    start with 'ABLATION DESCRIPTION: <description>', a brief description of
    what component is being ablated and why (3-5 sentences).
    """


def build_prompt_code_ablation(
    task: Task,
    metrics: Iterable[Metric],
    name: str,
    description: str,
    code: str,
    memory: str,
    cumulative_summary: str = "",
    baseline_results: str = "",
) -> str:
    return f"""
    You are an experienced AI researcher. You are provided with a previously
    developed baseline implementation. Your task is to implement the ablation
    study for the following idea:
    
    ## Input Variables

    - task: Research task containing hypothesis, abstract, and experimental goals.
    - metrics: Evaluation metrics to track during the ablation experiment.
    - name: Name of the specific ablation study being conducted.
    - description: Detailed description of what component to ablate and why.
    - code: Baseline implementation code to modify for ablation.
    - memory: Historical notes from previous attempts to avoid repeating mistakes.
    - cumulative_summary: Summary of all experiments run so far for context.
    - baseline_results: Performance metrics from baseline to compare against.
    
    Name: {name}
    Description: {description}

    ## Base code you are working on
    
    ```python
    {code}
    ```
    
    ## Instructions
    
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

    ### Ablation study guidelines

    - Implement the ablation study idea described above.
    - The code should be a single-file python program that is self-contained and
      can be executed as-is.
    - No parts of the code should be skipped, don't terminate the code execution
      before finishing the script.
    - You MUST evaluate your solution on at least 3 different datasets to ensure
      robustness. Use standard benchmark datasets when available (e.g., MNIST,
      CIFAR-10, ImageNet, GLUE, SQuAD, etc.). Each dataset should be evaluated
      separately and results should be tracked per dataset in the experiment_data
      structure.

    ### Implementation guidelines

    - The code should be a single-file python program that is self-contained and
      can be executed as-is.
    - No parts of the code should be skipped, don't terminate the code execution
      before finishing the script.
    
    Data saving requirements:

    - Save all data (metrics, losses, predictions, etc.) as JSON following
      the following structure:
      ```python
      # At the start of your code
      experiment_data = {{
          'ablation_type_1': {{
              'dataset_name_1': {{
                  'metrics': {{'train': [], 'val': []}},
                  'losses': {{'train': [], 'val': []}},
                  'predictions': [],
                  'ground_truth': [],
              }},
          }},
      }}
      ```
    - Make sure to use a filename 'data_ablation.json' to save the data. Do not
      use any other filename.

    ### CRITICAL EVALUATION REQUIREMENTS

    Your code MUST include ALL of these:

    1. ALWAYS print the dataset name at the start of training for that dataset:
       ```python
       print(f'Training on dataset: {{dataset_name}}')
       ```
    2. ALWAYS print epoch number, validation loss, and ALL metrics at EACH epoch:
       ```python
       print(f'Epoch {{epoch}}: val_loss={{val_loss:.4f}}, val_metric={{val_metric:.4f}}')
       ```
    3. Track and update ALL metrics at EACH epoch
    4. Save ALL metrics at the end using 'data_ablation.json' filename

    ## Memory

    <MEMORY>
    {memory or "NA"}
    </MEMORY>

    ## Previous Experiment Summaries

    <PREVIOUS_SUMMARIES>
    {cumulative_summary or "No previous experiments have been run yet."}
    </PREVIOUS_SUMMARIES>

    ## Baseline Results (for comparison)

    <BASELINE_RESULTS>
    {baseline_results or "NA"}
    </BASELINE_RESULTS>

    Compare ablation results against baseline to understand component importance.
    """


def build_prompt_ablation_output(
    task: Task, code: str, stdout: str, stderr: str
) -> str:
    return f"""
    ## Introduction
    
    You are an experienced AI researcher. You have written code for your
    ablation study experiment. Provide comprehensive analysis of ablation
    implementation, component impact assessment, and actionable suggestions.

    ## Input Variables

    - task: Research task with hypothesis and goals for context.
    - code: The ablation experiment code that was executed.
    - stdout: Standard output from running the experiment code.
    - stderr: Error output from running the experiment code.

    ## Analysis Requirements

    Provide structured analysis covering:

    1. **Execution Status**: Success or failure with specific errors
    2. **Implementation Quality**:
       - Coding errors (syntax, runtime, exceptions)
       - Logic flaws (component not properly removed/modified)
       - Design issues (ablation doesn't test intended component)
    3. **Ablation Validity**:
       - Was target component correctly ablated?
       - Does ablated version still function properly?
       - Fair comparison to baseline maintained?
    4. **Output Assessment**:
       - Do metrics show component impact clearly?
       - Are performance changes interpretable?
       - Multiple datasets evaluated correctly?
    5. **Scientific Interpretation**:
       - Does ablation reveal component importance?
       - Results align with expected behavior?
       - Unexpected findings explained?
    6. **Suggestions**: Improvements for ablation study or additional ablations

    ## Research idea

    <RESEARCH_IDEA>
    {_task_to_prompt(task)}
    </RESEARCH_IDEA>

    ## Implementation

    <IMPLEMENTATION>
    ```python
    {code}
    ```
    </IMPLEMENTATION>

    ## Stdout

    <STDOUT>
    ```
    {stdout}
    ```
    </STDOUT>

    ## Stderr

    <STDERR>
    ```
    {stderr}
    ```
    </STDERR>
    """


def build_prompt_ablation_parser_code(
    code: str,
    memory: str = "",
    baseline_results: str = "",
) -> str:
    return f"""
    ## Introduction
    
    You are an AI researcher analyzing experimental results stored in a JSON
    file. Write code to load and analyze the metrics from
    `data_ablation.json` generated by an ablation study experiment.
    
    ## Input Variables

    - code: Original ablation experiment code to understand data structure.
    - memory: Historical notes from previous parser attempts.
    - baseline_results: Baseline metrics to compare ablation results against.
    
    ## Context
    
    Original Ablation Code:
    
    ```python
    {code}
    ```
    
    ## Instructions
    
    1. Load the `data_ablation.json` file, which is located in the current
       directory
    2. Extract metrics for the ablation run and dataset. Refer to the original
       code to understand the data structure.
    3. Always print the name of the ablation type and dataset before printing
       the metrics
    4. Always print the name of the metric before printing the value with
       precise labels (e.g., 'train accuracy', 'validation loss', 'test F1
       score').
    5. Only print the best or final value for each metric for each dataset
    6. IMPORTANT: After printing ablation results, compare with baseline 
       results to show component impact (improvement/degradation percentages)
    7. DO NOT CREATE ANY PLOTS
    
    Important code structure requirements:

    - Do NOT put any execution code inside `if __name__ == "__main__":`
    - All code should be at the global scope or in functions that are called
      from the global scope
    - The script should execute immediately when run, without requiring any
      special entry point
    
    ## Example data loading code
    
    ```python
    import json
    import os
    with open(os.path.join(os.getcwd(), 'data_ablation.json')) as f:
        experiment_data = json.load(f)
    ```
    
    ## Response format
    
    Your response should use structured json outputs in the following format:

    - plan: A brief outline/sketch of your proposed solution in natural language
      (7-10 sentences)
    - code: A python script in plain python. DO NOT USE FENCES. EG:
      \\`\\`\\`python ... \\`\\`\\`
    - dependencies: A list of dependencies required for the code to run. EG:
      ["torch", "torchvision", "numpy", "pandas", "scikit-learn"]. NEVER
      include Python standard library dependencies (e.g., json, os, sys, pathlib).
      ALWAYS only include third-party packages.

    ## Baseline Results (for comparison)

    <BASELINE_RESULTS>
    {baseline_results or "NA"}
    </BASELINE_RESULTS>

    Compare ablation results against these baseline metrics to quantify 
    component importance and contribution.

    ## Memory

    <MEMORY>
    {memory or "NA"}
    </MEMORY>
    """


def build_prompt_ablation_parser_output(
    code: str, stdout: str, stderr: str, original_code: str = ""
) -> str:
    return f"""
    ## Introduction

    You are an experienced AI researcher. You have written code to parse and
    analyze ablation study results. Evaluate parsing quality, component impact
    quantification, and baseline comparison validity.

    ## Input Variables

    - code: Parser code that was executed to analyze results.
    - stdout: Standard output from running the parser code.
    - stderr: Error output from running the parser code.
    - original_code: Original ablation experiment code for reference.

    ## Analysis Requirements

    Provide structured analysis covering:

    1. **Parsing Success**: All ablation metrics extracted correctly?
    2. **Data Consistency**:
       - Do extracted values match ablation output?
       - All ablation types and datasets represented?
       - Baseline comparison data included?
    3. **Component Impact Analysis**:
       - Is component contribution clearly quantified?
       - Performance degradation/improvement calculated correctly?
       - Percentage changes meaningful and accurate?
    4. **Result Interpretation**:
       - Do ablation results make scientific sense?
       - Component importance correctly assessed?
       - Unexpected impacts explained?
    5. **Completeness Check**:
       - All ablation variations reported?
       - Dataset-specific impacts shown?
       - Missing comparisons or analysis?
    6. **Suggestions**: Better impact presentation or additional ablation analysis

    ## Original Experiment Code

    <ORIGINAL_CODE>
    ```python
    {original_code or "NA"}
    ```
    </ORIGINAL_CODE>

    ## Parser Implementation

    <PARSER_IMPLEMENTATION>
    ```python
    {code}
    ```
    </PARSER_IMPLEMENTATION>

    ## Stdout

    <STDOUT>
    ```
    {stdout}
    ```
    </STDOUT>

    ## Stderr

    <STDERR>
    ```
    {stderr}
    ```
    </STDERR>
    """
