"""Validation utilities for data and requests."""

import json
from typing import Any, Dict


def validate_json_content(content: str) -> Dict[str, Any]:
    """Validate and parse JSON content with fallback extraction."""
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        # Attempt basic brace-extraction fallback
        try:
            start = content.find("{")
            end = content.rfind("}")
            if start != -1 and end != -1 and end > start:
                return json.loads(content[start : end + 1])
        except json.JSONDecodeError as exc:
            raise RuntimeError(f"Model did not return valid JSON: {exc}") from exc
    
    # If parsing still fails, raise a generic error
    raise RuntimeError("Model did not return valid JSON.")


def format_input_payload(agent_input: Dict[str, Any]) -> str:
    """Format agent input as a compact JSON string for prompts."""
    return json.dumps(agent_input, ensure_ascii=False, indent=2)
