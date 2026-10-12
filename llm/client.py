from __future__ import annotations

import json
import os
import re
import statistics
from pathlib import Path
from typing import Any, Callable

import requests
import yaml
from dotenv import load_dotenv

from observability.recorder import RunRecord
from schemas.output import TicketClassification

load_dotenv()

_MODELS_PATH = Path(__file__).parent / "models.yml"
_API_URL = "https://api.together.xyz/v1/chat/completions"


def _load_model_config(key: str | None = None) -> dict[str, Any]:
    data = yaml.safe_load(_MODELS_PATH.read_text())
    resolved_key = key or data["default"]
    return data["models"][resolved_key]


def call(
    user_prompt: str,
    system_prompt: str,
    model_key: str | None = None,
) -> tuple[TicketClassification | None, RunRecord]:
    record = RunRecord(meta={"model_key": model_key or "default"})
    api_key = os.environ["TOGETHER_API_KEY"]
    config = _load_model_config(model_key)

    # --- request_prep ---
    record.start_interval("request_prep")
    payload: dict[str, Any] = {
        "model": config["id"],
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "max_tokens": config["max_tokens"],
        "temperature": config["temperature"],
        "response_format": {"type": "json_object"},
    }
    record.end_interval("request_prep")

    # --- model_call ---
    record.start_interval("model_call")
    try:
        resp = requests.post(
            _API_URL,
            headers={"Authorization": f"Bearer {api_key}"},
            json=payload,
            timeout=60,
        )
        resp.raise_for_status()
    except requests.RequestException as exc:
        record.end_interval("model_call")
        record.fail(f"http_error: {exc}")
        record.save()
        return None, record
    record.end_interval("model_call")

    # --- response_parse ---
    record.start_interval("response_parse")
    raw_text = resp.json()["choices"][0]["message"]["content"]
    try:
        raw_dict = json.loads(raw_text)
    except json.JSONDecodeError as exc:
        record.end_interval("response_parse")
        record.fail(f"json_decode: {exc}")
        record.save()
        return None, record
    record.end_interval("response_parse")

    # --- schema_validate ---
    record.start_interval("schema_validate")
    try:
        result = TicketClassification.model_validate(raw_dict)
    except Exception as exc:
        record.end_interval("schema_validate")
        record.fail(f"schema_validate: {exc}")
        record.save()
        return None, record
    record.end_interval("schema_validate")

    record.complete()
    record.save()
    return result, record


def _extract_json(text: str) -> dict[str, Any]:
    """Parse JSON from model output; tolerates markdown code fences."""
    text = text.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if match:
        return json.loads(match.group())
    raise ValueError("no JSON object found in response")


def call_with_tools(
    user_prompt: str,
    system_prompt: str,
    tools: list[dict[str, Any]],
    tool_executor: Callable[[str, dict[str, Any]], Any],
    model_key: str | None = None,
    max_rounds: int = 6,
) -> tuple[TicketClassification | None, RunRecord]:
    record = RunRecord(meta={"model_key": model_key or "default", "mode": "tool_loop"})
    api_key = os.environ["TOGETHER_API_KEY"]
    config = _load_model_config(model_key)

    # --- request_prep ---
    record.start_interval("request_prep")
    messages: list[dict[str, Any]] = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]
    base_payload: dict[str, Any] = {
        "model": config["id"],
        "max_tokens": config["max_tokens"],
        "temperature": config["temperature"],
        "tools": tools,
        "tool_choice": "auto",
    }
    record.end_interval("request_prep")

    # --- tool loop ---
    for round_num in range(max_rounds):
        record.start_interval(f"model_call_r{round_num}")
        try:
            resp = requests.post(
                _API_URL,
                headers={"Authorization": f"Bearer {api_key}"},
                json={**base_payload, "messages": messages},
                timeout=60,
            )
            resp.raise_for_status()
        except requests.RequestException as exc:
            record.end_interval(f"model_call_r{round_num}")
            record.fail(f"http_error: {exc}")
            record.save()
            return None, record
        record.end_interval(f"model_call_r{round_num}")

        choice = resp.json()["choices"][0]
        assistant_msg = choice["message"]
        messages.append(assistant_msg)

        if choice["finish_reason"] == "stop":
            break

        if choice["finish_reason"] == "tool_calls":
            record.start_interval(f"tool_exec_r{round_num}")
            for tc in assistant_msg.get("tool_calls", []):
                name = tc["function"]["name"]
                args = json.loads(tc["function"]["arguments"])
                result = tool_executor(name, args)
                messages.append({
                    "role": "tool",
                    "tool_call_id": tc["id"],
                    "content": json.dumps(result),
                })
            record.end_interval(f"tool_exec_r{round_num}")

    # --- response_parse ---
    record.start_interval("response_parse")
    final_content = ""
    for msg in reversed(messages):
        if msg.get("role") == "assistant" and msg.get("content"):
            final_content = msg["content"]
            break
    try:
        raw_dict = _extract_json(final_content)
    except (ValueError, json.JSONDecodeError) as exc:
        record.end_interval("response_parse")
        record.fail(f"json_decode: {exc}")
        record.save()
        return None, record
    record.end_interval("response_parse")

    # --- schema_validate ---
    record.start_interval("schema_validate")
    try:
        result = TicketClassification.model_validate(raw_dict)
    except Exception as exc:
        record.end_interval("schema_validate")
        record.fail(f"schema_validate: {exc}")
        record.save()
        return None, record
    record.end_interval("schema_validate")

    record.complete()
    record.save()
    return result, record


def baseline_run(
    user_prompt: str,
    system_prompt: str,
    model_key: str | None = None,
    n: int = 5,
) -> dict[str, Any]:
    durations: list[float] = []
    failures = 0

    for _ in range(n):
        result, record = call(user_prompt, system_prompt, model_key)
        if result is None:
            failures += 1
        mc = next(
            (iv for iv in record.intervals if iv.name == "model_call" and iv.duration_ms is not None),
            None,
        )
        if mc and mc.duration_ms is not None:
            durations.append(mc.duration_ms)

    mean = statistics.mean(durations) if durations else 0.0
    spread = statistics.stdev(durations) if len(durations) > 1 else 0.0

    return {
        "n": n,
        "model_call_mean_ms": round(mean, 2),
        "model_call_spread_ms": round(spread, 2),
        "parse_failure_rate": round(failures / n, 3),
        "failures": failures,
        "durations_ms": [round(d, 2) for d in durations],
    }
