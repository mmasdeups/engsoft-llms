# Week 3 · Exercise 2 — The Token Bill

Measuring two claims: that a mounted MCP server's registry costs tokens on every
request whether or not it is used, and that a CLI road through a task is far
cheaper than a browser road through the same task.

Setup: Windows + WSL (Ubuntu), RTX 5080.
Part 1 model: `qwen3:14b` via Ollama. Part 2 model: `gpt-4.1-mini` via
OpenRouter. Every call in both parts goes through one LiteLLM proxy that logs
usage to JSONL.

## Files

| file | what it is |
| --- | --- |
| `token_meter.py` | LiteLLM callback; one JSON line per call |
| `meter_report.py` | turns a log into the numbers below |
| `litellm_part1.yaml` | proxy config, local Ollama |
| `litellm_part2.yaml` | proxy config, OpenRouter |
| `opencode.json` | browser-road agent: proxy provider + Playwright MCP |
| `extra_tools.py` | five fat-description tools for Part 1 run 4 |
| `skills/moodle-cli/` | skill for the CLI road |
| `*.jsonl` | raw meter logs, one per run |

## The num_ctx trap

Ollama's default context is 4096. If the prompt exceeds it, Ollama truncates
**silently** and the reported `prompt_tokens` describes the truncated prompt —
the measurement becomes fiction without any error. Build an explicit variant
before measuring anything:

```bash
printf 'FROM qwen3:14b\nPARAMETER num_ctx 16384\n' > Modelfile
ollama create qwen3-14b-16k -f Modelfile
```

If Ollama runs on Windows rather than inside WSL, `localhost:11434` only
resolves from WSL under mirrored networking; otherwise use the Windows host IP.

## Runbook — Part 1

One proxy restart per run, with a distinct `METER_LOG`, so each number is
unambiguous. Point both demo agents at the proxy:

```
OPENAI_BASE_URL=http://localhost:4000/v1
OPENAI_API_KEY=anything
MODEL=meter
```

```bash
cd week3/token-bill
PYTHONPATH="$PWD" METER_LOG=part1-baseline.jsonl \
    litellm --config litellm_part1.yaml --port 4000
```

`PYTHONPATH` matters: LiteLLM imports `token_meter` by name, and a console
entry point does not put the working directory on `sys.path`.

| run | log | agent | prompt |
| --- | --- | --- | --- |
| 1 baseline, no MCP | `part1-baseline.jsonl` | `02-give-the-llm-hands` | a simple question |
| 2 mounted + used | `part1-used.jsonl` | `agent_with_mcp.py` | top speed of the Pallet Pup |
| 3 mounted + unused | `part1-unused.jsonl` | `agent_with_mcp.py` | capital of France |
| 4 unused, 6 tools | `part1-unused-6.jsonl` | `agent_with_mcp.py` | capital of France |

Then:

```bash
python meter_report.py part1-*.jsonl
```

Take `first_call_prompt_tokens` from each.

### Results — Part 1

| run | prompt_tokens (first call) |
| --- | --- |
| baseline, no MCP | |
| server mounted, used | |
| server mounted, NOT used | |
| unused, +5 tools | |

Registry cost = (mounted, unused) − baseline = ____ tokens.
At 10 servers × 50 turns: ____ tokens paid for nothing.

Why the unused server still costs:

> _one sentence here_

## Runbook — Part 2

```bash
export OPENROUTER_API_KEY=sk-or-...
cd week3/token-bill
PYTHONPATH="$PWD" METER_LOG=cli-road.jsonl \
    litellm --config litellm_part2.yaml --port 4000
```

**Road one — CLI.** `04-minimal-cli-agent`, `.env` pointed at the proxy, with
`skills/moodle-cli/` reachable. Task: post `hello from my CLI agent` to the
forum thread. Approve its commands.

**Road two — browser.** Restart the proxy with `METER_LOG=browser-road.jsonl`.
Prepare Playwright inside WSL once:

```bash
npx playwright install --with-deps chromium
opencode mcp list          # expect: playwright, connected
```

Headed under WSLg; add `--headless` to the MCP args if there is no display.
Task: open Àrtemis, reach the same thread, post `hello from my browser agent`.

```bash
python meter_report.py cli-road.jsonl browser-road.jsonl
```

### Results — Part 2

| road | calls | total tokens |
| --- | --- | --- |
| CLI | | |
| browser (Playwright MCP) | | |

Ratio: ____ ×

Forum comments: _links here_

Why the browser road costs what it does, and one task where it is still right:

> _two sentences here_
