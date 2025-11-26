import json
import logging
from typing import Iterable

from aigraph import utils
from aigraph.agents.research_prompts import _task_to_prompt

logger = logging.getLogger(__name__)


def build_prompt_summary(
    task: utils.Task,
    metrics: Iterable[utils.Metric],
    code: str,
    stdout: str,
    stderr: str,
    existing_summary: str,
    parsed_summary: str = "",
) -> str:
    return f"""
    ## Introduction

    You are an AI researcher monitoring a series of experiments. Your goal is to
    maintain a cumulative summary of the progress, focusing on the key evaluation
    metrics defined for this research.

    ## Research Idea

    {_task_to_prompt(task)}

    ## Evaluation Metrics

    <METRICS>
    {json.dumps([m.model_dump(mode="json") for m in metrics], indent=2)}
    </METRICS>

    ## Current Experiment Implementation

    <CODE>
    ```python
    {code}
    ```
    </CODE>

    ## Execution Output

    <STDOUT>
    {stdout}
    </STDOUT>

    <STDERR>
    {stderr}
    </STDERR>

    ## Parsed Output Summary

    The execution output was parsed by another agent. Here is their summary of
    what happened (e.g. bugs found, successful execution):

    <PARSED_SUMMARY>
    {parsed_summary or "NA"}
    </PARSED_SUMMARY>

    ## Existing Summary

    <PREVIOUS_SUMMARY>
    {existing_summary or "No previous experiments run."}
    </PREVIOUS_SUMMARY>

    ## Instructions

    1. Analyze the output of the current experiment, paying special attention to
       the values of the defined metrics.
    2. Determine if the experiment was successful (ran to completion) and what
       the results were.
    3. Write a concise update (max 5 sentences) summarizing the results of THIS
       experiment.
    4. Do NOT rewrite the entire summary. Just provide the text to APPEND to the
       existing summary.
    5. If the experiment failed (bugs, errors), briefly mention the failure mode.
    6. Be quantitative when possible (e.g., "Accuracy improved to 85%").

    ## Response

    Provide ONLY the new summary text to append. Do not include the previous
    summary in your response.
    """

