"""Shared paths, logging and the Claude Code CLI wrapper."""
import json, os, re, subprocess, sys, time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RUNS = ROOT / "runs"
CLAUDE = os.path.expanduser("~/.local/bin/claude")
CLAUDE_CWD = ROOT / "runs" / ".claude-cwd"  # empty, so no project CLAUDE.md is picked up


def log(*a):
    print(time.strftime("[%H:%M:%S]"), *a, flush=True)


def claude(model, system, user, web=False, timeout=1500, retries=2):
    CLAUDE_CWD.mkdir(parents=True, exist_ok=True)
    tools = "WebSearch,WebFetch" if web else ""
    args = [CLAUDE, "-p", "--output-format", "json", "--model", model, "--tools", tools,
            "--strict-mcp-config", "--setting-sources", "", "--no-session-persistence",
            "--system-prompt", system]
    if web:
        args += ["--allowedTools", tools]
    env = {k: v for k, v in os.environ.items() if not k.startswith("CLAUDE_CODE") and k != "CLAUDECODE"}
    err = None
    for attempt in range(retries + 1):
        try:
            p = subprocess.run(args, input=user, capture_output=True, text=True,
                               cwd=CLAUDE_CWD, timeout=timeout, env=env)
            out = json.loads(p.stdout)
            if out.get("is_error"):
                raise RuntimeError(str(out.get("result") or out.get("subtype"))[:400])
            return out["result"]
        except Exception as e:
            err = e
            log(f"claude {model} attempt {attempt + 1} failed: {str(e)[:300]}")
            time.sleep(30 * (attempt + 1))
    raise RuntimeError(f"claude {model} failed: {err}")


def parse_json(text):
    fenced = re.search(r"```(?:json)?\s*([\s\S]*?)```", text)
    raw = fenced.group(1) if fenced else text
    return json.loads(raw[raw.index("{"): raw.rindex("}") + 1])


def claude_json(model, system, user, **kw):
    """Asks once more with the parse error when a reply is not valid JSON."""
    reply = claude(model, system, user, **kw)
    try:
        return parse_json(reply)
    except ValueError as e:
        log(f"bad JSON from {model}: {e}; retrying")
        return parse_json(claude(model, system, user + "\n\nBalas HANYA dengan satu objek JSON valid.", **kw))


def run_dir(slug):
    d = RUNS / slug
    d.mkdir(parents=True, exist_ok=True)
    return d


def load(path):
    return json.loads(Path(path).read_text())


def save(path, obj):
    Path(path).write_text(json.dumps(obj, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    sys.exit("library module")
