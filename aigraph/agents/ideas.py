import logging
import operator as op
from typing import Annotated, Any, TypedDict, cast

import open_deep_research.deep_researcher as researcher
from langchain.chat_models import BaseChatModel, init_chat_model
from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage
from langgraph.errors import GraphRecursionError
from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph
from langgraph.runtime import Runtime
from langgraph.types import Checkpointer, Send
from open_deep_research.state import AgentState
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class Analysis(BaseModel):
    novel: bool
    relevance: int
    rationale: str


class Idea(BaseModel):
    title: str
    plan: str
    description: str


class State(BaseModel):
    # inputs
    research_domain: str
    prompt_generate: str
    prompt_novelty: str

    # state
    ideas: Annotated[list[Idea], op.add] = []
    researches: Annotated[list[AgentState], op.add] = []
    analyses: Annotated[list[Analysis], op.add] = []

    # outputs
    idea: Idea | None = None
    research: AgentState | None = None
    analysis: Analysis | None = None


class Context(BaseModel):
    """Configurable context for idea generation"""

    model: str = "gpt-4o-mini"
    temperature: float = 0.7
    max_attempts: int = 5
    score_cutoff: int = 7
    num_ideas: int = 5

    @property
    def llm(self) -> BaseChatModel:
        return init_chat_model(model=self.model, temperature=self.temperature)


async def node_generate_ideas(state: State, runtime: Runtime[Context]) -> list[Send]:
    logger.info("Starting node_generate_idea")

    class Schema(BaseModel):
        ideas: Annotated[
            list[Idea],
            Field(
                description=f"List of ideas. Max of {runtime.context.num_ideas} ideas"
            ),
        ]

    if len(state.ideas) >= runtime.context.max_attempts:
        raise GraphRecursionError("Max attempts reached")

    messages: list[BaseMessage] = [
        SystemMessage(content=state.prompt_generate),
        HumanMessage(content=f"Research domain: {state.research_domain}"),
    ]

    llms = runtime.context.llm.with_structured_output(Schema)
    response: Schema = await llms.ainvoke(messages)  # type: ignore

    logger.debug(f"generated {len(response.ideas)} ideas")
    for i, idea in enumerate(response.ideas):
        logger.debug(f"idea[{i}]: {idea.title}")
        logger.debug(f"idea[{i}]: {idea.description[:32]!r}")
        logger.debug(f"idea[{i}]: {idea.plan[:32]!r}")

    sends = []
    for idea in response.ideas:
        sends.append(
            Send(
                "node_research",
                {
                    "idea": idea,
                    "prompt_novelty": state.prompt_novelty,
                },
            )
        )

    logger.info("Finished node_generate_ideas")
    return sends


class InteralState(TypedDict, total=False):
    # inputs
    idea: Idea
    prompt_novelty: str


async def do_research(prompt: str) -> AgentState:
    logger.info("Starting do_research")

    response = await researcher.deep_researcher.ainvoke(
        input={"messages": [HumanMessage(content=prompt)]},
        config={
            "configurable": {
                "allow_clarification": False,
                "max_researcher_iterations": 2,
            }
        },
    )

    logger.debug("Finished do_research")
    return cast(AgentState, response)


async def do_analysis(
    prompt_novelty: str,
    prompt: str,
    runtime: Runtime[Context],
) -> Analysis:
    logger.info("Starting do_analysis")

    llms = runtime.context.llm.with_structured_output(Analysis)
    response = await llms.ainvoke(
        [
            SystemMessage(content=prompt_novelty),
            HumanMessage(content=prompt),
        ]
    )

    logger.debug("Finished do_analysis")
    return cast(Analysis, response)


async def node_research(
    state: InteralState,
    runtime: Runtime[Context],
) -> dict[str, Any]:
    logger.info("Starting node_check_novelty")

    idea = state.get("idea")
    assert idea is not None, "Idea is required"

    prompt_novelty = state.get("prompt_novelty", "")

    # original prompt with idea
    prompt = ""
    prompt += "Research idea:\n\n"
    prompt += f"<title>\n{idea.title}\n</title>\n\n"
    prompt += "Description:\n\n"
    prompt += f"<description>\n{idea.description}\n</description>\n\n"
    prompt += "Plan:\n\n"
    prompt += f"<plan>\n{idea.plan}\n</plan>\n\n"

    res_research = await do_research(prompt)
    logger.debug(f"Research report: {res_research['final_report'][:32]!r}")

    prompt += "----------------------------------------\n\n"
    prompt += "Research report:\n\n"
    prompt += f"<report>\n{res_research['final_report']}\n</report>\n\n"

    res_analysis = await do_analysis(prompt_novelty, prompt, runtime)
    logger.debug(f"Analysis: {res_analysis.rationale[:32]!r}")

    logger.info("Finished node_check_novelty")
    return {
        "ideas": [idea],
        "researches": [res_research],
        "analyses": [res_analysis],
    }


async def node_select_best(state: State, runtime: Runtime[Context]) -> dict[str, Any]:
    logger.info("Starting node_select_best")
    assert state.researches is not None, "Research is required"
    assert state.analyses is not None, "Analysis is required"

    class Schema(BaseModel):
        idea: Idea

    items = zip(state.ideas, state.researches, state.analyses)

    prompt = ""
    for i, (idea, research, analysis) in enumerate(items):
        prompt += f"Idea {i}:\n\n"
        prompt += f"<title>\n{idea.title}\n</title>\n\n"
        prompt += f"<description>\n{idea.description}\n</description>\n\n"
        prompt += f"<plan>\n{idea.plan}\n</plan>\n\n"
        prompt += "----------------------------------------\n\n"
        prompt += f"Research {i}:\n\n"
        prompt += f"<summary>\n{research['final_report']}\n</summary>\n\n"
        prompt += "----------------------------------------\n\n"
        prompt += f"Analysis {i}:\n\n"
        prompt += f"<score>\n{analysis.novel}\n</score>\n\n"
        prompt += f"<relevance>\n{analysis.relevance}\n</relevance>\n\n"
        prompt += f"<rationale>\n{analysis.rationale}\n</rationale>\n\n"
        prompt += "========================================\n\n"

    messages: list[BaseMessage] = [
        SystemMessage("Select the best idea based on the research and analysis"),
        HumanMessage(content=prompt),
    ]

    llms = runtime.context.llm.with_structured_output(Schema)
    response = await llms.ainvoke(messages)
    response = cast(Schema, response)

    idea_i = state.ideas.index(response.idea)
    research = state.researches[idea_i]
    analysis = state.analyses[idea_i]

    logger.info("Finished node_select_best")
    return {"idea": response.idea, "research": research, "analysis": analysis}


def build(
    checkpointer: Checkpointer = None,
) -> CompiledStateGraph[State, Context, State, State]:
    """Build the idea generation graph"""
    builder = StateGraph(state_schema=State, context_schema=Context)

    builder.add_node(
        "node_research",
        node_research,
    )
    builder.add_node(
        "node_select_best",
        node_select_best,
    )

    builder.add_conditional_edges(
        START,
        node_generate_ideas,
        ["node_research"],
    )
    builder.add_edge(
        "node_research",
        "node_select_best",
    )
    builder.add_edge(
        "node_select_best",
        END,
    )

    return builder.compile(name="graph_ideas", checkpointer=checkpointer)  # type: ignore
