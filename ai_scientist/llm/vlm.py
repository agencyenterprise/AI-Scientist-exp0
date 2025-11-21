import base64
import io
import json
import logging
import re
from typing import Any, cast

import anthropic
import backoff
import openai
from PIL import Image

from .query import backend_openai
from .query.utils import FunctionSpec, PromptType, compile_prompt_to_md, get_openai_base_url
from .token_tracker import track_token_usage

logger = logging.getLogger("ai-scientist")

MAX_NUM_TOKENS = 4096

AVAILABLE_VLMS = [
    "gpt-4o-2024-05-13",
    "gpt-4o-2024-08-06",
    "gpt-4o-2024-11-20",
    "gpt-4o-mini-2024-07-18",
    "o3-mini",
    "gpt-5",
]


def encode_image_to_base64(image_path: str) -> str:
    """Convert an image to base64 string."""
    with Image.open(image_path) as img:
        # Convert RGBA to RGB if necessary
        if img.mode == "RGBA":
            img = img.convert("RGB")

        # Save to bytes

        buffer = io.BytesIO()
        img.save(buffer, format="JPEG")
        image_bytes = buffer.getvalue()

    return base64.b64encode(image_bytes).decode("utf-8")


@track_token_usage
def make_vlm_call(
    client: openai.OpenAI | anthropic.Anthropic,
    model: str,
    temperature: float,
    system_message: str,
    prompt: list[dict[str, Any]],
) -> Any:  # noqa: ANN401
    if "gpt" in model or model == "gpt-5":
        # GPT-5 uses max_completion_tokens instead of max_tokens
        # and only supports temperature=1
        if model == "gpt-5":
            assert isinstance(client, openai.OpenAI)
            return client.chat.completions.create(
                model=model,
                messages=cast(Any, [{"role": "system", "content": system_message}] + prompt),
                temperature=1,  # GPT-5 only supports temperature=1
                max_completion_tokens=MAX_NUM_TOKENS,
            )
        else:
            assert isinstance(client, openai.OpenAI)
            return client.chat.completions.create(
                model=model,
                messages=cast(Any, [{"role": "system", "content": system_message}] + prompt),
                temperature=temperature,
                max_tokens=MAX_NUM_TOKENS,
            )
    else:
        raise ValueError(f"Model {model} not supported.")


@backoff.on_exception(
    backoff.expo,
    (
        openai.RateLimitError,
        openai.APITimeoutError,
    ),
)
def get_response_from_vlm(
    msg: str,
    image_paths: str | list[str],
    client: openai.OpenAI,
    model: str,
    system_message: str,
    temperature: float,
    print_debug: bool = False,
    msg_history: list[dict[str, Any]] | None = None,
    max_images: int = 25,
) -> tuple[str, list[dict[str, Any]]]:
    """Get response from vision-language model."""
    if msg_history is None:
        msg_history = []

    if model in AVAILABLE_VLMS:
        # Convert single image path to list for consistent handling
        if isinstance(image_paths, str):
            image_paths = [image_paths]

        # Create content list starting with the text message
        content: list[dict[str, Any]] = [{"type": "text", "text": msg}]

        # Add each image to the content list
        for image_path in image_paths[:max_images]:
            base64_image = encode_image_to_base64(image_path)
            content.append(
                {
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:image/jpeg;base64,{base64_image}",
                        "detail": "low",
                    },
                }
            )
        # Construct message with all images
        new_msg_history = msg_history + [{"role": "user", "content": content}]

        response = make_vlm_call(
            client=client,
            model=model,
            temperature=temperature,
            system_message=system_message,
            prompt=new_msg_history,
        )

        content_str = response.choices[0].message.content or ""
        new_msg_history = new_msg_history + [{"role": "assistant", "content": content_str}]
    else:
        raise ValueError(f"Model {model} not supported.")

    if print_debug:
        logger.debug("")
        logger.debug("*" * 20 + " VLM START " + "*" * 20)
        for j, message in enumerate(new_msg_history):
            logger.debug(f'{j}, {message["role"]}: {message["content"]}')
        logger.debug(content_str)
        logger.debug("*" * 21 + " VLM END " + "*" * 21)
        logger.debug("")

    return content_str, new_msg_history


