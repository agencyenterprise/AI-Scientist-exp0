import multiprocessing
import os
import pickle
import traceback
from pathlib import Path
from typing import Callable, Optional

from .codegen_agent import MinimalAgent
from .interpreter import Interpreter
from .journal import Node
from .stages.stage1_baseline import Stage1Baseline
from .stages.stage2_tuning import Stage2Tuning
from .stages.stage3_plotting import Stage3Plotting
from .stages.stage4_ablation import Stage4Ablation
from .utils.config import Config as AppConfig


def process_node(
    *,
    node_data: dict[str, object] | None,
    task_desc: str,
    cfg: AppConfig,
    gpu_id: Optional[int] = None,
    memory_summary: Optional[str] = None,
    evaluation_metrics: str | list[str] | None = None,
    stage_name: Optional[str] = None,
    new_ablation_idea: Optional[object] = None,
    new_hyperparam_idea: Optional[object] = None,
    best_stage3_plot_code: Optional[str] = None,
    best_stage2_plot_code: Optional[str] = None,
    best_stage1_plot_code: Optional[str] = None,
    seed_eval: bool = False,
    event_callback: Optional[Callable[[str, dict[str, object]], None]] = None,
) -> dict[str, object]:
    def emit(event_type: str, data: dict[str, object]) -> None:
        if event_callback:
            try:
                data["stage"] = stage_name
                event_callback(event_type, data)
            except Exception:
                pass

    process_id = multiprocessing.current_process().name
    workspace = os.path.join(cfg.workspace_dir, f"process_{process_id}")
    os.makedirs(workspace, exist_ok=True)
    working_dir = os.path.join(workspace, "working")
    os.makedirs(working_dir, exist_ok=True)

    if gpu_id is not None:
        os.environ["CUDA_VISIBLE_DEVICES"] = str(gpu_id)
    else:
        os.environ["CUDA_VISIBLE_DEVICES"] = ""

    worker_agent = MinimalAgent(
        task_desc=task_desc,
        cfg=cfg,
        memory_summary=memory_summary,
        evaluation_metrics=evaluation_metrics,
        stage_name=stage_name,
    )

    process_interpreter = Interpreter(
        working_dir=workspace,
        timeout=cfg.exec.timeout,
        format_tb_ipython=cfg.exec.format_tb_ipython,
        agent_file_name=cfg.exec.agent_file_name,
    )

    try:
        if node_data:
            parent_node = Node.from_dict(node_data, journal=None)
        else:
            parent_node = None

        if seed_eval:
            assert parent_node is not None, "parent_node must be provided for seed evaluation"
            emit("ai.run.log", {"message": "Running multi-seed evaluation", "level": "info"})
            child_node = worker_agent._generate_seed_node(parent_node)
            child_node.parent = parent_node
            child_node.plot_code = parent_node.plot_code
        else:
            if parent_node is None:
                emit(
                    "ai.run.log", {"message": "Generating new implementation code", "level": "info"}
                )
                child_node = Stage1Baseline.draft(worker_agent)
                emit("ai.run.log", {"message": "Code generation complete", "level": "info"})
            elif parent_node.is_buggy:
                emit(
                    "ai.run.log",
                    {"message": "Debugging failed node (attempt to fix bugs)", "level": "info"},
                )
                child_node = worker_agent._debug(parent_node)
                child_node.parent = parent_node
                emit("ai.run.log", {"message": "Fix attempt generated", "level": "info"})
            else:
                if new_hyperparam_idea is not None and new_ablation_idea is None:
                    child_node = Stage2Tuning.build_hyperparam_tuning_node(agent=worker_agent, parent_node=parent_node, hyperparam_idea=new_hyperparam_idea)  # type: ignore[arg-type]
                    child_node.parent = parent_node
                elif new_ablation_idea is not None and new_hyperparam_idea is None:
                    child_node = Stage4Ablation.build_ablation_node(agent=worker_agent, parent_node=parent_node, ablation_idea=new_ablation_idea)  # type: ignore[arg-type]
                    child_node.parent = parent_node
                else:
                    child_node = Stage1Baseline.improve(agent=worker_agent, parent_node=parent_node)
                    child_node.parent = parent_node

        emit("ai.run.log", {"message": "Executing experiment code on GPU...", "level": "info"})
        exec_result = process_interpreter.run(child_node.code, True)
        process_interpreter.cleanup_session()
        emit(
            "ai.run.log",
            {
                "message": f"Code execution completed ({exec_result.exec_time:.1f}s)",
                "level": "info",
            },
        )

        emit("ai.run.log", {"message": "Analyzing results and extracting metrics", "level": "info"})
        worker_agent.parse_exec_result(
            node=child_node, exec_result=exec_result, workspace=working_dir
        )

        if not child_node.is_buggy:
            try:
                emit("ai.run.log", {"message": "Generating visualization plots", "level": "info"})
                retry_count = 0
                while True:
                    if seed_eval:
                        assert parent_node is not None
                        plotting_code = parent_node.plot_code or ""
                    else:
                        if (
                            worker_agent.stage_name
                            and worker_agent.stage_name.startswith("3_")
                            and best_stage2_plot_code
                        ):
                            plot_code_from_prev_stage = best_stage2_plot_code
                        elif (
                            worker_agent.stage_name
                            and worker_agent.stage_name.startswith("4_")
                            and best_stage3_plot_code
                        ):
                            plot_code_from_prev_stage = best_stage3_plot_code
                        else:
                            plot_code_from_prev_stage = None

                        plotting_code = Stage3Plotting.generate_plotting_code(
                            agent=worker_agent,
                            node=child_node,
                            working_dir=working_dir,
                            plot_code_from_prev_stage=plot_code_from_prev_stage,
                        )
                    emit("ai.run.log", {"message": "Executing plotting code", "level": "info"})
                    plot_exec_result = process_interpreter.run(plotting_code, True)
                    process_interpreter.cleanup_session()
                    child_node.absorb_plot_exec_result(plot_exec_result)
                    if child_node.plot_exc_type and retry_count < 3:
                        retry_count += 1
                        continue
                    else:
                        break

                plots_dir = Path(working_dir)
                if plots_dir.exists():
                    plot_count = len(list(plots_dir.glob("*.png")))
                    if plot_count > 0:
                        emit(
                            "ai.run.log",
                            {"message": f"✓ Generated {plot_count} plot file(s)", "level": "info"},
                        )

                    base_dir = Path(cfg.workspace_dir).parent
                    run_name = Path(cfg.workspace_dir).name
                    exp_results_dir = (
                        base_dir
                        / "logs"
                        / run_name
                        / "experiment_results"
                        / f"experiment_{child_node.id}_proc_{os.getpid()}"
                    )
                    child_node.exp_results_dir = str(exp_results_dir)
                    exp_results_dir.mkdir(parents=True, exist_ok=True)
                    plot_code_path = exp_results_dir / "plotting_code.py"
                    with open(plot_code_path, "w") as f:
                        f.write(plotting_code)
                    exp_code_path = exp_results_dir / "experiment_code.py"
                    with open(exp_code_path, "w") as f:
                        f.write(child_node.code)
                    for exp_data_file in plots_dir.glob("*.npy"):
                        exp_data_path = exp_results_dir / exp_data_file.name
                        exp_data_file.resolve().rename(exp_data_path)

                    for plot_file in plots_dir.glob("*.png"):
                        final_path = exp_results_dir / plot_file.name
                        plot_file.resolve().rename(final_path)
                        web_path = f"../../logs/{Path(cfg.workspace_dir).name}/experiment_results/experiment_{child_node.id}_proc_{os.getpid()}/{plot_file.name}"
                        child_node.plots.append(web_path)
                        child_node.plot_paths.append(str(final_path.absolute()))
            except Exception:
                pass

            if child_node.plots:
                try:
                    emit(
                        "ai.run.log",
                        {
                            "message": f"Analyzing {len(child_node.plots)} generated plots with VLM",
                            "level": "info",
                        },
                    )
                    Stage3Plotting.analyze_plots_with_vlm(agent=worker_agent, node=child_node)
                    emit("ai.run.log", {"message": "✓ Plot analysis complete", "level": "info"})
                except Exception:
                    emit("ai.run.log", {"message": "Plot analysis failed", "level": "warn"})

        result_data = child_node.to_dict()
        # sanity pickle

        pickle.dumps(result_data)
        return result_data
    except Exception:

        traceback.print_exc()
        raise
    finally:
        if process_interpreter:
            process_interpreter.cleanup_session()
