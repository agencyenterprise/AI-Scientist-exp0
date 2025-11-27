import logging
import operator as op
from pathlib import Path
from typing import Annotated, Any, TypedDict

from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph
from langgraph.runtime import Runtime
from langgraph.types import Checkpointer, Send
from pydantic import BaseModel

from aigraph.agents import experiment, ideas, writer

logger = logging.getLogger(__name__)

# Prompts
PROMPT_IDEAS_GENERATE = "Generate some ideas for the task."

PROMPT_IDEAS_NOVELTY = "Make the ideas as novel as possible."

PROMPT_INITIAL_EXPERIMENT = """
Research idea:

<title>
{title}
</title>

Description:

<description>
{description}
</description>

Research:

<research>
{research}
</research>

Analysis:

<analysis>
{analysis}
</analysis>
"""

PROMT_WRITER_WRITE = """
You are an ambitious AI researcher who is looking to publish a paper that will
contribute significantly to the field. Ensure that the paper is scientifically
accurate, objective, and truthful. Accurately report the experimental results,
even if they are negative or inconclusive.

## Input Variables

- task: Research task with hypothesis and goals for the paper.
- pages: Page limit for the main paper content.

You are planning to submit to a top-tier ML conference, which has guidelines:

- The main paper is limited to {pages} pages, including all figures and tables,
  but excluding references, the impact statement, and optional appendices. In
  general, try to use the available space and include all relevant information.
- Do not change the overall style which is mandated by the conference. Keep to
  the current method of including the references.bib file.
- Do not remove the \\graphicspath directive or no figures will be found.

Here are some tips for each section of the paper:

## Paper

### Title

- Title should be catchy and informative. It should give a good idea of what the
  paper is about.
- Try to keep it under 2 lines.

### Abstract

- TL;DR of the paper.
- What are we trying to do and why is it relevant?
- Make sure the abstract reads smoothly and is well-motivated. This should be
  one continuous paragraph.

### Introduction

- Longer version of the Abstract, i.e., an overview of the entire paper.
- Provide context to the study and explain its relevance.
- If results are inconclusive or negative, present them frankly; if they are
  positive, you may highlight how the approach effectively addresses the
  research question or problem.
- Summarize your contributions, highlighting pertinent findings, insights, or
  proposed methods.

### Related Work

- Academic siblings of our work, i.e., alternative attempts in literature at
  trying to address the same or similar problems.
- Compare and contrast their approach with yours, noting key differences or
  similarities.
- Ensure proper citations are provided.

### Background

- Present foundational concepts or prior work needed to understand your method.
- This should include necessary definitions, the problem setting, or relevant
  theoretical constructs.

### Method

- Clearly detail what you propose to do and why. If your study aims to address
  certain hypotheses, describe them and how your method is constructed to test
  them.
- If results are negative or inconclusive, you may suggest improvements or
  discuss possible causes.

### Experimental Setup

- Explain how you tested your method or hypothesis.
- Describe necessary details such as data, environment, and baselines, but omit
  hardware details unless explicitly mentioned.

### Experiments

- Present the results truthfully according to the data you have. If outcomes are
  not as expected, discuss it transparently.
- Include comparisons to baselines if available, and only include analyses
  supported by genuine data.
- Try to include all relevant plots and tables. Consider combining multiple
  plots into one figure if they are related.

### Conclusion

- Summarize the entire paper, including key strengths or findings.
- If results are strong, highlight how they might address the research problem.
- If results are negative or inconclusive, highlight potential improvements or
  reasons and propose future directions.

### Appendix

- Place for supplementary material that did not fit in the main paper.

## Output

When returning final code, return ONLY the raw LaTeX code without fenced
code blocks or triple backticks.

## Research idea

<RESEARCH_IDEA>
{research_idea}
</RESEARCH_IDEA>

## Latex template

Update the following LaTeX template to reflect the research idea:

<TEMPLATE>
{template}
</TEMPLATE>
"""

PROMPT_WRITER_REVIEW = "Review the research report for clarity, accuracy, and completeness. Ensure it accurately reflects the experiment and results."


class State(BaseModel):
    # inputs
    cwd: Path
    task: Path

    # state
    state_ideas: ideas.State | None = None
    states_experiment: Annotated[list[experiment.State], op.add] = []
    states_writer: Annotated[list[writer.State], op.add] = []


