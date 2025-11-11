import os
import os.path as osp
import shutil

import yaml


def edit_bfts_config_file(config_path: str, idea_dir: str, idea_path: str) -> str:
    """
    Edit the bfts_config.yaml file to point to the idea.md file

    Args:
        config_path: Path to the bfts_config.yaml file
        idea_dir: Directory where the idea.md file is located
        idea_path: Path to the idea.md file

    Returns:
        Path to the edited bfts_config.yaml file
    """
    run_config_path = osp.join(idea_dir, "bfts_config.yaml")
    shutil.copy(config_path, run_config_path)
    with open(run_config_path, "r") as f:
        config = yaml.load(f, Loader=yaml.FullLoader)
    config["desc_file"] = idea_path
    config["workspace_dir"] = idea_dir

    # make an empty data directory
    data_dir = osp.join(idea_dir, "data")
    os.makedirs(data_dir, exist_ok=True)
    config["data_dir"] = data_dir

    # make an empty log directory
    log_dir = osp.join(idea_dir, "logs")
    os.makedirs(log_dir, exist_ok=True)
    config["log_dir"] = log_dir

    with open(run_config_path, "w") as f:
        yaml.dump(config, f)
    return run_config_path
