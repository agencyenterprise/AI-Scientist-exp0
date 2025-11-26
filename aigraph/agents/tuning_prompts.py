import json
from typing import Iterable

from aigraph.utils import Metric, Task


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


def build_prompt_tuning_propose(code: str, hyperparams: list[str]) -> str:
    attempted = hyperparams or ["Nothing has been tried yet."]

    return f"""
    You are an AI researcher conducting hyperparameter tuning for baseline
    experiments. Based on the current implementation and previous hyperparameter
    tuning attempts (if any), propose ONE new hyperparameter tuning idea to see
    if it improves the performance.
    
    You should first check if simply training longer (more epochs) improves the
    performance. Then try tuning common hyperparameters such as learning rate,
    batch size, etc. Only propose algorithm-specific and/or model-specific
    hyperparameters after you have tried the above.
    
    ## Input Variables

    - code: The baseline implementation code to tune hyperparameters for.
    - hyperparams: List of previously attempted hyperparameter tuning studies.
    
    ## Code
    
    <CODE>
    ```python
    {code}
    ```
    </CODE>

    ## Previous Hyperparam Tuning Attempts
    
    <PREVIOUS_HYPERPARAM_TUNING_ATTEMPTS>
    {"\n".join(f"- {i}" for i in attempted)}
    </PREVIOUS_HYPERPARAM_TUNING_ATTEMPTS>
    
    ## Requirements
    
    1. Identify ONE specific hyperparameter to tune
    2. Ensure the hyperparameter is different from previous attempts

    ## Response format
    
    - Your response should start with 'HYPERPARAM NAME: <hyperparam name>' on
      the first line to represent the name of the hyperparameter.
    - The second line should start with 'DESCRIPTION: <description>', a brief
      description of what hyperparameter is being tuned and why (3-5 sentences).
    """


def build_prompt_tuning_code(
    task: Task,
    metrics: Iterable[Metric],
    name: str,
    description: str,
    code: str,
    memory: str,
    cumulative_summary: str = "",
    baseline_results: str = "",
    experiment_plan: str = "",
) -> str:
    return f"""
    ## Introduction

    You are an experienced AI researcher. You are provided with a previously
    developed baseline implementation. Your task is to implement hyperparameter
    tuning for the following idea:
    
    ## Input Variables

    - task: Research task with hypothesis and goals to implement.
    - metrics: Evaluation metrics to track during tuning experiments.
    - name: Name of the specific hyperparameter being tuned.
    - description: Detailed description of the hyperparameter tuning approach.
    - code: Baseline implementation code to modify for tuning.
    - memory: Historical notes from previous attempts to avoid repeating mistakes.
    - cumulative_summary: Summary of all experiments run so far for context.
    - baseline_results: Baseline performance metrics to compare improvements against.
    - experiment_plan: Structured experiment plan defining objectives and approach.
    
    Name: {name}
    Description: {description}

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

    ### Hyperparameter tuning guidelines

    - Implement the hyperparameter tuning idea described above.
    - The code should be a single-file python program that is self-contained and
      can be executed as-is.
    - No parts of the code should be skipped, don't terminate the code execution
      before finishing the script.
    - You MUST evaluate your solution on at least 3 different datasets to ensure
      robustness. Use standard benchmark datasets when available:
      
      **Vision**: MNIST, Fashion-MNIST, CIFAR-10, CIFAR-100, ImageNet, SVHN
      **NLP**: GLUE, SQuAD, IMDb, AG News, SST-2, MRPC
      **Tabular**: Iris, Wine Quality, Titanic, Diabetes, Breast Cancer
      **Audio**: LibriSpeech, Speech Commands
      
      Each dataset should be evaluated separately and results tracked per dataset 
      in the experiment_data structure.

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

    CRITICAL: Your experiment_data dictionary MUST ALWAYS include these four required keys for each dataset:
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
    5. Save ALL metrics at the end. You must use the filename `data_tuning.json`:
       ```python
       with open(os.path.join(os.getcwd(), 'data_tuning.json'), 'w') as f:
           json.dump(experiment_data, f)
       ```

    YOUR CODE MUST SAVE THE DATA IN THE `data_tuning.json` FILE.

    ## Research idea

    <RESEARCH_IDEA>
    {_task_to_prompt(task)}
    </RESEARCH_IDEA>

    ## Structured Experiment Plan

    <EXPERIMENT_PLAN>
    {experiment_plan or "No structured plan available."}
    </EXPERIMENT_PLAN>

    ## Evaluation metrics

    <EVALUATION METRICS>
    ```json
    {json.dumps([i.model_dump(mode="json") for i in metrics], indent=2)}
    ```
    </EVALUATION METRICS>

    ## Original Code
    
    ```python
    {code}
    ```

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

    Your goal is to tune hyperparameters to improve upon these baseline metrics.
    """


