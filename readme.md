# aigraph

Graph implementation based on [Sakana][1]

## About

Scientific research automation using LangGraph agents.

## Development

### Requirements

- **pdflatex**: Required for LaTeX document compilation

```bash
sudo apt-get install texlive
# or
brew install basictex
```

### Setup

```bash
uv sync
```

### LangGraph Core Concepts

- **Context**: Passes runtime dependencies (database connections)
- **State**: Holds graph data relevant to execution
- **Config**: Configures LangChain/LangGraph (e.g., `thread_id`)
- **Checkpointer**: Persists state at each super-step

**Use Cases**:
- Human-in-the-loop: Pause for intervention at nodes
- Memory: Retain conversation history across sessions
- Time travel: Revert to previous execution states
- Fault tolerance: Resume from last checkpoint

**Example**:

```python
from langgraph.graph import StateGraph
from langgraph.checkpoint.memory import MemorySaver

# Define state
class State(TypedDict):
    messages: list[str]

# Node with context access
def process(state: State, context):
    db = context["db"]  # Access runtime dependency
    # Use db connection here
    return {"messages": state["messages"] + ["done"]}

# Build graph
graph = StateGraph(State)
graph.add_node("process", process)
graph.set_entry_point("process")
graph.set_finish_point("process")

# Compile with checkpointer
app = graph.compile(checkpointer=MemorySaver())

# Invoke with config and context
result = app.invoke(
    {"messages": ["start"]},
    config={"configurable": {"thread_id": "1"}},
    context={"db": db_connection}
)
```

## Running Scripts

Execute individual agents:

- `uv run -m aigraph.scripts.run_baseline` - Run baseline experiment
- `uv run -m aigraph.scripts.run_tuning` - Hyperparameter optimization
- `uv run -m aigraph.scripts.run_ablation` - Ablation studies
- `uv run -m aigraph.scripts.run_plotting` - Generate plots and analysis
- `uv run -m aigraph.scripts.run_writeup` - Generate LaTeX document
- `uv run -m aigraph.scripts.run_all` - Execute complete pipeline (includes prepare phase)

## Complete Pipeline (run_all)

Sequential execution with data flow between graphs:

```mermaid
graph TD
    START([START]) --> Prepare[Prepare Graph]
    START --> |cwd, task| Prepare
    Prepare --> |research, metrics, plan| Baseline[Baseline Graph]
    START --> |cwd, task| Baseline
    Baseline --> |experiment_code, summary| Tuning[Tuning Graph]
    Prepare --> |research, metrics, plan| Tuning
    START --> |cwd, task| Tuning
    Tuning --> |tuning_code, summary| Ablation[Ablation Graph]
    Baseline --> |experiment_code, baseline_results| Ablation
    Prepare --> |research, metrics, plan| Ablation
    START --> |cwd, task| Ablation
    Ablation --> |ablation_code| Plotting[Plotting Graph]
    Baseline --> |experiment_code| Plotting
    START --> |cwd, task| Plotting
    Plotting --> |plots| Writeup[Writeup Graph]
    Ablation --> |ablation_code, parser_code, parser_stdout| Writeup
    Prepare --> |research, plan| Writeup
    START --> |cwd, task| Writeup
    Writeup --> END([END])
```

## Agent Architectures

### 1. Prepare Agent

Research, experiment planning, and metrics definition.

```mermaid
graph TD
    START([START]) --> node_create_experiment_plan
    node_create_experiment_plan --> node_research
    node_research --> node_define_metrics
    node_define_metrics --> END([END])
```

### 2. Baseline Agent

Runs baseline experiment with retry and summary generation.

```mermaid
graph TD
    START([START]) --> node_baseline_code_experiment
    node_baseline_code_experiment --> node_baseline_exec_experiment
    node_baseline_exec_experiment --> node_baseline_parse_experiment_output
    node_baseline_parse_experiment_output --> node_baseline_summary
    node_baseline_summary -->|Has Bug| node_baseline_code_experiment
    node_baseline_summary -->|No Bug| node_baseline_code_metrics_parser
    node_baseline_code_metrics_parser --> node_baseline_exec_metrics_parser
    node_baseline_exec_metrics_parser --> node_baseline_parse_metrics_output
    node_baseline_parse_metrics_output -->|Has Bug| node_baseline_code_metrics_parser
    node_baseline_parse_metrics_output -->|No Bug| END([END])
```

### 3. Tuning Agent

Proposes hyperparameters, runs experiments, generates summaries.

```mermaid
graph TD
    START([START]) --> node_tuning_propose_hyperparam
    node_tuning_propose_hyperparam --> node_tuning_code_tuning
    node_tuning_code_tuning --> node_tuning_exec_tuning
    node_tuning_exec_tuning --> node_tuning_parse_tuning_output
    node_tuning_parse_tuning_output --> node_tuning_summary
    node_tuning_summary -->|Has Bug| node_tuning_code_tuning
    node_tuning_summary -->|No Bug| node_tuning_code_metrics_parser
    node_tuning_code_metrics_parser --> node_tuning_exec_metrics_parser
    node_tuning_exec_metrics_parser --> node_tuning_parse_metrics_output
    node_tuning_parse_metrics_output -->|Has Bug| node_tuning_code_metrics_parser
    node_tuning_parse_metrics_output -->|No Bug| END([END])
```

### 4. Ablation Agent

Proposes ablation studies, runs experiments, generates summaries.

```mermaid
graph TD
    START([START]) --> node_ablation_propose_ablation
    node_ablation_propose_ablation --> node_ablation_code_ablation
    node_ablation_code_ablation --> node_ablation_exec_ablation
    node_ablation_exec_ablation --> node_ablation_parse_ablation_output
    node_ablation_parse_ablation_output --> node_ablation_summary
    node_ablation_summary -->|Has Bug| node_ablation_code_ablation
    node_ablation_summary -->|No Bug| node_ablation_code_metrics_parser
    node_ablation_code_metrics_parser --> node_ablation_exec_metrics_parser
    node_ablation_exec_metrics_parser --> node_ablation_parse_metrics_output
    node_ablation_parse_metrics_output -->|Has Bug| node_ablation_code_metrics_parser
    node_ablation_parse_metrics_output -->|No Bug| END([END])
```

### 5. Plotting Agent

Generates plots and analyzes them with fan-out.

```mermaid
graph TD
    START([START]) --> node_plotting_code_plotting
    node_plotting_code_plotting --> node_plotting_exec_plotting
    node_plotting_exec_plotting --> node_plotting_parse_plotting_output
    node_plotting_parse_plotting_output -->|Has Bug| node_plotting_code_plotting
    node_plotting_parse_plotting_output -->|No Bug| node_plotting_analyze_single_plot
    node_plotting_analyze_single_plot -->|Fan Out: One per PNG| END([END])
```

### 6. Writeup Agent

Generates LaTeX document with review and compilation loops.

```mermaid
graph TD
    START([START]) --> node_writeup_setup_writeup
    node_writeup_setup_writeup --> node_writeup_generate_writeup
    node_writeup_generate_writeup --> node_writeup_review_paper
    node_writeup_review_paper -->|Reject & Retry < 3| node_reset_compile_counter
    node_reset_compile_counter --> node_writeup_generate_writeup
    node_writeup_review_paper -->|Accept or Max Retries| node_compile_writeup
    node_compile_writeup --> node_parse_compile_output
    node_parse_compile_output -->|Has Bug| node_writeup_generate_writeup
    node_parse_compile_output -->|No Bug| END([END])
```

[1]: https://github.com/SakanaAI/AI-Scientist