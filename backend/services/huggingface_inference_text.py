"""
Plain text generation for instruction / chat LMs on Hugging Face.

Primary path: huggingface_hub.InferenceClient.chat.completions (router / provider models
e.g. ``Qwen/Qwen2.5-1.5B-Instruct:featherless-ai``).

Fallback: classic ``POST /models/{id}`` text-generation API (often 404 for provider-qualified ids).

Separate from FinBERT (classification).
"""

from __future__ import annotations

import logging
from typing import Any

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)


def _normalize_message_content(content: Any) -> str:
    if content is None:
        return ""
    if isinstance(content, str):
        return content.strip()
    # Some completions return multipart content blocks
    if isinstance(content, list):
        parts: list[str] = []
        for block in content:
            if isinstance(block, dict):
                t = block.get("text") or block.get("content")
                if isinstance(t, str):
                    parts.append(t)
            elif isinstance(block, str):
                parts.append(block)
        return " ".join(parts).strip()
    return str(content).strip()


def _extract_generated_text(data: Any) -> str:
    if isinstance(data, list) and data:
        first = data[0]
        if isinstance(first, dict) and "generated_text" in first:
            return str(first["generated_text"]).strip()
        if isinstance(first, dict) and isinstance(first.get("summary_text"), str):
            return str(first["summary_text"]).strip()
    if isinstance(data, dict):
        if isinstance(data.get("generated_text"), str):
            return data["generated_text"].strip()
        lst = data.get("generated_texts")
        if isinstance(lst, list) and lst:
            return str(lst[0]).strip()
    raise ValueError("unexpected_hf_textgen_shape")


def _generate_via_inference_client_chat(
    prompt: str,
    *,
    model_id: str,
    max_new_tokens: int,
    temperature: float,
    token: str,
    timeout_s: float,
) -> str:
    from huggingface_hub import InferenceClient

    client = InferenceClient(api_key=token, timeout=timeout_s)
    completion = client.chat.completions.create(
        model=model_id,
        messages=[{"role": "user", "content": prompt}],
        max_tokens=max_new_tokens,
        temperature=temperature,
    )
    choices = getattr(completion, "choices", None) or []
    if not choices:
        raise RuntimeError("Hugging Face chat completion returned no choices.")
    msg = choices[0].message
    text = _normalize_message_content(getattr(msg, "content", None))
    if not text and msg is not None:
        text = _normalize_message_content(msg)
    if not text:
        raise RuntimeError("Hugging Face chat completion returned empty content.")
    return text


def _generate_via_legacy_rest(
    prompt: str,
    *,
    model_id: str,
    max_new_tokens: int,
    temperature: float,
    token: str,
    timeout_s: float,
) -> str:
    mid = model_id
    url = f"https://api-inference.huggingface.co/models/{mid}"
    headers = {"Authorization": f"Bearer {token}"}
    payload: dict[str, Any] = {
        "inputs": prompt,
        "parameters": {
            "max_new_tokens": max_new_tokens,
            "temperature": temperature,
            "return_full_text": False,
        },
    }
    with httpx.Client(timeout=timeout_s) as client:
        r = client.post(url, headers=headers, json=payload)
        r.raise_for_status()
        data = r.json()
    text = _extract_generated_text(data)
    if not text:
        raise RuntimeError("Hugging Face returned an empty completion.")
    return text


def hf_generate_instruction_text(
    prompt: str,
    *,
    model_id: str,
    max_new_tokens: int = 512,
    temperature: float = 0.25,
) -> str:
    """
    Prompt → assistant text via HF Hub (chat API first).

    Raises:
        RuntimeError: missing token or both paths failed.
    """
    token = (settings.huggingface_api_token or "").strip()
    if not token:
        raise RuntimeError("HUGGINGFACE_API_TOKEN (or HF_TOKEN) is not configured.")

    mid = (model_id or "").strip()
    if not mid:
        raise RuntimeError("HF instruction model id is empty.")

    timeout_s = max(60.0, float(settings.buysell_llm_timeout_seconds or 120))

    hub_err: str | None = None
    try:
        return _generate_via_inference_client_chat(
            prompt,
            model_id=mid,
            max_new_tokens=max_new_tokens,
            temperature=temperature,
            token=token,
            timeout_s=timeout_s,
        )
    except Exception as exc:  # noqa: BLE001
        hub_err = str(exc)[:400]
        logger.warning(
            "HF InferenceClient.chat failed for %s: %s; falling back to legacy REST.",
            mid,
            hub_err,
        )

    try:
        return _generate_via_legacy_rest(
            prompt,
            model_id=mid,
            max_new_tokens=max_new_tokens,
            temperature=temperature,
            token=token,
            timeout_s=timeout_s,
        )
    except Exception as exc:  # noqa: BLE001
        rest_msg = str(exc)[:400]
        raise RuntimeError(
            f"HF text generation failed for '{mid}'. "
            f"InferenceClient: {hub_err or 'unknown'}. REST: {rest_msg}"
        ) from exc