def build_prompt_tuning_code_output(
    task: Task, code: str, stdout: str, stderr: str
) -> str:
    return f"""
    ## Introduction
    
    You are an experienced AI researcher. You have written code for your
    hyperparameter tuning experiment. Provide comprehensive analysis of
    implementation quality, tuning effectiveness, and actionable suggestions.

    ## Input Variables

    - task: Research task with hypothesis and goals for context.
    - code: The tuning experiment code that was executed.
    - stdout: Standard output from running the experiment code.
    - stderr: Error output from running the experiment code.

    ## Analysis Requirements

    Provide structured analysis covering:

    1. **Execution Status**: Success or failure with specific errors
    2. **Implementation Quality**:
       - Coding errors (syntax, runtime, exceptions)
       - Logic flaws (incorrect hyperparameter application)
       - Design issues (tuning strategy doesn't match goals)
    3. **Tuning Validity**:
       - Are hyperparameter changes correctly implemented?
       - Do metrics show impact of tuning?
       - Are results compared to baseline?
    4. **Output Assessment**:
       - Do loss curves show proper convergence?
       - Are metric improvements/degradations reasonable?
       - Multiple datasets evaluated correctly?
    5. **Experimental Soundness**:
       - Sufficient tuning exploration?
       - Fair comparison conditions maintained?
       - All metrics tracked properly?
    6. **Suggestions**: Improvements for hyperparameter tuning strategy

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


def build_prompt_tuning_parser_code(
    code: str,
    memory: str = "",
    baseline_results: str = "",
    experiment_plan: str = "",
) -> str:
    return f"""
    ## Introduction

    You are an AI researcher analyzing experimental results stored in a JSON
    file. Write code to load and analyze the metrics from a file named
    'data_tuning.json'. It has the following structure:

    ## Input Variables

    - code: Original tuning experiment code to understand data structure.
    - memory: Historical notes from previous parser attempts.
    - baseline_results: Baseline metrics to compare tuning improvements against.
    - experiment_plan: Structured experiment plan for context on expected outputs.

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

    - Load the `data_tuning.json` file, which is located in the current
      directory
    - Extract metrics for each dataset. Refer to the original code to understand
      the data structure.
    - Always print the name of the dataset before printing the metrics
    - Always print the name of the metric before printing the value with precise
      labels (e.g., 'train accuracy', 'validation loss', 'test F1 score').
    - Only print the best or final value for each metric for each dataset
    - IMPORTANT: After printing tuning results, compare with baseline results
      and print improvement/degradation percentages
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
    with open(os.path.join(os.getcwd(), 'data_tuning.json')) as f:
        experiment_data = json.load(f)
    ```

    ## Structured Experiment Plan

    <EXPERIMENT_PLAN>
    {experiment_plan or "No structured plan available."}
    </EXPERIMENT_PLAN>

    ## Context

    Here is the original code that was used to generate the `data_tuning.json`
    file:

    <ORIGINAL_CODE>
    ```python
    {code}
    ```
    </ORIGINAL_CODE>

    ## Baseline Results (for comparison)

    <BASELINE_RESULTS>
    {baseline_results or "NA"}
    </BASELINE_RESULTS>

    Compare tuning results against these baseline metrics to show improvements.

    ## Memory

    <MEMORY>
    {memory or "NA"}
    </MEMORY>
    """


def build_prompt_tuning_parser_output(
    code: str, stdout: str, stderr: str, original_code: str = ""
) -> str:
    return f"""
    ## Introduction

    You are an experienced AI researcher. You have written code to parse and
    analyze hyperparameter tuning results. Evaluate parsing quality, baseline
    comparison validity, and improvement interpretation.

    ## Input Variables

    - code: Parser code that was executed to analyze results.
    - stdout: Standard output from running the parser code.
    - stderr: Error output from running the parser code.
    - original_code: Original tuning experiment code for reference.

    ## Analysis Requirements

    Provide structured analysis covering:

    1. **Parsing Success**: All tuning metrics extracted correctly?
    2. **Data Consistency**:
       - Do extracted values match experiment output?
       - All datasets included in comparison?
       - Baseline vs tuned results clearly separated?
    3. **Comparison Validity**:
       - Are improvements/degradations calculated correctly?
       - Percentage changes meaningful?
       - Fair comparison (same conditions)?
    4. **Result Interpretation**:
       - Do tuning outcomes make scientific sense?
       - Are improvements statistically meaningful?
       - Unexpected results explained?
    5. **Completeness Check**:
       - All hyperparameter impacts reported?
       - Dataset-specific comparisons shown?
       - Missing analysis or metrics?
    6. **Suggestions**: Better comparison presentation or additional analysis

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
