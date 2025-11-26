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

    ## Input Variables

    - task: Research task with hypothesis and goals for context.
    - metrics: Evaluation metrics being tracked across experiments.
    - code: Experiment code that was executed.
    - stdout: Standard output from running the experiment.
    - stderr: Error output from running the experiment.
    - existing_summary: Cumulative summary of all previous experiments.
    - parsed_summary: Summary from parser analyzing the execution output.

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
    3. Assess implementation quality: Does code properly test hypothesis?
    4. Evaluate scientific validity: Do results make sense? Any anomalies?
    5. Note if results support or contradict research hypothesis.
    6. Write a concise update (max 7 sentences) summarizing:
       - Execution status (success/failure)
       - Key metric values (be quantitative)
       - Implementation quality issues if any
       - Whether results align with hypothesis
       - Suggestions for next experiments
    7. Do NOT rewrite the entire summary. Just provide the text to APPEND to the
       existing summary.

    ## Response

    Provide ONLY the new summary text to append. Do not include the previous
    summary in your response.
    """

