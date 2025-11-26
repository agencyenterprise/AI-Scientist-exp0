import json
from typing import Iterable

from aigraph.agents.research_prompts import _task_to_prompt
from aigraph.utils import Metric, Task


def build_prompt_baseline_metrics(task: Task) -> str:
    return f"""
    ## Introduction

    You are an AI researcher setting up experiments. Please propose meaningful
    evaluation metrics that will help analyze the performance and
    characteristics of solutions for this research task.

    ## Input Variables

    - task: Research task containing hypothesis, abstract, and experimental goals.

    ## Research idea

    {_task_to_prompt(task)}

    ## Goals

    - Focus on getting basic working implementation
    - Use a dataset appropriate to the experiment
    - Aim for basic functional correctness
    - If you are given "Code To Use", you can directly use it as a starting
      point.

    ## Instructions

    Propose a single evaluation metric that would be useful for analyzing the
    performance of solutions for this research task.

    Note: Validation loss will be tracked separately so you don't need to
    include it in your response.

    Format your response as a list containing:

      - name: The name of the metric
      - maximize: Whether higher values are better (true/false)
      - description: A brief explanation of what the metric measures. Your list
        should contain only one metric.
    """


def build_prompt_baseline_code(
    task: Task, metrics: Iterable[Metric], memory: str, cumulative_summary: str = ""
) -> str:
    prompt = f"""
    ## Introduction

    You are an AI researcher who is looking to publish a paper that will
    contribute significantly to the field. Your first task is to write a python
    script that implements a solid baseline based on the research idea provided
    below. From data preparation to model training. Focus on getting a simple
    but working implementation first, before any sophisticated improvements. We
    will explore more advanced variations in later stages.

    ## Input Variables

    - task: Research task with hypothesis and goals to implement.
    - metrics: Evaluation metrics to track during baseline training.
    - memory: Historical notes from previous attempts to avoid repeating mistakes.
    - cumulative_summary: Summary of all experiments run so far for context.

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

    ### Baseline experiment guidelines

    - This first experiment design should be relatively simple, without
      extensive hyper-parameter optimization.
    - Take the Memory section into consideration when proposing the design.
    - Don't suggest to do EDA.
    - Prioritize using real public datasets (e.g., from HuggingFace) when they
      suit the task, and only fall back to synthetic data if no suitable dataset
      is available or synthetic generation is essential to the proposed
      experiment.
    - You MUST evaluate your solution on at least 3 different datasets to ensure
      robustness. Use standard benchmark datasets when available (e.g., MNIST,
      CIFAR-10, ImageNet, GLUE, SQuAD, etc.). Each dataset should be evaluated
      separately and results should be tracked per dataset in the experiment_data
      structure.

    ## Implementation guidelines

    ### CRITICAL GPU REQUIREMENTS

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

    ### CRITICAL MODEL INPUT GUIDELINES

    - Always pay extra attention to the input to the model being properly
      normalized
    - This is extremely important because the input to the model's forward pass
      directly affects the output, and the loss function is computed based on
      the output

    For generative modeling tasks, you must:

    - Generate a set of samples from your model
    - Compare these samples with ground truth data using appropriate
      visualizations

    ### CODING GUIDELINES

    - Do NOT put any execution code inside 'if __name__ == "__main__":' block
    - All code should be at the global scope or in functions that are called
      from the global scope
    - The script should execute immediately when run, without requiring any
      special entry point or args. Should be executable py running `python
      script.py`.
    - Store any extra files and outputs in the current directory.
    - DO NOT CREATE ANY PLOTS! USING PLOTS IS NOT ALLOWED.

    Data saving requirements:

    Save all data (metrics, losses, predictions, etc.) as JSON following
    the following structure:

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

    YOU MUST APPEND THE DATA TO THE STRUCTURE ABOVE FOR EACH EPOCH. Like so 
    (update the code to your specific logic):

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
    3. Track and update ALL metrics passed below
    4. Update metrics at EACH epoch
    5. Save ALL metrics at the end. You must use the filename `data_baseline.json`:
       ```python
       with open(os.path.join(os.getcwd(), 'data_baseline.json'), 'w') as f:
           json.dump(experiment_data, f)
       ```

    YOUR CODE MUST SAVE THE DATA IN THE `data_baseline.json` FILE.

    ## Research idea

    <RESEARCH IDEA>
    {_task_to_prompt(task)}
    </RESEARCH IDEA>

    ## Evaluation metrics

    <EVALUATION METRICS>
    ```json
    {json.dumps([i.model_dump(mode="json") for i in metrics], indent=2)}
    ```
    </EVALUATION METRICS>

    ## Memory

    <MEMORY>
    {memory or "NA"}
    </MEMORY>

    ## Previous Experiment Summaries

    <PREVIOUS_SUMMARIES>
    {cumulative_summary or "No previous experiments have been run yet."}
    </PREVIOUS_SUMMARIES>
    """
    return prompt


def build_prompt_baseline_code_output(
    task: Task, code: str, stdout: str, stderr: str
) -> str:
    return f"""
    ## Introduction

    You are an experienced AI researcher. You have written code for your
    research experiment and now need to evaluate the output of the code
    execution. Provide comprehensive analysis of implementation quality,
    experimental validity, and actionable suggestions.

    ## Input Variables

    - task: Research task with hypothesis and goals for context.
    - code: The baseline experiment code that was executed.
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

    <RESEARCH IDEA>
    {_task_to_prompt(task)}
    </RESEARCH IDEA>

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


def build_prompt_baseline_parser_code(code: str, memory: str = "") -> str:
    return f"""
    ## Introduction

    You are an AI researcher analyzing experimental results stored in a JSON
    file. Write code to load and analyze the metrics from a file named
    'data_baseline.json'. It has the following structure:

    ## Input Variables

    - code: Original baseline experiment code to understand data structure.
    - memory: Historical notes from previous parser attempts.

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

    - Load the `data_baseline.json` file, which is located in the current
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
    with open(os.path.join(os.getcwd(), 'data_baseline.json')) as f:
        experiment_data = json.load(f)
    ```

    ## Context

    Here is the original code that was used to generate the `data_baseline.json`
    file:

    <ORIGINAL_CODE>
    ```python
    {code}
    ```
    </ORIGINAL_CODE>

    ## Memory

    <MEMORY>
    {memory or "NA"}
    </MEMORY>
    """


def build_prompt_baseline_parser_output(
    code: str, stdout: str, stderr: str, original_code: str = ""
) -> str:
    return f"""
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
