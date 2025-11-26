import logging
import operator as op
from typing import Annotated, Any

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


class Research(BaseModel):
    is_novel: bool
    summary: str
    related_papers: list[str]
    research: AgentState


class Analysis(BaseModel):
    score: int
    rationale: str


class Idea(BaseModel):
    title: str
    description: str
    plan: str


class State(BaseModel):
    # inputs
    research_domain: str
    prompt_generate: str
    prompt_novelty: str
    prompt_score: str

    # state
    ideas: Annotated[list[Idea], op.add] = []
    researches: Annotated[list[Research], op.add] = []
    analyses: Annotated[list[Analysis], op.add] = []

    # outputs
    idea: Idea | None = None
    research: Research | None = None
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
    for idea in state.ideas:
        sends.append(
            Send(
                "node_research",
                {
                    "idea": idea,
                    "prompt_score": state.prompt_score,
                    "prompt_novelty": state.prompt_novelty,
                },
            )
        )

    logger.info("Finished node_generate_ideas")
    return sends


class InteralState(BaseModel):
    # inputs
    idea: Idea
    prompt_score: str
    prompt_novelty: str

    # outputs
    research: Research | None = None
    analysis: Analysis | None = None


async def node_research(
    state: InteralState,
    runtime: Runtime[Context],
) -> dict[str, Any]:
    logger.info("Starting node_check_novelty")
    assert state.idea is not None, "Idea is required"

    class SchemaAnalysis(BaseModel):
        is_novel: bool
        similar_papers: list[str]
        novelty_summary: str

    class SchemaScore(BaseModel):
        score: int
        rationale: str

    prompt = ""
    prompt += "Research idea:\n\n"
    prompt += f"<title>\n{state.idea.title}\n</title>\n\n"
    prompt += "Description:\n\n"
    prompt += f"<description>\n{state.idea.description}\n</description>\n\n"
    prompt += "Plan:\n\n"
    prompt += f"<plan>\n{state.idea.plan}\n</plan>\n\n"

    messages_researcher: list[BaseMessage] = [HumanMessage(content=prompt)]
    graph = researcher.deep_researcher_builder.compile(checkpointer=True)

    res_research: AgentState = await graph.ainvoke(  # type: ignore
        input={"messages": messages_researcher},
        config={
            "configurable": {
                "allow_clarification": False,
                "max_researcher_iterations": 2,
            }
        },
    )

    logger.debug(f"Research report: {res_research['final_report'][:32]!r}")

    messages_novel: list[BaseMessage] = [
        SystemMessage(content=state.prompt_novelty),
        HumanMessage(content=f"Research report: {res_research['final_report']}"),
        HumanMessage(content=res_research["final_report"]),
    ]

    llms_novel = runtime.context.llm.with_structured_output(SchemaAnalysis)
    res_novel: SchemaAnalysis = await llms_novel.ainvoke({"messages": messages_novel})  # type: ignore

    logger.debug(f"Is novel: {res_novel.is_novel}")
    logger.debug(f"Related papers: {res_novel.similar_papers[:4]!r}")
    logger.debug(f"Novelty summary: {res_novel.novelty_summary[:32]!r}")

    messages_score: list[BaseMessage] = [
        SystemMessage(content=state.prompt_score),
        HumanMessage(content=f"Novelty summary: {res_novel.novelty_summary}"),
        HumanMessage(content=res_novel.novelty_summary),
    ]

    llms_score = runtime.context.llm.with_structured_output(SchemaScore)
    res_score: SchemaScore = await llms_score.ainvoke({"messages": messages_score})  # type: ignore

    logger.info("Finished node_check_novelty")
    return {
        "idea": state.idea,
        "research": Research(
            is_novel=res_novel.is_novel,
            summary=res_novel.novelty_summary,
            related_papers=res_novel.similar_papers,
            research=res_research,
        ),
        "analysis": Analysis(
            score=res_score.score,
            rationale=res_score.rationale,
        ),
    }


async def node_aggregate_research(
    state: InteralState,
    runtime: Runtime[Context],
) -> dict[str, Any]:
    logger.info("Starting node_aggregate_research")
    assert state.research is not None, "Research is required"
    assert state.analysis is not None, "Analysis is required"

    logger.info("Finished node_aggregate_research")
    return {
        "ideas": [state.idea],
        "researches": [state.research],
        "analyses": [state.analysis],
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
        prompt += f"<summary>\n{research.summary}\n</summary>\n\n"
        prompt += f"<related_papers>\n{research.related_papers}\n</related_papers>\n\n"
        prompt += f"<research>\n{research.research}\n</research>\n\n"
        prompt += "----------------------------------------\n\n"
        prompt += f"Analysis {i}:\n\n"
        prompt += f"<score>\n{analysis.score}\n</score>\n\n"
        prompt += f"<rationale>\n{analysis.rationale}\n</rationale>\n\n"
        prompt += "========================================\n\n"

    system = "Select the best idea based on the research and analysis"
    messages: list[BaseMessage] = [
        SystemMessage(content=system),
        HumanMessage(content=prompt),
    ]

    llms = runtime.context.llm.with_structured_output(Schema)
    response: Schema = await llms.ainvoke({"messages": messages})  # type: ignore

    logger.info("Finished node_select_best")
    return {"idea": state.idea}


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
        "node_aggregate_research",
        node_aggregate_research,
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
        "node_aggregate_research",
    )
    builder.add_edge(
        "node_aggregate_research",
        "node_select_best",
    )
    builder.add_edge(
        "node_select_best",
        END,
    )

    return builder.compile(name="graph_ideas", checkpointer=checkpointer)  # type: ignore
