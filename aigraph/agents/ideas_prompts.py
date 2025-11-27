from aigraph.agents.research_prompts import _task_to_prompt
from aigraph.utils import Task


def build_prompt_generate_ideas(task: Task, num_ideas: int) -> str:
    return f"""
    ## Introduction

    You are an AI researcher tasked with generating creative and impactful
    research ideas.

    ## Task Description

    {_task_to_prompt(task)}

    ## Instructions

    Generate {num_ideas} research ideas based on the task description above.
    Each idea should be:

    - Novel and interesting
    - Feasible to implement and test
    - Scientifically rigorous
    - Suitable for publication at a top conference

    For each idea, provide:

    - Name: A short, descriptive name for the research idea
    - Title: A full research paper title
    - Abstract: A comprehensive abstract (2-3 paragraphs)
    - Short Hypothesis: A clear, testable hypothesis
    - Related Work: A brief overview of relevant prior work
    - Experiments: A list of specific experiments to conduct (3-5 items)
    - Risk Factors and Limitations: Potential issues or limitations (2-4 items)
    - Code: Optional starting code if applicable (can be null)

    Format your response as a list of research ideas, each following the Task
    schema structure.
    """
