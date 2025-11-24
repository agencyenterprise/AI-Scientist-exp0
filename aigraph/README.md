# aigraph

Graph implementation based on [Sakana][1]

## About

Scientific research automation using LangGraph agents.

## Agent Architectures

### 1. Baseline Agent

Defines metrics and runs baseline experiment.

```mermaid
graph TD
    START([START]) --> node_baseline_define_metrics
    node_baseline_define_metrics --> node_baseline_code_experiment
    node_baseline_code_experiment --> node_baseline_exec_experiment
    node_baseline_exec_experiment --> node_baseline_parse_experiment_output
    node_baseline_parse_experiment_output -->|Has Bug| node_baseline_code_experiment
    node_baseline_parse_experiment_output -->|No Bug| node_baseline_code_metrics_parser
    node_baseline_code_metrics_parser --> node_baseline_exec_metrics_parser
    node_baseline_exec_metrics_parser --> node_baseline_parse_metrics_output
    node_baseline_parse_metrics_output -->|Has Bug| node_baseline_code_metrics_parser
    node_baseline_parse_metrics_output -->|No Bug| END([END])
```

### 2. Tuning Agent

Proposes and tests hyperparameters.

```mermaid
graph TD
    START([START]) --> node_tuning_propose_hyperparam
    node_tuning_propose_hyperparam --> node_tuning_code_tuning
    node_tuning_code_tuning --> node_tuning_exec_tuning
    node_tuning_exec_tuning --> node_tuning_parse_tuning_output
    node_tuning_parse_tuning_output -->|Has Bug| node_tuning_code_tuning
    node_tuning_parse_tuning_output -->|No Bug| node_tuning_code_metrics_parser
    node_tuning_code_metrics_parser --> node_tuning_exec_metrics_parser
    node_tuning_exec_metrics_parser --> node_tuning_parse_metrics_output
    node_tuning_parse_metrics_output -->|Has Bug| node_tuning_code_metrics_parser
    node_tuning_parse_metrics_output -->|No Bug| END([END])
```

### 3. Ablation Agent

Proposes and runs ablation studies.

```mermaid
graph TD
    START([START]) --> node_ablation_propose_ablation
    node_ablation_propose_ablation --> node_ablation_code_ablation
    node_ablation_code_ablation --> node_ablation_exec_ablation
    node_ablation_exec_ablation --> node_ablation_parse_ablation_output
    node_ablation_parse_ablation_output -->|Has Bug| node_ablation_code_ablation
    node_ablation_parse_ablation_output -->|No Bug| node_ablation_code_metrics_parser
    node_ablation_code_metrics_parser --> node_ablation_exec_metrics_parser
    node_ablation_exec_metrics_parser --> node_ablation_parse_metrics_output
    node_ablation_parse_metrics_output -->|Has Bug| node_ablation_code_metrics_parser
    node_ablation_parse_metrics_output -->|No Bug| END([END])
```

### 4. Plotting Agent

Generates and analyzes visualization plots.

```mermaid
graph TD
    START([START]) --> node_plotting_code_plotting
    node_plotting_code_plotting --> node_plotting_exec_plotting
    node_plotting_exec_plotting --> node_plotting_parse_plotting_output
    node_plotting_parse_plotting_output -->|Has Bug| node_plotting_code_plotting
    node_plotting_parse_plotting_output -->|No Bug| node_plotting_prepare_analysis
    node_plotting_prepare_analysis -->|Fan Out| node_plotting_analyze_single_plot
    node_plotting_analyze_single_plot --> END([END])
```

### 5. Writeup Agent

Generates and compiles LaTeX document.

```mermaid
graph TD
    START([START]) --> node_writeup_setup_writeup
    node_writeup_setup_writeup --> node_writeup_generate_writeup
    node_writeup_generate_writeup --> node_compile_writeup
    node_compile_writeup --> node_parse_compile_output
    node_parse_compile_output -->|Has Bug| node_writeup_generate_writeup
    node_parse_compile_output -->|No Bug| END([END])
```

[1]: https://github.com/SakanaAI/AI-Scientist