class Context(BaseModel):
    model: str = "gpt-4o-mini"
    temperature: float = 0.0
    max_attempts: int = 5


async def node_ideas(state: State, runtime: Runtime[Context]) -> list[Send]:
    logger.info("Starting node_ideas")

    ideas_context = ideas.Context(
        model=runtime.context.model,
        temperature=runtime.context.temperature,
        max_attempts=runtime.context.max_attempts,
        num_ideas=3,
    )

    ideas_state = ideas.State(
        research_domain=state.task.read_text(),
        prompt_generate=PROMPT_IDEAS_GENERATE,
        prompt_novelty=PROMPT_IDEAS_NOVELTY,
    )

    graph = ideas.build(checkpointer=True)
    result = await graph.ainvoke(ideas_state, context=ideas_context)
    result = ideas.State.model_validate(result)
    logger.info(f"Generated {len(result.ideas)} ideas")

    items = zip(result.ideas, result.researches, result.analyses)

    sends: list[Send] = []
    for i, (idea, research, analysis) in enumerate(items):
        sends.append(
            Send(
                "node_experiment",
                {
                    "idea": idea,
                    "research": research,
                    "analysis": analysis,
                    "cwd": state.cwd / f"experiment_{i:02d}",
                },
            )
        )

    logger.info("Finished node_ideas")
    return sends


class InternalState(TypedDict, total=False):
    cwd: Path
    idea: ideas.Idea
    research: ideas.AgentState
    analysis: ideas.Analysis
    experiment: experiment.State


async def node_experiment(
    state: InternalState,
    runtime: Runtime[Context],
) -> dict[str, Any]:
    logger.info("Starting node_experiment: %s", state.get("cwd"))

    cwd = state.get("cwd")
    idea = state.get("idea")
    research = state.get("research")
    analysis = state.get("analysis")

    assert cwd is not None, "CWD is required"
    assert idea is not None, "Idea is required"
    assert research is not None, "Research is required"
    assert analysis is not None, "Analysis is required"

    cwd.mkdir(parents=True, exist_ok=True)

    experiment_context = experiment.Context(
        model=runtime.context.model,
        temperature=runtime.context.temperature,
        max_attempts=runtime.context.max_attempts,
    )

    experiment_state = experiment.State(
        cwd=cwd,
        prompt=PROMPT_INITIAL_EXPERIMENT.format(
            title=idea.title,
            description=idea.description,
            research=research["final_report"],
            analysis=analysis.rationale,
        ),
    )

    graph = experiment.build(checkpointer=True)
    result = await graph.ainvoke(experiment_state, context=experiment_context)
    result = experiment.State.model_validate(result)

    logger.info("Finished node_experiment: %s", cwd)
    return {"experiment": result}


async def node_writer(
    state: InternalState, runtime: Runtime[Context]
) -> dict[str, Any]:
    logger.info("Starting node_writer")

    idea = state.get("idea")
    exps = state.get("experiment")

    assert idea is not None, "Idea is required"
    assert exps is not None, "Experiments are required"

    writer_state = writer.State(
        prompt_write=PROMT_WRITER_WRITE.format(
            research_idea=idea.description,
        ),
        prompt_review=PROMPT_WRITER_REVIEW,
    )

    writer_context = writer.Context(
        model=runtime.context.model,
        temperature=runtime.context.temperature,
    )

    graph = writer.build(checkpointer=True)
    result = await graph.ainvoke(writer_state, context=writer_context)
    result = writer.State.model_validate(result)

    logger.info("Finished node_writer")
    return {"writer": result}


def build(
    checkpointer: Checkpointer = None,
) -> CompiledStateGraph[State, Context, State, State]:
    """Build the pipeline graph with iterative experiment replanning"""
    builder = StateGraph(state_schema=State, context_schema=Context)

    builder.add_node("node_ideas", node_ideas)
    builder.add_node("node_experiment", node_experiment)
    builder.add_node("node_writer", node_writer)

    builder.add_conditional_edges(
        START,
        node_ideas,
        ["node_experiment"],
    )
    builder.add_edge("node_experiment", "node_writer")
    builder.add_edge("node_writer", END)

    return builder.compile(name="graph_pipeline", checkpointer=checkpointer)  # type: ignore
