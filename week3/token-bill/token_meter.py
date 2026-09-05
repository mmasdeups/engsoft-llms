"""LiteLLM proxy callback: append one JSON line per LLM call.

Run the proxy from the directory that contains this file, and make sure the
directory is on PYTHONPATH so LiteLLM can import it:

    cd week3/token-bill
    PYTHONPATH="$PWD" METER_LOG=part1-baseline.jsonl \
        litellm --config litellm_part1.yaml --port 4000

Every request through the proxy adds a record to $METER_LOG.
Read it back with meter_report.py.
"""

import json
import os
import time

from litellm.integrations.custom_logger import CustomLogger

LOG_PATH = os.environ.get("METER_LOG", "meter.jsonl")


def _usage_dict(response_obj):
    """Pull usage out of whatever shape LiteLLM hands us."""
    usage = getattr(response_obj, "usage", None)
    if usage is None and isinstance(response_obj, dict):
        usage = response_obj.get("usage")
    if usage is None:
        return {}
    if hasattr(usage, "model_dump"):
        try:
            return usage.model_dump()
        except Exception:
            pass
    if isinstance(usage, dict):
        return dict(usage)
    return {
        key: getattr(usage, key, None)
        for key in ("prompt_tokens", "completion_tokens", "total_tokens")
    }


def _write(record):
    with open(LOG_PATH, "a") as handle:
        handle.write(json.dumps(record) + "\n")
        handle.flush()


class TokenMeter(CustomLogger):
    async def async_log_success_event(self, kwargs, response_obj, start_time, end_time):
        usage = _usage_dict(response_obj)
        _write(
            {
                "ts": time.time(),
                "ok": True,
                "model": kwargs.get("model"),
                "prompt_tokens": usage.get("prompt_tokens"),
                "completion_tokens": usage.get("completion_tokens"),
                "total_tokens": usage.get("total_tokens"),
            }
        )

    async def async_log_failure_event(self, kwargs, response_obj, start_time, end_time):
        _write(
            {
                "ts": time.time(),
                "ok": False,
                "model": kwargs.get("model"),
                "error": str(response_obj)[:300],
            }
        )


# LiteLLM looks for this instance by name: token_meter.proxy_handler_instance
proxy_handler_instance = TokenMeter()