def create_vlm_client(model: str) -> tuple[openai.OpenAI, str]:
    """Create client for vision-language model."""
    if model in [
        "gpt-4o-2024-05-13",
        "gpt-4o-2024-08-06",
        "gpt-4o-2024-11-20",
        "gpt-4o-mini-2024-07-18",
        "o3-mini",
        "gpt-5",
    ]:
        logger.info(f"Using OpenAI API with model {model}.")
        base_url = get_openai_base_url()
        if base_url:
            logger.info(f"Using custom OpenAI base_url: {base_url}")
        return openai.OpenAI(base_url=base_url), model
    else:
        raise ValueError(f"Model {model} not supported.")


def vlm_query(
    system_message: PromptType | None,
    user_message: PromptType | None,
    model: str,
    temperature: float,
    max_tokens: int | None = None,
    func_spec: FunctionSpec | None = None,
    **model_kwargs: object,
) -> str | dict:
    """
    Vision-language query helper with the same external signature as `llm.query.query`,
    but restricted to VLM-capable OpenAI models defined in `AVAILABLE_VLMS`.
    """
    if model not in AVAILABLE_VLMS:
        raise ValueError(f"Model {model} is not a supported vision-language model.")

    # Merge caller-provided kwargs with core generation parameters
    merged_kwargs: dict[str, object] = {**model_kwargs, "model": model, "temperature": temperature}
    # For non-o1 models, use max_tokens; o1-style models are not in AVAILABLE_VLMS.
    merged_kwargs["max_tokens"] = max_tokens

    compiled_system = compile_prompt_to_md(system_message) if system_message is not None else None
    compiled_user = compile_prompt_to_md(user_message) if user_message is not None else None
    logger.debug("*" * 20 + " VLM_QUERY CALL " + "*" * 20)
    logger.debug(f"Model: {model}")
    logger.debug(f"Temperature: {temperature}")
    logger.debug(f"Max tokens: {max_tokens}")
    logger.debug(f"Has func_spec: {func_spec.name if func_spec is not None else None}")
    logger.debug(f"System message: {system_message}")
    logger.debug(f"User message: {user_message}")
    logger.debug("*" * 24 + " END VLM_QUERY CALL " + "*" * 24)
    logger.debug(f"Compiled system: {compiled_system}")
    logger.debug(f"Compiled user: {compiled_user}")

    output, _req_time, _in_tok, _out_tok, _info = backend_openai.query(
        system_message=compiled_system,
        user_message=compiled_user,
        func_spec=func_spec,
        **merged_kwargs,
    )
    return output


def extract_json_between_markers_vlm(llm_output: str) -> dict[Any, Any] | None:
    # Regular expression pattern to find JSON content between ```json and ```
    json_pattern = r"```json(.*?)```"
    matches = re.findall(json_pattern, llm_output, re.DOTALL)

    if not matches:
        # Fallback: Try to find any JSON-like content in the output
        json_pattern = r"\{.*?\}"
        matches = re.findall(json_pattern, llm_output, re.DOTALL)

    for json_string in matches:
        json_string = json_string.strip()
        try:
            parsed_json: dict[Any, Any] | list[Any] = json.loads(json_string)
            if isinstance(parsed_json, dict):
                return parsed_json
        except json.JSONDecodeError:
            # Attempt to fix common JSON issues
            try:
                # Remove invalid control characters
                json_string_clean = re.sub(r"[\x00-\x1F\x7F]", "", json_string)
                parsed_json = json.loads(json_string_clean)
                if isinstance(parsed_json, dict):
                    return parsed_json
            except json.JSONDecodeError:
                continue  # Try next match

    return None  # No valid JSON found
