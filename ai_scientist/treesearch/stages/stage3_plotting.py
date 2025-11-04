import base64
import os
from typing import List, Protocol, Tuple

from ai_scientist.llm.query import FunctionSpec, query

from ..journal import Journal, Node
from ..response_parsing import parse_keyword_prefix_response
from ..types import PromptType
from ..utils.config import Config as AppConfig
from ..vlm_function_specs import plot_selection_spec, vlm_feedback_spec
from .base import Stage


class SupportsStage3Agent(Protocol):
    stage_name: str | None
    cfg: AppConfig

    def plan_and_code_query(self, *, prompt: PromptType, retries: int = 3) -> Tuple[str, str]:
        pass

    @property
    def _prompt_resp_fmt(self) -> dict[str, str]:
        pass


class Stage3Plotting(Stage):
    MAIN_STAGE_SLUG = "creative_research"
    DEFAULT_GOALS = (
        "- Explore novel improvements\n"
        "- Come up with experiments to reveal new insights\n"
        "- Be creative and think outside the box\n"
        "- Test your models on multiple HuggingFace datasets to demonstrate generalization. Use dataset sizes appropriate to the experiment. Usually THREE datasets are enough."
    )

    @staticmethod
    def generate_plotting_code(
        *,
        agent: SupportsStage3Agent,
        node: Node,
        working_dir: str,
        plot_code_from_prev_stage: str | None,
    ) -> str:
        prompt_guideline: list[str] = [
            "AVAILABLE DATA: ",
            "Experiment Data: experiment_data.npy",
        ]
        prompt_guideline += [
            "REQUIREMENTS: ",
            "The code should start with:",
            "  import matplotlib.pyplot as plt",
            "  import numpy as np",
            "  import os",
            "  working_dir = os.path.join(os.getcwd(), 'working')",
            "Create standard visualizations of experiment results",
            "Save all plots to working_dir",
            "Include training/validation curves if available",
            "ONLY plot data that exists in experiment_data.npy - DO NOT make up or simulate any values",
            "Use basic matplotlib without custom styles",
            "Each plot should be in a separate try-except block",
            "Always close figures after saving",
            "Always include a title for each plot, and be sure to use clear subtitles—such as 'Left: Ground Truth, Right: Generated Samples'—while also specifying the type of dataset being used.",
            "Make sure to use descriptive names for figures when saving e.g. always include the dataset name and the type of plot in the name",
            "When there are many similar figures to plot (e.g. generated samples at each epoch), make sure to plot only at a suitable interval of epochs so that you only plot at most 5 figures.",
            "Use the following experiment code to infer the data to plot: " + node.code,
            "Example to extract data from experiment_data: experiment_data['dataset_name_1']['metrics']['train']",
        ]
        prompt_guideline += [
            "Example data loading and plot saving code: ",
            """
                    try:
                        experiment_data = np.load(os.path.join(working_dir, 'experiment_data.npy'), allow_pickle=True).item()
                    except Exception as e:
                        print(f'Error loading experiment data: {e}')

                    try:
                        # First plot
                        plt.figure()
                        # ... plotting code ...
                        plt.savefig('working_dir/[plot_name_1].png')
                        plt.close()
                    except Exception as e:
                        print(f"Error creating plot1: {e}")
                        plt.close()  # Always close figure even if error occurs

                    try:
                        # Second plot
                        plt.figure()
                        # ... plotting code ...
                        plt.savefig('working_dir/[plot_name_2].png')
                        plt.close()
                    except Exception as e:
                        print(f"Error creating plot2: {e}")
                        plt.close()
                """,
        ]

        plotting_prompt: PromptType = {
            "Instructions": {},
        }
        plotting_instructions: dict[str, str | list[str]] = {}
        plotting_instructions |= agent._prompt_resp_fmt
        plotting_instructions |= {
            "Plotting code guideline": prompt_guideline,
        }
        plotting_prompt["Instructions"] = plotting_instructions

        if agent.stage_name and agent.stage_name.startswith("3_") and plot_code_from_prev_stage:
            prompt_guideline.extend(
                [
                    "IMPORTANT: Use the following base plotting code as a starting point:",
                    "Base plotting code: " + plot_code_from_prev_stage,
                    "Modify the base plotting code to:",
                    "1. Keep the same numpy data structure and plotting style",
                    "2. Add comparison plots between different datasets",
                    "3. Add dataset-specific visualizations if needed",
                    "4. Include clear labels indicating which plots are from which dataset",
                    "5. Use consistent naming conventions for saved files",
                ]
            )
        elif agent.stage_name and agent.stage_name.startswith("4_") and plot_code_from_prev_stage:
            prompt_guideline.extend(
                [
                    "IMPORTANT: This is an ablation study. Use the following base plotting code as a starting point:",
                    "Base plotting code: \n" + plot_code_from_prev_stage,
                    "Modify the base plotting code to:",
                    "1. Keep the same numpy data structure and plotting style",
                    "2. Add comparison plots between ablation and baseline results",
                    "3. Add ablation-specific visualizations if needed",
                    "4. Include clear labels indicating which plots are from ablation vs baseline",
                    "5. Use consistent naming conventions for saved files",
                ]
            )

        plan, code = agent.plan_and_code_query(prompt=plotting_prompt)
        if not code.strip().startswith("import"):
            code = "import matplotlib.pyplot as plt\nimport numpy as np\n\n" + code
        node.plot_code = code
        node.plot_plan = plan
        return code

    @staticmethod
    def _encode_image_to_base64(image_path: str) -> str | None:
        try:
            with open(image_path, "rb") as image_file:
                return base64.b64encode(image_file.read()).decode("utf-8")
        except Exception:
            return None

    @staticmethod
    def determine_datasets_successfully_tested(
        *, agent: SupportsStage3Agent, node: Node
    ) -> List[str]:
        plot_analyses = ""
        plot_analyses_list = node.plot_analyses
        for i, plot_analysis in enumerate(plot_analyses_list):
            plot_analyses += f"plot {i + 1}: {plot_analysis['analysis']}\n"

        determine_prompt: dict[str, object] = {
            "Introduction": "You are an AI researcher analyzing experiment results. Based on the plot analyses and feedback, determine which datasets are successfully tested. Return reasoning and the dataset names that are successfully executed, or an empty string if no datasets are successfully executed.",
            "Plot analyses": plot_analyses,
            "VLM feedback summary": node.vlm_feedback_summary,
            "Original plotting code": node.plot_code or "",
            "Response format": (
                "Your response should start with 'REASONING: <reasoning>' to think about the plot analysis and feedback in the first line."
                "In the second line, you should have a list of dataset names that are successfully executed, starting with 'SUCCESSFULLY_TESTED_DATASETS: <list_datasets_successfully_tested>', "
            ),
        }

        retry_count = 0
        retry_limit = 5
        while retry_count < retry_limit:
            response = query(
                system_message=determine_prompt,
                user_message=None,
                model=agent.cfg.agent.feedback.model,
                temperature=agent.cfg.agent.feedback.temp,
            )
            response_text = str(response)
            reasoning, datasets_successfully_tested_str = parse_keyword_prefix_response(
                response_text, "REASONING:", "SUCCESSFULLY_TESTED_DATASETS:"
            )
            if reasoning is not None and datasets_successfully_tested_str is not None:
                if datasets_successfully_tested_str == "":
                    return [""]
                datasets = [ds.strip() for ds in datasets_successfully_tested_str.split(",")]
                datasets = [ds for ds in datasets if isinstance(ds, str) and ds]
                return datasets
            retry_count += 1
        return [""]

    @staticmethod
    def analyze_plots_with_vlm(*, agent: SupportsStage3Agent, node: Node) -> None:
        if not node.plot_paths:
            return
        if len(node.plot_paths) <= 10:
            selected_plots = node.plot_paths
        else:
            prompt_select_plots = {
                "Introduction": (
                    "You are an experienced AI researcher analyzing experimental results. "
                    "You have been provided with plots from a machine learning experiment. "
                    "Please select 10 most relevant plots to analyze. "
                    "For similar plots (e.g. generated samples at each epoch), select only at most 5 plots at a suitable interval of epochs."
                    "Format your response as a list of plot paths, where each plot path includes the full path to the plot file."
                ),
                "Plot paths": node.plot_paths,
            }
            try:
                response_select_plots = query(
                    system_message=prompt_select_plots,
                    user_message=None,
                    func_spec=plot_selection_spec,
                    model=agent.cfg.agent.feedback.model,
                    temperature=agent.cfg.agent.feedback.temp,
                )
                selected_plots = node.plot_paths[:10]
                if isinstance(response_select_plots, dict):
                    candidate = response_select_plots.get("selected_plots", [])
                    valid_plots: list[str] = []
                    if isinstance(candidate, list):
                        for plot_path in candidate:
                            if (
                                isinstance(plot_path, str)
                                and os.path.exists(plot_path)
                                and plot_path.lower().endswith((".png", ".jpg", ".jpeg"))
                            ):
                                valid_plots.append(plot_path)
                    if valid_plots:
                        selected_plots = valid_plots
            except Exception:
                selected_plots = node.plot_paths[:10]

        user_message = [
            {
                "type": "text",
                "text": (
                    "You are an experienced AI researcher analyzing experimental results. "
                    "You have been provided with plots from a machine learning experiment. "
                    f"This experiment is based on the following research idea: {agent.stage_name}"
                    "Please analyze these plots and provide detailed insights about the results. "
                    "If you don't receive any plots, say 'No plots received'. "
                    "Never make up plot analysis. "
                    "Please return the analyzes with strict order of uploaded images, but DO NOT include any word "
                    "like 'the first plot'."
                ),
            }
        ] + [
            {
                "type": "image_url",
                "image_url": {
                    "url": f"data:image/jpeg;base64,{Stage3Plotting._encode_image_to_base64(plot_path)}"
                },
            }
            for plot_path in selected_plots
        ]

        response = query(
            system_message=None,
            user_message=user_message,
            func_spec=vlm_feedback_spec,
            model=agent.cfg.agent.vlm_feedback.model,
            temperature=agent.cfg.agent.vlm_feedback.temp,
        )
        if not isinstance(response, dict):
            return
        valid_plots_received = bool(response.get("valid_plots_received"))
        node.is_buggy_plots = not valid_plots_received

        plot_analyses_val = response.get("plot_analyses")
        if isinstance(plot_analyses_val, list):
            for index, analysis in enumerate(plot_analyses_val):
                if isinstance(analysis, dict) and index < len(node.plot_paths):
                    analysis["plot_path"] = node.plot_paths[index]
            node.plot_analyses = plot_analyses_val

        vlm_summary_val = response.get("vlm_feedback_summary")
        if isinstance(vlm_summary_val, list):
            node.vlm_feedback_summary = [str(x) for x in vlm_summary_val]
        elif isinstance(vlm_summary_val, str):
            node.vlm_feedback_summary = [vlm_summary_val]
        node.datasets_successfully_tested = Stage3Plotting.determine_datasets_successfully_tested(
            agent=agent, node=node
        )

    @staticmethod
    def parse_vlm_feedback(*, node: Node) -> str:
        if len(node.plot_analyses) > 0:
            first_analysis = node.plot_analyses[0]
            analysis_text = (
                str(first_analysis.get("analysis", ""))
                if isinstance(first_analysis, dict)
                else str(first_analysis)
            )
            feedback = f"Plot analyses: {analysis_text}\n"
        else:
            feedback = "No plot analyses found\n"
        feedback += f"VLM Feedback Summary: {node.vlm_feedback_summary}\n"
        return feedback

    @staticmethod
    def compute_substage_completion(
        *, goals: str, journal: Journal, cfg: AppConfig, current_substage_name: str
    ) -> tuple[bool, str]:
        best_node = journal.get_best_node()
        if not best_node:
            return False, "No best node found"
        vlm_feedback = Stage3Plotting.parse_vlm_feedback(node=best_node)
        eval_prompt = f"""
        Evaluate if the current sub-stage is complete based on the following evidence:
        1. Figure Analysis:
        {vlm_feedback}

        Requirements for completion:
        - {goals}

        Provide a detailed evaluation of completion status.
        """
        stage_completion_eval_spec = FunctionSpec(
            name="evaluate_stage_completion",
            description="Evaluate if a stage/sub-stage is complete",
            json_schema={
                "type": "object",
                "properties": {
                    "is_complete": {"type": "boolean"},
                    "reasoning": {"type": "string"},
                    "missing_criteria": {"type": "array", "items": {"type": "string"}},
                },
                "required": ["is_complete", "reasoning", "missing_criteria"],
            },
        )
        evaluation = query(
            system_message=eval_prompt,
            user_message=None,
            func_spec=stage_completion_eval_spec,
            model=cfg.agent.feedback.model,
            temperature=cfg.agent.feedback.temp,
        )
        if isinstance(evaluation, dict) and evaluation.get("is_complete"):
            return True, str(evaluation.get("reasoning", "sub-stage complete"))
        if isinstance(evaluation, dict):
            missing = ", ".join(evaluation.get("missing_criteria", []))
            return False, "Missing criteria: " + missing
        return False, "Sub-stage not complete"

    @staticmethod
    def compute_stage_completion(
        *, journal: Journal, cfg: AppConfig, stage_name: str, max_stage3_iterations: int
    ) -> tuple[bool, str]:
        best_node = journal.get_best_node()
        if not best_node:
            return False, "No best node found"
        if best_node == journal.nodes[0]:
            return False, "No improvement from base node"
        exec_time = best_node.exec_time if best_node.exec_time is not None else 0.0
        exec_time_minutes = exec_time / 60
        if len(journal.nodes) > (max_stage3_iterations / 2):
            if exec_time_minutes < cfg.exec.timeout / 60 / 2:
                exec_time_feedback = (
                    f"Implementation works but runs too quickly ({exec_time_minutes:.2f} minutes). "
                    "Scale up the experiment by increasing epochs, using a larger model, or bigger datasets."
                )
                if journal.nodes:
                    journal.nodes[-1].exec_time_feedback = exec_time_feedback
                return False, exec_time_feedback
        return False, "stage not completed"

    def curate_task_desc(self) -> str:
        return self._context.task_desc

    def evaluate_substage_completion(self) -> tuple[bool, str]:
        return Stage3Plotting.compute_substage_completion(
            goals=self._meta.goals,
            journal=self._context.journal,
            cfg=self._context.cfg,
            current_substage_name=self._context.stage_name,
        )

    def evaluate_stage_completion(self) -> tuple[bool, str]:
        return Stage3Plotting.compute_stage_completion(
            journal=self._context.journal,
            cfg=self._context.cfg,
            stage_name=self._context.stage_name,
            max_stage3_iterations=self._meta.max_iterations,
        )

    def generate_substage_goal(self) -> tuple[str, str]:
        return self._meta.goals, "first_attempt"
