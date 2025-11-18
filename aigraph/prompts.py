

from aigraph.utils import ROOT_DIR, Task


def build_task_prompt(task: Task) -> str:
    prompt = f"""
    You are an ambitious AI researcher who is looking to publish a paper that
    will contribute significantly to the field.
    
    You have an idea and you want to conduct creative experiments to gain
    scientific insights.
    
    Your aim is to run experiments to gather sufficient results for a top
    conference paper.

    Your research idea:

    Title:
    {task.title}

    Abstract:
    {task.abstract}

    Hypothesis:
    {task.short_hypothesis}

    """

    if task.code:
        code = f'```python\n{task.code}\n```'
        return prompt + f"Code To Use:\n{code}\n"

    example = ROOT_DIR / "example.py"
    if not example.exists():
        return prompt

    code = example.read_text()
    code = f'```python\n{code}\n```'
    return prompt + f"Code To Use:\n{code}\n"



def build_prompt_metrics(task: Task) -> str:
    return f"""
    ## Introduction
    
    You are an AI researcher setting up experiments. Please propose meaningful
    evaluation metrics that will help analyze the performance and
    characteristics of solutions for this research task.

    ## Research idea

    {build_task_prompt(task)}
    
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
