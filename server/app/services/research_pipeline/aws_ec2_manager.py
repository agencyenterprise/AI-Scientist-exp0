"""
Provision and manage research pipeline workers on AWS EC2.
"""

from __future__ import annotations

import base64
import json
import logging
import os
import shlex
import subprocess
import tempfile
from dataclasses import dataclass
from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, cast

import boto3
from botocore.exceptions import BotoCoreError, ClientError
from omegaconf import OmegaConf


class AWSEC2Error(Exception):
    """AWS EC2 provisioning error."""

    def __init__(self, message: str):
        super().__init__(message)


logger = logging.getLogger(__name__)

CONFIG_TEMPLATE_PATH = Path(__file__).resolve().parent / "bfts_config_template.yaml"
WORKER_SETUP_SCRIPT_PATH = Path(__file__).resolve().parent / "worker_repo_setup.sh"
WORKER_INSTALL_SCRIPT_PATH = Path(__file__).resolve().parent / "install_worker.sh"


def _require_env(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        raise RuntimeError(f"Environment variable {name} is required.")
    return value


def _optional_env(name: str) -> str | None:
    value = os.environ.get(name)
    return value if value else None


def _parse_security_groups(value: str) -> list[str]:
    groups = [item.strip() for item in value.split(",") if item.strip()]
    if not groups:
        raise RuntimeError("AWS_EC2_SECURITY_GROUP_IDS must include at least one id.")
    return groups


def _parse_int(value: str, *, env_name: str) -> int:
    try:
        return int(value)
    except ValueError as exc:
        raise RuntimeError(f"{env_name} must be an integer.") from exc


@dataclass
class WorkerEnvironment:
    git_deploy_key: str
    repo_org: str
    repo_branch: str
    openai_api_key: str
    hf_token: str
    database_public_url: str
    telemetry_webhook_url: str
    telemetry_webhook_token: str
    aws_region: str
    aws_s3_bucket_name: str
    aws_access_key_id: str
    aws_secret_access_key: str
    subnet_id: str
    security_group_ids: list[str]
    ami_id: str
    instance_type: str
    key_name: str
    instance_profile_arn: str | None
    volume_size_gb: int
    worker_public_key: str | None

    def git_deploy_key_b64(self) -> str:
        return base64.b64encode(self.git_deploy_key.encode("utf-8")).decode("utf-8")


def _load_worker_environment() -> WorkerEnvironment:
    git_key = _require_env("GIT_DEPLOY_KEY").replace("\\n", "\n")
    repo_org = os.environ.get("REPO_ORG", "agencyenterprise")
    repo_branch = os.environ.get("REPO_BRANCH", "main")
    return WorkerEnvironment(
        git_deploy_key=git_key,
        repo_org=repo_org,
        repo_branch=repo_branch,
        openai_api_key=_require_env("OPENAI_API_KEY"),
        hf_token=_require_env("HF_TOKEN"),
        database_public_url=_require_env("DATABASE_PUBLIC_URL"),
        telemetry_webhook_url=_require_env("TELEMETRY_WEBHOOK_URL"),
        telemetry_webhook_token=_require_env("TELEMETRY_WEBHOOK_TOKEN"),
        aws_region=_require_env("AWS_REGION"),
        aws_s3_bucket_name=_require_env("AWS_S3_BUCKET_NAME"),
        aws_access_key_id=_require_env("AWS_ACCESS_KEY_ID"),
        aws_secret_access_key=_require_env("AWS_SECRET_ACCESS_KEY"),
        subnet_id=_require_env("AWS_EC2_SUBNET_ID"),
        security_group_ids=_parse_security_groups(_require_env("AWS_EC2_SECURITY_GROUP_IDS")),
        ami_id=_require_env("AWS_EC2_AMI_ID"),
        instance_type=_require_env("AWS_EC2_INSTANCE_TYPE"),
        key_name=_require_env("AWS_EC2_KEY_NAME"),
        instance_profile_arn=_optional_env("AWS_EC2_INSTANCE_PROFILE_ARN"),
        volume_size_gb=_parse_int(
            _require_env("AWS_EC2_ROOT_VOLUME_GB"), env_name="AWS_EC2_ROOT_VOLUME_GB"
        ),
        worker_public_key=_optional_env("WORKER_SSH_PUBLIC_KEY"),
    )


def _load_script(path: Path, *, description: str) -> str:
    if not path.exists():
        raise RuntimeError(f"{description} missing at {path}.")
    return path.read_text(encoding="utf-8").strip()


def _encode_multiline(value: str) -> str:
    return base64.b64encode(value.encode("utf-8")).decode("utf-8")


def _prepare_yaml_config(*, idea_filename: str, telemetry: dict[str, str]) -> str:
    if not CONFIG_TEMPLATE_PATH.exists():
        raise RuntimeError(
            f"Pipeline config template missing at {CONFIG_TEMPLATE_PATH}. Ensure the file exists."
        )
    config = OmegaConf.load(CONFIG_TEMPLATE_PATH)
    logger.info(
        "Preparing pipeline config from %s with desc_file=%s",
        CONFIG_TEMPLATE_PATH,
        idea_filename,
    )
    config.desc_file = idea_filename
    config.telemetry = telemetry or None
    config_yaml = OmegaConf.to_yaml(config)
    if not config_yaml.endswith("\n"):
        config_yaml += "\n"
    return config_yaml


def _export_line(name: str, value: str) -> str:
    return f"export {name}={shlex.quote(value)}"


def _collect_repo_exports(*, env: WorkerEnvironment) -> list[str]:
    exports = [
        _export_line(name="WORKSPACE_DIR", value="/workspace"),
        _export_line(name="REPO_NAME", value="AE-Scientist"),
        _export_line(name="REPO_ORG", value=env.repo_org),
        _export_line(name="REPO_BRANCH", value=env.repo_branch),
        _export_line(name="GIT_SSH_KEY_B64", value=env.git_deploy_key_b64()),
    ]
    if env.worker_public_key:
        exports.append(_export_line(name="PUBLIC_KEY", value=env.worker_public_key))
    return exports


def _repository_setup_commands(*, env: WorkerEnvironment) -> list[str]:
    script_text = _load_script(
        WORKER_SETUP_SCRIPT_PATH,
        description="Worker repository setup script",
    )
    return _collect_repo_exports(env=env) + [
        "# === Repository Setup ===",
        "cat <<'WORKER_SETUP' | bash",
        script_text,
        "WORKER_SETUP",
        "",
    ]


def _installation_commands() -> list[str]:
    script_text = _load_script(
        WORKER_INSTALL_SCRIPT_PATH,
        description="Worker installation script",
    )
    return [
        "# === Installation ===",
        'echo "Running installation script..."',
        "cd /workspace/AE-Scientist",
        "cat <<'WORKER_INSTALL' | bash",
        script_text,
        "WORKER_INSTALL",
        "",
    ]


def _build_user_data_script(
    *,
    env: WorkerEnvironment,
    idea_filename: str,
    idea_content_b64: str,
    config_filename: str,
    config_content_b64: str,
    run_id: str,
) -> str:
    script_parts: list[str] = [
        "#!/bin/bash",
        "set -euo pipefail",
        "export DEBIAN_FRONTEND=noninteractive",
        "",
        'echo "Bootstrapping AE Scientist worker..."',
        "",
    ]
    script_parts += _repository_setup_commands(env=env)
    script_parts += _installation_commands()
    script_parts += [
        "# === Environment Setup ===",
        "cd /workspace/AE-Scientist/research_pipeline",
        "cat > .env << 'EOF'",
        f"OPENAI_API_KEY={env.openai_api_key}",
        f"HF_TOKEN={env.hf_token}",
        f"AWS_ACCESS_KEY_ID={env.aws_access_key_id}",
        f"AWS_SECRET_ACCESS_KEY={env.aws_secret_access_key}",
        f"AWS_REGION={env.aws_region}",
        f"AWS_S3_BUCKET_NAME={env.aws_s3_bucket_name}",
        f"RUN_ID={run_id}",
        f"DATABASE_PUBLIC_URL={env.database_public_url}",
        "EOF",
        "",
        "# === Inject refined idea and config ===",
        "cd /workspace/AE-Scientist/research_pipeline",
        "python - <<'PY'",
        "import base64, pathlib",
        f"pathlib.Path('{idea_filename}').write_bytes(base64.b64decode('{idea_content_b64}'))",
        f"pathlib.Path('{config_filename}').write_bytes(base64.b64decode('{config_content_b64}'))",
        "PY",
        "",
        "# === GPU Validation ===",
        'echo "Validating GPU..."',
        'nvidia-smi || { echo "❌ nvidia-smi failed"; exit 1; }',
        'echo "✅ GPU validated"',
        "source .venv/bin/activate",
        "python - <<'PY' || { echo \"❌ PyTorch CUDA initialization failed\"; exit 1; }",
        "import torch",
        "torch.cuda.set_device(0)",
        "print('✅ PyTorch device initialized successfully')",
        "PY",
        "",
        "# === Starting Research Pipeline ===",
        'echo "Launching research pipeline..."',
        "pipeline_exit_code=0",
        "set +e",
        f"python launch_scientist_bfts.py '{config_filename}' 2>&1 | tee -a /workspace/research_pipeline.log",
        "pipeline_exit_code=$?",
        "set -e",
        'if [ "$pipeline_exit_code" -eq 0 ]; then',
        '  echo "Research pipeline completed successfully. Check /workspace/research_pipeline.log for full output."',
        "else",
        '  echo "Research pipeline failed. Check /workspace/research_pipeline.log for details."',
        "fi",
        "",
        "# === Upload Research Pipeline Log to S3 ===",
        'echo "Uploading research pipeline log to S3 (best-effort)..."',
        "python upload_worker_log.py --log-path /workspace/research_pipeline.log --artifact-type run_log || true",
        'if [ "$pipeline_exit_code" -ne 0 ]; then',
        '  echo "Research pipeline failed with exit code $pipeline_exit_code (log uploaded)."',
        "  python upload_worker_workspace.py --workspace-path /workspace/AE-Scientist/workspaces/0-run --artifact-type workspace_archive --archive-name 0-run-workspace.zip || true",
        "else",
        '  echo "Research pipeline finished successfully (log uploaded)."',
        "fi",
    ]
    return "\n".join(script_parts).strip()


class AWSEC2Manager:
    def __init__(self, *, region: str):
        self.region = region
        self.ec2 = boto3.client("ec2", region_name=region)

    def launch_instance(self, *, env: WorkerEnvironment, user_data: str, run_id: str) -> str:
        block_device_mappings = [
            {
                "DeviceName": "/dev/xvda",
                "Ebs": {
                    "VolumeSize": env.volume_size_gb,
                    "VolumeType": "gp3",
                    "DeleteOnTermination": True,
                    "Encrypted": True,
                },
            }
        ]
        network_interface = {
            "DeviceIndex": 0,
            "AssociatePublicIpAddress": True,
            "SubnetId": env.subnet_id,
            "Groups": env.security_group_ids,
        }
        tag_specifications = [
            {
                "ResourceType": "instance",
                "Tags": [
                    {"Key": "Name", "Value": f"ae-scientist-{run_id}"},
                    {"Key": "RunId", "Value": run_id},
                    {"Key": "Project", "Value": "ae-scientist"},
                ],
            }
        ]
        request: dict[str, Any] = {
            "ImageId": env.ami_id,
            "InstanceType": env.instance_type,
            "MinCount": 1,
            "MaxCount": 1,
            "KeyName": env.key_name,
            "BlockDeviceMappings": block_device_mappings,
            "NetworkInterfaces": [network_interface],
            "TagSpecifications": tag_specifications,
            "InstanceInitiatedShutdownBehavior": "terminate",
            "UserData": user_data,
        }
        if env.instance_profile_arn:
            request["IamInstanceProfile"] = {"Arn": env.instance_profile_arn}
        try:
            response: dict[str, Any] = self.ec2.run_instances(**request)
        except (ClientError, BotoCoreError) as exc:
            raise AWSEC2Error(f"Failed to launch EC2 instance: {exc}") from exc
        instances = cast(list[dict[str, Any]], response.get("Instances", []))
        if not instances:
            raise AWSEC2Error("No instances returned from run_instances call.")
        instance_id_value = instances[0].get("InstanceId")
        if not isinstance(instance_id_value, str):
            raise AWSEC2Error("run_instances response missing InstanceId.")
        return instance_id_value

    def describe_instance(self, *, instance_id: str) -> dict[str, Any]:
        try:
            response: dict[str, Any] = self.ec2.describe_instances(InstanceIds=[instance_id])
        except (ClientError, BotoCoreError) as exc:
            raise AWSEC2Error(f"Failed to describe instance {instance_id}: {exc}") from exc
        reservations = cast(list[dict[str, Any]], response.get("Reservations", []))
        if not reservations:
            raise AWSEC2Error(f"No reservations returned for instance {instance_id}.")
        instances = cast(list[dict[str, Any]], reservations[0].get("Instances", []))
        if not instances:
            raise AWSEC2Error(f"No instances returned for id {instance_id}.")
        return instances[0]

    def wait_for_instance_ready(self, *, instance_id: str) -> dict[str, Any]:
        try:
            waiter = self.ec2.get_waiter("instance_running")
            waiter.wait(InstanceIds=[instance_id])
        except (ClientError, BotoCoreError) as exc:
            raise AWSEC2Error(
                f"Failed while waiting for instance {instance_id} to run: {exc}"
            ) from exc
        instance = self.describe_instance(instance_id=instance_id)
        if not instance.get("PublicIpAddress"):
            try:
                status_waiter = self.ec2.get_waiter("instance_status_ok")
                status_waiter.wait(InstanceIds=[instance_id])
                instance = self.describe_instance(instance_id=instance_id)
            except (ClientError, BotoCoreError) as exc:
                raise AWSEC2Error(
                    f"Instance {instance_id} failed to reach OK status: {exc}"
                ) from exc
        if not instance.get("PublicIpAddress"):
            raise AWSEC2Error(f"Instance {instance_id} did not acquire a public IP.")
        return instance

    def terminate_instance(self, *, instance_id: str) -> None:
        try:
            self.ec2.terminate_instances(InstanceIds=[instance_id])
        except (ClientError, BotoCoreError) as exc:
            raise AWSEC2Error(f"Failed to terminate instance {instance_id}: {exc}") from exc


def _extract_instance_name(instance: dict[str, Any]) -> str | None:
    for tag in instance.get("Tags", []):
        if tag.get("Key") == "Name":
            value = tag.get("Value")
            if isinstance(value, str):
                return value
    return None


def _instance_launch_time(instance: dict[str, Any]) -> datetime | None:
    launch_time = instance.get("LaunchTime")
    if isinstance(launch_time, datetime):
        if launch_time.tzinfo is None:
            return launch_time.replace(tzinfo=timezone.utc)
        return launch_time.astimezone(timezone.utc)
    return None


def launch_research_pipeline_run(
    *,
    idea: Dict[str, Any],
    config_name: str,
    run_id: str,
) -> Dict[str, Any]:
    env = _load_worker_environment()
    telemetry_block = {
        "database_url": env.database_public_url,
        "run_id": run_id,
        "webhook_url": env.telemetry_webhook_url,
        "webhook_token": env.telemetry_webhook_token,
    }
    idea_filename = f"{run_id}_idea.json"
    config_filename = config_name
    idea_text = json.dumps(idea, indent=2)
    config_text = _prepare_yaml_config(idea_filename=idea_filename, telemetry=telemetry_block)
    idea_b64 = _encode_multiline(idea_text)
    config_b64 = _encode_multiline(config_text)
    user_data = _build_user_data_script(
        env=env,
        idea_filename=idea_filename,
        idea_content_b64=idea_b64,
        config_filename=config_filename,
        config_content_b64=config_b64,
        run_id=run_id,
    )
    manager = AWSEC2Manager(region=env.aws_region)
    instance_id = manager.launch_instance(env=env, user_data=user_data, run_id=run_id)
    instance = manager.wait_for_instance_ready(instance_id=instance_id)
    launch_time = _instance_launch_time(instance)
    logger.debug("Launched EC2 instance %s for run %s: %s", instance_id, run_id, instance)
    hourly_cost = _lookup_instance_price(
        instance_type=env.instance_type,
        region_code=env.aws_region,
    )
    if hourly_cost is None:
        logger.warning(
            "Unable to determine on-demand price for instance_type=%s region=%s; defaulting to 0.",
            env.instance_type,
            env.aws_region,
        )
    return {
        "instance_id": instance_id,
        "instance_name": _extract_instance_name(instance),
        "instance_type": instance.get("InstanceType"),
        "public_ip": instance.get("PublicIpAddress"),
        "ssh_port": "22",
        "availability_zone": instance.get("Placement", {}).get("AvailabilityZone"),
        "launch_time": launch_time.isoformat() if launch_time else None,
        "costPerHr": hourly_cost if hourly_cost is not None else 0.0,
    }


def terminate_instance(*, instance_id: str) -> None:
    manager = AWSEC2Manager(region=_require_env("AWS_REGION"))
    manager.terminate_instance(instance_id=instance_id)


def fetch_instance_billing_summary(*, instance_id: str) -> dict[str, Any] | None:
    manager = AWSEC2Manager(region=_require_env("AWS_REGION"))
    try:
        instance = manager.describe_instance(instance_id=instance_id)
    except AWSEC2Error as exc:
        logger.warning("Failed to describe instance %s for billing summary: %s", instance_id, exc)
        return None
    launch_time = _instance_launch_time(instance)
    if not launch_time:
        return None
    now = datetime.now(timezone.utc)
    duration_seconds = max(0.0, (now - launch_time).total_seconds())
    hourly_cost = _lookup_instance_price(
        instance_type=cast(str, instance.get("InstanceType", "")),
        region_code=_require_env("AWS_REGION"),
    )
    estimated_amount = (
        round(hourly_cost * (duration_seconds / 3600), 6) if hourly_cost is not None else 0.0
    )
    return {
        "instance_id": instance_id,
        "instance_type": instance.get("InstanceType"),
        "state": instance.get("State", {}).get("Name"),
        "duration_seconds": duration_seconds,
        "hourly_cost_usd": hourly_cost,
        "estimated_amount_usd": estimated_amount,
        "launch_time": launch_time.isoformat(),
    }


LOG_UPLOAD_REQUIRED_ENVS = [
    "AWS_ACCESS_KEY_ID",
    "AWS_SECRET_ACCESS_KEY",
    "AWS_REGION",
    "AWS_S3_BUCKET_NAME",
]


def _gather_log_env(run_id: str) -> dict[str, str] | None:
    env_values: dict[str, str] = {"RUN_ID": run_id}
    missing: list[str] = []
    for name in LOG_UPLOAD_REQUIRED_ENVS:
        value = os.environ.get(name)
        if value:
            env_values[name] = value
        else:
            missing.append(name)
    public_db = os.environ.get("DATABASE_PUBLIC_URL")
    if public_db:
        env_values["DATABASE_PUBLIC_URL"] = public_db
        env_values["DATABASE_URL"] = os.environ.get("DATABASE_URL", public_db)
    else:
        missing.append("DATABASE_PUBLIC_URL")
    if missing:
        logger.info("Missing env vars for worker log upload: %s", ", ".join(sorted(set(missing))))
        return None
    return env_values


def _write_temp_key_file(raw_key: str) -> str:
    key_material = raw_key.replace("\\n", "\n").strip() + "\n"
    fd, path = tempfile.mkstemp(prefix="worker-key-", suffix=".pem")
    with os.fdopen(fd, "w") as handle:
        handle.write(key_material)
    os.chmod(path, 0o600)
    return path


def upload_worker_log_via_ssh(*, host: str, port: str | int, run_id: str) -> None:
    if not host or not port:
        logger.info("Skipping worker log upload for run %s; missing host/port.", run_id)
        return
    private_key = os.environ.get("WORKER_SSH_PRIVATE_KEY")
    if not private_key:
        logger.info("WORKER_SSH_PRIVATE_KEY is not configured; skipping worker log upload.")
        return
    env_values = _gather_log_env(run_id)
    if env_values is None:
        return
    key_path = _write_temp_key_file(private_key)
    remote_env = " ".join(f"{name}={shlex.quote(value)}" for name, value in env_values.items())
    remote_command = (
        "cd /workspace/AE-Scientist/research_pipeline && "
        "source .venv/bin/activate && "
        f"{remote_env} python upload_worker_log.py "
        "--log-path /workspace/research_pipeline.log --artifact-type run_log"
    )
    ssh_user = os.environ.get("WORKER_SSH_USERNAME", "ubuntu")
    ssh_command = [
        "ssh",
        "-i",
        key_path,
        "-o",
        "StrictHostKeyChecking=no",
        "-o",
        "UserKnownHostsFile=/dev/null",
        "-p",
        str(port),
        f"{ssh_user}@{host}",
        "bash",
        "-lc",
        shlex.quote(remote_command),
    ]
    try:
        result = subprocess.run(
            ssh_command,
            capture_output=True,
            text=True,
            timeout=180,
            check=False,
        )
        if result.returncode != 0:
            logger.warning(
                "Worker log upload via SSH failed for run %s (exit %s): %s",
                run_id,
                result.returncode,
                result.stderr.strip(),
            )
        elif result.stdout:
            logger.info("Worker log upload output for run %s: %s", run_id, result.stdout.strip())
    except Exception as exc:  # noqa: BLE001
        logger.exception("Error uploading worker log for run %s: %s", run_id, exc)
    finally:
        try:
            Path(key_path).unlink(missing_ok=True)
        except OSError:
            pass


REGION_LOCATIONS = {
    "us-east-1": "US East (N. Virginia)",
    "us-east-2": "US East (Ohio)",
    "us-west-1": "US West (N. California)",
    "us-west-2": "US West (Oregon)",
    "ca-central-1": "Canada (Central)",
    "sa-east-1": "South America (São Paulo)",
    "eu-central-1": "EU (Frankfurt)",
    "eu-central-2": "EU (Zurich)",
    "eu-west-1": "EU (Ireland)",
    "eu-west-2": "EU (London)",
    "eu-west-3": "EU (Paris)",
    "eu-north-1": "EU (Stockholm)",
    "eu-south-1": "EU (Milan)",
    "eu-south-2": "EU (Spain)",
    "af-south-1": "Africa (Cape Town)",
    "ap-south-1": "Asia Pacific (Mumbai)",
    "ap-south-2": "Asia Pacific (Hyderabad)",
    "ap-southeast-1": "Asia Pacific (Singapore)",
    "ap-southeast-2": "Asia Pacific (Sydney)",
    "ap-southeast-3": "Asia Pacific (Jakarta)",
    "ap-southeast-4": "Asia Pacific (Melbourne)",
    "ap-northeast-1": "Asia Pacific (Tokyo)",
    "ap-northeast-2": "Asia Pacific (Seoul)",
    "ap-northeast-3": "Asia Pacific (Osaka)",
    "ap-east-1": "Asia Pacific (Hong Kong)",
    "me-south-1": "Middle East (Bahrain)",
    "me-central-1": "Middle East (UAE)",
}


@lru_cache(maxsize=128)
def _lookup_instance_price(
    *, instance_type: str, region_code: str, operating_system: str = "Linux"
) -> float | None:
    location = REGION_LOCATIONS.get(region_code)
    if not location:
        logger.warning("No pricing location mapping for region %s", region_code)
        return None
    try:
        pricing = boto3.client("pricing", region_name="us-east-1")
        response = pricing.get_products(
            ServiceCode="AmazonEC2",
            Filters=[
                {"Type": "TERM_MATCH", "Field": "instanceType", "Value": instance_type},
                {"Type": "TERM_MATCH", "Field": "location", "Value": location},
                {"Type": "TERM_MATCH", "Field": "operatingSystem", "Value": operating_system},
                {"Type": "TERM_MATCH", "Field": "tenancy", "Value": "Shared"},
                {"Type": "TERM_MATCH", "Field": "capacitystatus", "Value": "Used"},
                {"Type": "TERM_MATCH", "Field": "preInstalledSw", "Value": "NA"},
            ],
            MaxResults=1,
        )
    except (ClientError, BotoCoreError) as exc:
        logger.warning(
            "Pricing lookup failed for instance_type=%s region=%s: %s",
            instance_type,
            region_code,
            exc,
        )
        return None
    price_list = response.get("PriceList")
    if not price_list:
        logger.warning(
            "Pricing lookup returned no results for instance_type=%s region=%s",
            instance_type,
            region_code,
        )
        return None
    try:
        price_data = json.loads(price_list[0])
        terms = price_data["terms"]["OnDemand"]
        for term in terms.values():
            for dimension in term["priceDimensions"].values():
                usd = dimension["pricePerUnit"]["USD"]
                return float(usd)
    except (KeyError, ValueError, TypeError) as exc:
        logger.warning(
            "Failed to parse pricing response for instance_type=%s region=%s: %s",
            instance_type,
            region_code,
            exc,
        )
        return None
    return None
