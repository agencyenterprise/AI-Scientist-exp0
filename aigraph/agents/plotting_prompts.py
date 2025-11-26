from aigraph.utils import Task


def _task_to_prompt(task: Task) -> str:
    return f"""
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


def build_prompt_plotting_code(
    task: Task, code: str, memory: str = "", baseline_code: str = ""
) -> str:
    return f"""
    ## Introduction

    You are an AI researcher. You have run an experiment and generated results
    in `data_ablation.json`. Your task is to write a Python script to
    visualize these results using matplotlib or seaborn.

    ## Input Variables

    - task: Research task with hypothesis and goals for context.
    - code: Experiment code that generated the data to plot.
    - memory: Historical notes from previous plotting attempts.

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
      ["matplotlib", "seaborn", "numpy", "pandas"]. NEVER include Python
      standard library dependencies (e.g., json, os, sys, pathlib). ALWAYS only
      include third-party packages.

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
    {_task_to_prompt(task)}
    </RESEARCH_IDEA>

    ## Reference: Original Baseline Implementation
    
    This is the original baseline code for reference. Use it to understand the 
    data structure and visualization context:
    
    <BASELINE_CODE>
    ```python
    {baseline_code or "Not available"}
    ```
    </BASELINE_CODE>

    ## Experiment Code

    This is the current code that generated the data to visualize:
    
    <CODE>
    ```python
    {code}
    ```
    </CODE>

    ## Memory (Previous Attempts)

    <MEMORY>
    {memory or "NA"}
    </MEMORY>
    """


def build_prompt_plotting_output(
    task: Task, code: str, stdout: str, stderr: str
) -> str:
    return f"""
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


def build_prompt_analyze_plots(task: Task) -> str:
    return f"""
    ## Introduction

    You are an AI researcher. You have generated plots from your experiment
    results. Your task is to analyze these plots to interpret the scientific
    findings.

    ## Input Variables

    - task: Research task with hypothesis and goals for context.

    ## Research idea

    <RESEARCH_IDEA>
    {_task_to_prompt(task)}
    </RESEARCH_IDEA>

    ## Instructions

    - Analyze the provided plot images.
    - Describe the trends you observe (e.g., convergence, overfitting,
      performance comparison).
    - Relate the findings back to the hypothesis.
    - Conclude if the hypothesis is supported or rejected.
    - Provide a relevancy score (integer 0-10) indicating how important this
      plot is for the final paper. 0 means irrelevant, 10 means critical.
    """
