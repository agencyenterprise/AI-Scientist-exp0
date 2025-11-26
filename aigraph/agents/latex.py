import logging
import operator as op
from pathlib import Path
from typing import Annotated, Any, Literal, cast

from langchain.chat_models import BaseChatModel, init_chat_model
from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage
from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph
from langgraph.runtime import Runtime
from langgraph.types import Checkpointer
from pydantic import BaseModel

from aigraph import utils

logger = logging.getLogger(__name__)


class Execution(BaseModel):
    stdout: str
    stderr: str
    returncode: int
    filename: Path


class Output(BaseModel):
    is_error: bool
    summary: str


class State(BaseModel):
    # inputs
    cwd: Path
    prompt: str
    template: str

    # state
    attempts_content: Annotated[list[str], op.add] = []
    attempts_execution: Annotated[list[Execution], op.add] = []
    attempts_output: Annotated[list[Output], op.add] = []

    # outputs
    content: str | None = None


class Context(BaseModel):
    """Configurable context for the latex compiler"""

    model: str = "gpt-4o-mini"
    temperature: float = 0.0
    max_attempts: int = 5

    @property
    def llm(self) -> BaseChatModel:
        return init_chat_model(model=self.model, temperature=self.temperature)


async def node_generate_latex(
    state: State, runtime: Runtime[Context]
) -> dict[str, Any]:
    logger.info("Starting node_generate_latex")

    class Schema(BaseModel):
        content: str

    prompt = "\n".join(
        [
            "You are a LaTeX expert. Your goal is to generate a complete, "
            "compilable LaTeX document. Use the provided template and "
            "fill it with the provided content instructions. Return ONLY "
            "the raw LaTeX code.",
            "",
            "Template for you to base your document on:",
            "",
            "<template>",
            f"{state.template}",
            "</template>",
            "",
            "Content for you to fill the template with:",
            "",
            "<content>",
            f"{state.prompt}",
            "</content>",
        ]
    )

    last_exe: Execution | None = None
    last_out: Output | None = None

    if state.attempts_execution:
        last_exe = state.attempts_execution[-1]
    if state.attempts_output:
        last_out = state.attempts_output[-1]

    memory = ""
    if last_exe:
        memory += "Previous execution:\n\n"
        memory += f"<stdout>\n{last_exe.stdout or 'NA'}\n</stdout>\n\n"
        memory += f"<stderr>\n{last_exe.stderr or 'NA'}\n</stderr>\n\n"
        memory += f"<returncode>\n{last_exe.returncode or 'NA'}\n</returncode>\n\n"
    if last_out:
        memory += "Previous output:\n\n"
        memory += f"<is_bug>\n{last_out.is_error or 'NA'}\n</is_bug>\n\n"
        memory += f"<summary>\n{last_out.summary or 'NA'}\n</summary>\n\n"

    messages: list[BaseMessage] = [SystemMessage(content=prompt)]
    if memory:
        messages.append(HumanMessage(content=memory))

    llms = runtime.context.llm.with_structured_output(Schema)
    response = await llms.ainvoke([SystemMessage(prompt)])
    response = cast(Schema, response)

    logger.debug(f"latex_content length: {len(response.content)}")
    logger.debug(f"latex_content: {response.content[:32]!r}")

    logger.info("Finished node_generate_latex")
    return {"content": response.content, "attempts_content": [response.content]}


async def node_compile(state: State, runtime: Runtime[Context]) -> dict[str, Any]:
    logger.info("Starting node_compile")
    assert state.content is not None, "Content is required"

    file = state.cwd / "template.tex"
    file.write_text(state.content)

    result = await utils.compile(state.cwd, file)

    logger.debug(f"compile_stdout: {result.stdout[:32]!r}")
    logger.debug(f"compile_stderr: {result.stderr[:32]!r}")
    logger.debug(f"compile_returncode: {result.returncode}")

    logger.info("Finished node_compile")
    return {
        "attempts_execution": [
            Execution(
                stdout=result.stdout,
                stderr=result.stderr,
                returncode=result.returncode,
                filename=file,
            ),
        ],
    }


async def node_check_output(state: State, runtime: Runtime[Context]) -> dict[str, Any]:
    logger.info("Starting node_check_output")
    assert state.content is not None, "Content is required"
    assert state.attempts_execution is not None, "Attempts execution is required"
    assert len(state.attempts_execution) > 0, "Attempts execution is required"

    prompt = "\n".join(
        [
            "You are a LaTeX expert. Your goal is to analyze the pdflatex ",
            "compilation output and determine if there are any errors or ",
            "issues.",
            "",
            "Search for `LaTeX Error` in the outputs and add a possible fix ",
            "if you can.",
            "",
            "Look for common LaTeX errors like undefined commands, missing "
            "packages, syntax errors, or file not found errors",
            "",
            "Provide a clear summary of what happened during compilation, "
            "including any specific errors found. and possible fixes.",
            "",
            "Content:",
            "",
            f"<content>\n{state.content}\n</content>",
            "",
            "Stdout:",
            "",
            f"<stdout>\n{state.attempts_execution[-1].stdout}\n</stdout>",
            "",
            "Stderr:",
            "",
            f"<stderr>\n{state.attempts_execution[-1].stderr}\n</stderr>",
            "",
            "Return code:",
            "",
            f"<returncode>\n{state.attempts_execution[-1].returncode}\n</returncode>",
        ]
    )

    llms = runtime.context.llm.with_structured_output(Output)
    response = await llms.ainvoke([SystemMessage(prompt)])
    response = cast(Output, response)

    logger.debug(f"compile_is_bug: {response.is_error}")
    logger.debug(f"compile_summary: {response.summary[:32]!r}")

    logger.info("Finished node_check_output")
    return {"attempts_output": [response.model_dump()]}


async def node_should_retry(
    state: State, runtime: Runtime[Context]
) -> Literal["node_generate_latex", "__end__"]:
    logger.info("Starting node_should_retry")
    assert state.attempts_output is not None, "Attempts output is required"
    assert len(state.attempts_output) > 0, "Attempts output is required"

    last_out = state.attempts_output[-1]

    if last_out.is_error:
        logger.info("Going to `node_generate_latex`")
        return "node_generate_latex"

    logger.info("Going to `__end__`")
    return "__end__"


def build(
    checkpointer: Checkpointer = None,
) -> CompiledStateGraph[State, Context, State, State]:
    builder = StateGraph(state_schema=State, context_schema=Context)

    builder.add_node("node_generate_latex", node_generate_latex)
    builder.add_node("node_compile", node_compile)
    builder.add_node("node_check_output", node_check_output)

    builder.add_edge(START, "node_generate_latex")
    builder.add_edge("node_generate_latex", "node_compile")
    builder.add_edge("node_compile", "node_check_output")
    builder.add_conditional_edges(
        "node_check_output",
        node_should_retry,
        ["node_generate_latex", END],
    )

    return builder.compile(name="graph_latex", checkpointer=checkpointer)  # type: ignore
