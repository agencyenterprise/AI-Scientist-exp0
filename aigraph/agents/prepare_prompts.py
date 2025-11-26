from aigraph.agents.research_prompts import _task_to_prompt
from aigraph.utils import Task


def build_prompt_prepare_research(task: Task, experiment_plan: str = "") -> str:
    return f"""
      ## Task

      <TASK>
      {_task_to_prompt(task)}
      </TASK>

      ## Experiment Plan

      <EXPERIMENT_PLAN>
      {experiment_plan or "No plan available."}
      </EXPERIMENT_PLAN>

      Focus your research on topics, techniques, and related work that are most 
      relevant to the experimental approach outlined in the plan above.
      """


def build_prompt_prepare_metrics(task: Task, research: str = "") -> str:
    return f"""
    ## Introduction

    You are an AI researcher setting up experiments. Please propose meaningful
    evaluation metrics that will help analyze the performance and
    characteristics of solutions for this research task.

    ## Input Variables

    - task: Research task containing hypothesis, abstract, and experimental goals.
    - research: Deep research findings on related work and state-of-the-art.

    ## Research idea

    {_task_to_prompt(task)}

    ## Research Context

    <RESEARCH_CONTEXT>
    {research or "No research context available yet."}
    </RESEARCH_CONTEXT>

    ## Goals

    - Focus on getting basic working implementation
    - Use a dataset appropriate to the experiment
    - Aim for basic functional correctness
    - If you are given "Code To Use", you can directly use it as a starting
      point.

    ## Instructions

    Propose up to 3 evaluation metrics that would be useful for analyzing the
    performance of solutions for this research task.

    Note: Validation loss will be tracked separately so you don't need to
    include it in your response.

    Format your response as a list containing:

      - name: The name of the metric
      - maximize: Whether higher values are better (true/false)
      - description: A brief explanation of what the metric measures. Your list
        should contain at most 3 metrics.
    """


def build_prompt_prepare_plan(task: Task) -> str:
    """Prompt for creating initial structured experiment plan."""
    return f"""
    ## Introduction

    You are an AI researcher creating an initial structured experiment plan. 
    Transform the research task into a detailed, actionable experiment plan 
    that will guide implementation.

    ## Input Variables

    - task: Research task with hypothesis and experimental goals.

    ## Research idea

    {_task_to_prompt(task)}

    ## Instructions

    Create a structured experiment plan covering:

    1. **Research Objective**: Clear statement of what hypothesis is tested
    2. **Experimental Design**:
       - Approach overview
       - Key components/modules needed
       - Data flow architecture
    3. **Implementation Strategy**:
       - Dataset selection rationale (3+ datasets required)
       - Model architecture requirements
       - Training/evaluation procedure
    4. **Evaluation Considerations**:
       - What types of metrics would be appropriate
       - When/where to collect measurements
       - Expected value ranges
    5. **Expected Outputs**:
       - Data structure format
       - Key results to track
       - Validation checkpoints

    Format as clear, detailed plan (10-15 sentences). Be specific about
    technical choices and justify decisions relative to research hypothesis.
    """
