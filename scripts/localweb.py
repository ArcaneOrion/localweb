# /// script
# dependencies = [
#   "fastapi>=0.115",
#   "uvicorn>=0.30",
# ]
# ///
import argparse
import asyncio
import fcntl
import hashlib
import json
import re
import secrets
import shlex
import shutil
import socket
import sys
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


SCHEMA_VERSION = 1
DEFAULT_SESSION = "cli-main"
DEFAULT_STATE = "idle"
MAX_PANEL_INPUT_CHARS = 20_000


def now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def skill_root() -> Path:
    return Path(__file__).resolve().parents[1]


def shell_source_dir() -> Path:
    return skill_root() / "assets" / "shell"


def learn_source_dir() -> Path:
    return skill_root() / "learn"


def learn_template_path() -> Path:
    return learn_source_dir() / "templates" / "lesson.html"


def resolve_project(project: str | None) -> Path:
    return Path(project).expanduser().resolve() if project else Path.cwd().resolve()


def localweb_dir(project: Path) -> Path:
    return project / ".localweb"


def state_path(project: Path) -> Path:
    return localweb_dir(project) / "state.json"


def events_path(project: Path) -> Path:
    return localweb_dir(project) / "events.jsonl"


def inbox_path(project: Path) -> Path:
    return localweb_dir(project) / "inbox" / "events.jsonl"


def shell_dir(project: Path) -> Path:
    return localweb_dir(project) / "shell"


def panels_dir(project: Path) -> Path:
    return localweb_dir(project) / "panels"


def assets_dir(project: Path) -> Path:
    return localweb_dir(project) / "assets"


def generated_assets_dir(project: Path) -> Path:
    return assets_dir(project) / "generated"


def safe_id(value: str) -> str:
    cleaned = slug_id(value)
    if not cleaned:
        raise SystemExit("id must contain at least one letter, digit, '_' or '-'")
    return cleaned


def slug_id(value: str) -> str:
    return re.sub(r"[^a-zA-Z0-9_-]+", "-", value.strip()).strip("-")


def read_json(path: Path, default: dict[str, Any]) -> dict[str, Any]:
    if not path.exists():
        return default.copy()
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise SystemExit(f"Invalid JSON at {path}: {exc}") from exc


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + f".{uuid.uuid4().hex}.tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp.replace(path)


def write_jsonl_atomic(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + f".{uuid.uuid4().hex}.tmp")
    tmp.write_text(
        "".join(json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n" for row in rows),
        encoding="utf-8",
    )
    tmp.replace(path)


def lock_path(path: Path) -> Path:
    return path.with_suffix(path.suffix + ".lock")


def with_jsonl_lock(path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)
    lock = lock_path(path).open("w", encoding="utf-8")
    fcntl.flock(lock, fcntl.LOCK_EX)
    return lock


def append_jsonl(path: Path, obj: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with with_jsonl_lock(path) as lock:
        try:
            with path.open("a", encoding="utf-8") as fh:
                fh.write(json.dumps(obj, ensure_ascii=False, separators=(",", ":")) + "\n")
        finally:
            fcntl.flock(lock, fcntl.LOCK_UN)


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    out: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            value = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(value, dict):
            out.append(value)
    return out


def default_state() -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "session_id": DEFAULT_SESSION,
        "write_token": secrets.token_urlsafe(32),
        "title": "LocalWeb",
        "status": DEFAULT_STATE,
        "active_panel": "panels/main.html",
        "active_choice_id": None,
        "updated_at": now_iso(),
        "context": [
            {"label": "Project", "value": "Current working directory"},
            {"label": "Control", "value": "CLI terminal"},
            {"label": "Panel", "value": "panels/main.html"},
        ],
        "choices": [],
    }


def default_panel_html() -> str:
    return """<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>LocalWeb Panel</title>
<style>
  :root {
    color-scheme: dark;
    --ink: #29465d;
    --panel: #31536d;
    --yellow: #ffd43b;
    --cream: #fff8d6;
    --cyan: #35d8ff;
    --line: #07111b;
  }
  * { box-sizing: border-box; }
  html, body {
    margin: 0;
    min-height: 100%;
    background:
      repeating-linear-gradient(90deg, rgba(255, 248, 214, .14) 0 1px, transparent 1px 72px),
      repeating-linear-gradient(0deg, rgba(53, 216, 255, .11) 0 1px, transparent 1px 72px),
      var(--ink);
    color: var(--cream);
  }
  body {
    display: grid;
    place-items: center;
    padding: clamp(18px, 5vw, 64px);
    font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
  }
  main {
    width: min(980px, 100%);
    border: 4px solid var(--line);
    background: var(--panel);
    box-shadow: 10px 10px 0 var(--line);
    padding: clamp(24px, 5vw, 56px);
  }
  .eyebrow {
    display: inline-block;
    background: var(--yellow);
    color: var(--line);
    border: 3px solid var(--line);
    padding: 6px 10px;
    font-weight: 900;
    text-transform: uppercase;
  }
  h1 {
    margin: 22px 0 14px;
    color: var(--yellow);
    font-size: clamp(42px, 8vw, 96px);
    line-height: .88;
    letter-spacing: 0;
    text-transform: uppercase;
  }
  p { max-width: 68ch; font-size: clamp(16px, 2vw, 22px); line-height: 1.6; }
  .grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 12px; margin-top: 28px; }
  .cell { border: 3px solid var(--line); background: #fff8d6; color: var(--line); padding: 14px; min-height: 88px; }
  .cell strong { display: block; font-size: 24px; color: var(--line); }
  .cell span { display: block; margin-top: 8px; font-weight: 700; }
  @media (max-width: 720px) { .grid { grid-template-columns: 1fr; } }
</style>
</head>
<body>
<main>
  <div class="eyebrow" data-lw-text="eyebrow">Local visual deck online</div>
  <h1 data-lw-text="headline">LocalWeb</h1>
  <p data-lw-text="summary">Generate or register an HTML panel from the CLI to replace this default view with a visual explanation, diagram, comparison, report, or interactive context card.</p>
  <section class="grid" aria-label="Runtime contract">
    <div class="cell"><strong>01</strong><span>CLI owns context</span></div>
    <div class="cell"><strong>02</strong><span>Web renders panels</span></div>
    <div class="cell"><strong>03</strong><span>Inputs return by wait</span></div>
  </section>
</main>
</body>
</html>
"""


def ensure_layout(project: Path) -> None:
    for path in (
        localweb_dir(project),
        panels_dir(project),
        localweb_dir(project) / "inbox",
        assets_dir(project),
        generated_assets_dir(project),
        shell_dir(project),
    ):
        path.mkdir(parents=True, exist_ok=True)


def copy_file(src: Path, dst: Path, force: bool) -> bool:
    if dst.exists() and not force:
        return False
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)
    return True


def shell_supports_write_token(project: Path) -> bool:
    app_js = shell_dir(project) / "app.js"
    if not app_js.exists():
        return False
    try:
        content = app_js.read_text(encoding="utf-8")
    except OSError:
        return False
    return "x-localweb-token" in content and "write_token" in content


def require_current_shell(project: Path) -> None:
    if shell_supports_write_token(project):
        return
    raise SystemExit(
        "LocalWeb shell assets are missing write-token support. "
        f"Run: uv run scripts/localweb.py init --project {project} --shell-only"
    )


def copy_shell_assets(project: Path, force: bool) -> tuple[list[str], list[str]]:
    created: list[str] = []
    preserved: list[str] = []
    src_shell = shell_source_dir()
    if not src_shell.exists():
        raise SystemExit(f"Missing shell assets: {src_shell}")
    for src in src_shell.iterdir():
        if src.is_file():
            dst = shell_dir(project) / src.name
            if copy_file(src, dst, force):
                created.append(str(dst))
            else:
                preserved.append(str(dst))
    return created, preserved


def init_project(project: Path, force: bool = False, shell_only: bool = False) -> dict[str, Any]:
    if shell_only:
        require_initialized(project)

    ensure_layout(project)
    created: list[str] = []
    preserved: list[str] = []

    if shell_only:
        shell_created, shell_preserved = copy_shell_assets(project, force=True)
        created.extend(shell_created)
        preserved.extend(shell_preserved)
        append_jsonl(
            events_path(project),
            {
                "type": "shell_refreshed",
                "project_root": str(project),
                "ts": now_iso(),
            },
        )
        return {
            "status": "ok",
            "project_root": str(project),
            "localweb_dir": str(localweb_dir(project)),
            "created": created,
            "preserved": preserved,
            "next_command": f"uv run scripts/localweb.py serve --project {project} --port 8765",
        }

    defaults: list[tuple[Path, str]] = [
        (state_path(project), json.dumps(default_state(), ensure_ascii=False, indent=2) + "\n"),
        (events_path(project), ""),
        (inbox_path(project), ""),
        (panels_dir(project) / "main.html", default_panel_html()),
    ]
    for path, content in defaults:
        if path.exists() and not force:
            preserved.append(str(path))
            continue
        path.write_text(content, encoding="utf-8")
        created.append(str(path))

    shell_created, shell_preserved = copy_shell_assets(project, force)
    created.extend(shell_created)
    preserved.extend(shell_preserved)

    append_jsonl(
        events_path(project),
        {
            "type": "initialized",
            "project_root": str(project),
            "ts": now_iso(),
        },
    )
    return {
        "status": "ok",
        "project_root": str(project),
        "localweb_dir": str(localweb_dir(project)),
        "created": created,
        "preserved": preserved,
        "next_command": f"uv run scripts/localweb.py serve --project {project} --port 8765",
    }


def require_initialized(project: Path) -> None:
    if not state_path(project).exists():
        raise SystemExit(f"{localweb_dir(project)} is not initialized. Run: localweb.py init --project {project}")


def load_state(project: Path) -> dict[str, Any]:
    state = read_json(state_path(project), default_state())
    if state.get("schema_version") != SCHEMA_VERSION:
        state["schema_version"] = SCHEMA_VERSION
    if not state.get("write_token"):
        state["write_token"] = secrets.token_urlsafe(32)
        write_json(state_path(project), state)
    return state


def save_state(project: Path, state: dict[str, Any], event_type: str = "state_updated") -> None:
    state["updated_at"] = now_iso()
    write_json(state_path(project), state)
    append_jsonl(
        events_path(project),
        {
            "type": event_type,
            "status": state.get("status"),
            "active_panel": state.get("active_panel"),
            "active_choice_id": state.get("active_choice_id"),
            "ts": now_iso(),
        },
    )


def parse_context(items: list[str] | None) -> list[dict[str, str]] | None:
    if not items:
        return None
    context: list[dict[str, str]] = []
    for item in items:
        if "=" in item:
            label, value = item.split("=", 1)
        elif ":" in item:
            label, value = item.split(":", 1)
        else:
            label, value = "Context", item
        context.append({"label": label.strip(), "value": value.strip()})
    return context


def parse_options(options: list[str]) -> list[dict[str, str]]:
    parsed: list[dict[str, str]] = []
    for raw in options:
        if "=" in raw:
            opt_id, label = raw.split("=", 1)
        elif ":" in raw:
            opt_id, label = raw.split(":", 1)
        else:
            opt_id, label = raw, raw
        opt_id = opt_id.strip()
        label = label.strip()
        if not opt_id or not label:
            raise SystemExit(f"Invalid --option value: {raw!r}. Use A=Label.")
        parsed.append({"id": opt_id, "label": label})
    return parsed


def print_json(obj: dict[str, Any]) -> None:
    print(json.dumps(obj, ensure_ascii=False, indent=2))


def read_lesson(path: Path) -> dict[str, Any]:
    if not path.exists() or not path.is_file():
        raise SystemExit(f"Lesson file not found: {path}")
    try:
        lesson = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise SystemExit(f"Invalid lesson JSON at {path}: {exc}") from exc
    if not isinstance(lesson, dict):
        raise SystemExit("Lesson JSON must be an object")
    if not str(lesson.get("title") or "").strip():
        raise SystemExit("Lesson JSON must include a non-empty title")
    return lesson


def json_for_script(data: Any) -> str:
    return (
        json.dumps(data, ensure_ascii=False, separators=(",", ":"))
        .replace("<", "\\u003c")
        .replace(">", "\\u003e")
        .replace("&", "\\u0026")
    )


def js_string(value: str) -> str:
    return json_for_script(value)


def render_learn_panel(lesson: dict[str, Any], input_id: str, panel_path: str, interactive: bool) -> str:
    template = learn_template_path()
    if not template.exists():
        raise SystemExit(f"Missing learn template: {template}")
    html = template.read_text(encoding="utf-8")
    replacements = {
        "__LOCALWEB_LESSON_DATA__": json_for_script(lesson),
        "__LOCALWEB_INPUT_ID__": js_string(input_id)[1:-1],
        "__LOCALWEB_PANEL_ID__": js_string(panel_path)[1:-1],
        "__LOCALWEB_INTERACTIVE__": "true" if interactive else "false",
    }
    for marker, value in replacements.items():
        if marker not in html:
            raise SystemExit(f"Learn template missing marker: {marker}")
        html = html.replace(marker, value)
    return html


def has_lesson_questions(lesson: dict[str, Any]) -> bool:
    questions = lesson.get("questions")
    return isinstance(questions, list) and any(isinstance(item, dict) for item in questions)


def lesson_panel_id(args_id: str | None, lesson: dict[str, Any]) -> str:
    if args_id is not None:
        panel_id = safe_id(args_id)
        return panel_id if panel_id.startswith("learn-") else f"learn-{panel_id}"

    for raw in (lesson.get("id"), lesson.get("title")):
        panel_id = slug_id(str(raw or ""))
        if panel_id:
            return panel_id if panel_id.startswith("learn-") else f"learn-{panel_id}"

    digest = hashlib.sha1(str(lesson.get("title") or "learn").encode("utf-8")).hexdigest()[:10]
    panel_id = f"learn-{digest}"
    return panel_id if panel_id.startswith("learn-") else f"learn-{panel_id}"


def learn_context(args_context: list[str] | None, lesson: dict[str, Any], input_mode: str) -> list[dict[str, str]]:
    context = [
        {"label": "Mode", "value": "learn"},
        {"label": "Topic", "value": str(lesson.get("title") or "Learning panel")},
        {"label": "Stage", "value": str(lesson.get("stage") or "Concept")},
        {"label": "Input", "value": input_mode},
    ]
    extra = parse_context(args_context)
    if extra:
        context.extend(extra)
    return context


def wait_next_command(project: Path, include_project: bool, wait_id: str, wait_type: str) -> str:
    command = ["uv", "run", "scripts/localweb.py", "wait"]
    if include_project:
        command.extend(["--project", str(project)])
    command.extend(["--id", wait_id])
    if wait_type != "choice":
        command.extend(["--type", wait_type])
    return shlex.join(command)


def wait_response_fields(project: Path, include_project: bool, wait_id: str, wait_type: str) -> dict[str, Any]:
    return {
        "command_status": "ok",
        "state_status": "waiting_for_user",
        "wait_required": True,
        "wait": {
            "id": wait_id,
            "type": wait_type,
        },
        "next_command": wait_next_command(project, include_project, wait_id, wait_type),
    }


def wait_hint_fields() -> dict[str, Any]:
    return {
        "command_status": "ok",
        "state_status": "waiting_for_user",
        "wait_required": True,
        "wait": {
            "id": None,
            "type": None,
        },
        "next_command": None,
        "hint": "Run localweb wait with the matching input id, or pass --wait-id to this command.",
    }


def cmd_init(args: argparse.Namespace) -> None:
    print_json(init_project(resolve_project(args.project), force=args.force, shell_only=args.shell_only))


def cmd_panel(args: argparse.Namespace) -> None:
    project = resolve_project(args.project)
    if not state_path(project).exists():
        init_project(project)
    panel_id = safe_id(args.id)
    src = Path(args.file).expanduser().resolve()
    if not src.exists() or not src.is_file():
        raise SystemExit(f"Panel file not found: {src}")
    dst = panels_dir(project) / f"{panel_id}.html"
    dst.write_text(src.read_text(encoding="utf-8"), encoding="utf-8")
    state = load_state(project)
    if args.activate:
        state["active_panel"] = f"panels/{panel_id}.html"
    if args.title:
        state["title"] = args.title
    context = parse_context(args.context)
    if context is not None:
        state["context"] = context
    if args.wait_id:
        state["status"] = "waiting_for_user"
    save_state(project, state, event_type="panel_updated")
    output: dict[str, Any] = {
        "status": state["status"] if args.wait_id else "ok",
        "panel": f"panels/{panel_id}.html",
        "path": str(dst),
    }
    if args.wait_id:
        output.update(wait_response_fields(project, args.project is not None, args.wait_id, args.wait_type))
    print_json(output)


def cmd_learn(args: argparse.Namespace) -> None:
    project = resolve_project(args.project)
    if not state_path(project).exists():
        init_project(project)

    lesson = read_lesson(Path(args.file).expanduser().resolve())
    panel_id = lesson_panel_id(args.id, lesson)
    panel_path = f"panels/{panel_id}.html"
    input_id = safe_id(args.input_id or panel_id)
    should_wait = has_lesson_questions(lesson) if args.wait is None else bool(args.wait)
    panel_html = render_learn_panel(lesson, input_id, panel_path, interactive=should_wait)

    dst = panels_dir(project) / f"{panel_id}.html"
    dst.write_text(panel_html, encoding="utf-8")

    if should_wait:
        obsolete_old_panel_inputs(project, input_id)

    state = load_state(project)
    if args.activate:
        state["active_panel"] = panel_path
    state["title"] = args.title or str(lesson.get("title") or "LocalWeb Learn")
    state["status"] = "waiting_for_user" if should_wait else "learning"
    state["context"] = learn_context(args.context, lesson, "panel_input" if should_wait else "display")
    state["choices"] = []
    state["active_choice_id"] = None
    save_state(project, state, event_type="learn_panel_updated")

    output: dict[str, Any] = {
        "status": "waiting_for_user" if should_wait else "ok",
        "mode": "learn",
        "lesson": str(Path(args.file).expanduser().resolve()),
        "panel": panel_path,
        "path": str(dst),
        "input_id": input_id if should_wait else None,
    }
    if should_wait:
        output.update(wait_response_fields(project, args.project is not None, input_id, "panel"))
    print_json(output)


def cmd_status(args: argparse.Namespace) -> None:
    project = resolve_project(args.project)
    if not state_path(project).exists():
        init_project(project)
    state = load_state(project)
    if args.wait_id and args.state not in (None, "waiting_for_user"):
        raise SystemExit("--wait-id requires --state waiting_for_user or no --state")
    if args.state is not None:
        state["status"] = args.state
    if args.wait_id:
        state["status"] = "waiting_for_user"
    if args.title is not None:
        state["title"] = args.title
    if args.session_id is not None:
        state["session_id"] = args.session_id
    if args.panel is not None:
        state["active_panel"] = args.panel
    context = parse_context(args.context)
    if context is not None:
        state["context"] = context
    save_state(project, state)
    is_waiting = state.get("status") == "waiting_for_user"
    output: dict[str, Any] = {"status": "waiting_for_user" if is_waiting else "ok", "state": state}
    if args.wait_id:
        output.update(wait_response_fields(project, args.project is not None, args.wait_id, args.wait_type))
    elif state.get("status") == "waiting_for_user":
        output.update(wait_hint_fields())
    print_json(output)


def cmd_choice(args: argparse.Namespace) -> None:
    project = resolve_project(args.project)
    if not state_path(project).exists():
        init_project(project)

    # 标记同 choice_id 的旧事件为已作废
    obsolete_old_choices(project, args.id)

    choices = parse_options(args.option)
    state = load_state(project)
    state["active_choice_id"] = args.id
    state["choices"] = choices
    state["status"] = "waiting_for_user"
    if args.title:
        state["title"] = args.title
    save_state(project, state, event_type="choice_requested")
    output: dict[str, Any] = {
        "status": "waiting_for_user",
        "choice_id": args.id,
        "choices": choices,
    }
    output.update(wait_response_fields(project, args.project is not None, args.id, "choice"))
    print_json(output)


def consumed_event_ids(project: Path) -> set[str]:
    """返回已消费或已作废的 event_id 集合"""
    return {
        str(event.get("event_id"))
        for event in read_jsonl(events_path(project))
        if (
            event.get("type")
            in ("choice_consumed", "choice_obsoleted", "panel_input_consumed", "panel_input_obsoleted")
            and event.get("event_id")
        )
    }


def obsolete_old_choices(project: Path, choice_id: str) -> None:
    """标记同 choice_id 的所有未消费事件为已作废"""
    consumed = consumed_event_ids(project)
    for event in read_jsonl(inbox_path(project)):
        if event.get("type") == "choice" and event.get("choice_id") == choice_id:
            event_id = str(event.get("event_id", ""))
            if event_id and event_id not in consumed:
                append_jsonl(
                    events_path(project),
                    {
                        "type": "choice_obsoleted",
                        "event_id": event_id,
                        "choice_id": choice_id,
                        "reason": "new choice created with same id",
                        "ts": now_iso(),
                    },
                )


def obsolete_old_panel_inputs(project: Path, input_id: str) -> None:
    """标记同 input_id 的所有未消费 panel 输入为已作废"""
    consumed = consumed_event_ids(project)
    for event in read_jsonl(inbox_path(project)):
        if event.get("type") == "panel_input" and event.get("input_id") == input_id:
            event_id = str(event.get("event_id", ""))
            if event_id and event_id not in consumed:
                append_jsonl(
                    events_path(project),
                    {
                        "type": "panel_input_obsoleted",
                        "event_id": event_id,
                        "input_id": input_id,
                        "reason": "new panel input received with same id",
                        "ts": now_iso(),
                    },
                )


def find_choice(project: Path, choice_id: str) -> dict[str, Any] | None:
    consumed = consumed_event_ids(project)
    for event in read_jsonl(inbox_path(project)):
        if event.get("type") != "choice":
            continue
        if event.get("choice_id") != choice_id:
            continue
        event_id = str(event.get("event_id", ""))
        if event_id and event_id not in consumed:
            return event
    return None


def find_panel_input(project: Path, input_id: str) -> dict[str, Any] | None:
    consumed = consumed_event_ids(project)
    for event in read_jsonl(inbox_path(project)):
        if event.get("type") != "panel_input":
            continue
        if event.get("input_id") != input_id:
            continue
        event_id = str(event.get("event_id", ""))
        if event_id and event_id not in consumed:
            return event
    return None


def consume_choice(project: Path, choice_id: str, event: dict[str, Any]) -> str:
    event_id = str(event.get("event_id"))
    append_jsonl(
        events_path(project),
        {
            "type": "choice_consumed",
            "event_id": event_id,
            "choice_id": choice_id,
            "value": event.get("value"),
            "ts": now_iso(),
        },
    )
    return str(event.get("value", ""))


def consume_panel_input(project: Path, input_id: str, event: dict[str, Any]) -> str:
    event_id = str(event.get("event_id"))
    text = str(event.get("text", ""))
    append_jsonl(
        events_path(project),
        {
            "type": "panel_input_consumed",
            "event_id": event_id,
            "input_id": input_id,
            "text": text,
            "ts": now_iso(),
        },
    )
    return text


def find_wait_event(project: Path, wait_id: str, wait_type: str) -> tuple[str, dict[str, Any]] | None:
    if wait_type in ("choice", "any"):
        event = find_choice(project, wait_id)
        if event:
            return ("choice", event)
    if wait_type in ("panel", "any"):
        event = find_panel_input(project, wait_id)
        if event:
            return ("panel", event)
    return None


def consume_wait_event(project: Path, wait_id: str, result: tuple[str, dict[str, Any]]) -> str:
    event_type, event = result
    if event_type == "choice":
        return consume_choice(project, wait_id, event)
    return consume_panel_input(project, wait_id, event)


def cli_override_event(wait_id: str, wait_type: str, value: str) -> dict[str, Any]:
    event: dict[str, Any] = {
        "type": "cli_override",
        "wait_type": wait_type,
        "value": value,
        "reason": "interactive tty fallback",
        "ts": now_iso(),
    }
    if wait_type in ("choice", "any"):
        event["choice_id"] = wait_id
    if wait_type in ("panel", "any"):
        event["input_id"] = wait_id
    return event


def cmd_wait(args: argparse.Namespace) -> None:
    project = resolve_project(args.project)
    require_initialized(project)
    start = time.monotonic()
    timeout = args.timeout
    wait_type = args.type

    cli_fallback = bool(args.cli_fallback)
    select_module = None
    if cli_fallback:
        if not sys.stdin.isatty():
            raise SystemExit("--cli-fallback requires interactive TTY stdin")
        try:
            import select
        except ImportError as exc:
            raise SystemExit("--cli-fallback requires select support") from exc
        select_module = select

    while True:
        result = find_wait_event(project, args.id, wait_type)
        if result:
            print(consume_wait_event(project, args.id, result))
            return

        if cli_fallback and select_module is not None:
            readable, _, _ = select_module.select([sys.stdin], [], [], 0)
            if readable:
                try:
                    user_input = sys.stdin.readline().strip()
                except (EOFError, OSError):
                    user_input = ""
                if user_input:
                    result = find_wait_event(project, args.id, wait_type)
                    if result:
                        print(consume_wait_event(project, args.id, result))
                        return
                    append_jsonl(events_path(project), cli_override_event(args.id, wait_type, user_input))
                    print(user_input)
                    return

        if timeout is not None and timeout >= 0 and time.monotonic() - start >= timeout:
            raise SystemExit(f"Timed out waiting for {wait_type} input id {args.id!r}")

        time.sleep(args.interval)


def cmd_emit(args: argparse.Namespace) -> None:
    project = resolve_project(args.project)
    if not state_path(project).exists():
        init_project(project)
    data: dict[str, Any] = {}
    if args.data:
        try:
            parsed = json.loads(args.data)
        except json.JSONDecodeError as exc:
            raise SystemExit(f"Invalid --data JSON: {exc}") from exc
        if not isinstance(parsed, dict):
            raise SystemExit("--data must be a JSON object")
        data = parsed
    event = {
        "type": args.type,
        "message": args.message,
        "ts": now_iso(),
        **data,
    }
    append_jsonl(events_path(project), event)
    print_json({"status": "ok", "event": event})


def cmd_clean(args: argparse.Namespace) -> None:
    """清理 inbox 中已消费或已作废的事件"""
    project = resolve_project(args.project)
    require_initialized(project)

    consumed = consumed_event_ids(project)
    inbox = inbox_path(project)

    with with_jsonl_lock(inbox) as lock:
        try:
            # 读取所有未消费的事件
            unconsumed_events = []
            removed_count = 0
            for event in read_jsonl(inbox):
                event_id = str(event.get("event_id", ""))
                if event_id and event_id in consumed:
                    removed_count += 1
                else:
                    unconsumed_events.append(event)

            # 原子替换 inbox，只保留未消费的事件
            write_jsonl_atomic(inbox, unconsumed_events)
        finally:
            fcntl.flock(lock, fcntl.LOCK_UN)

    # 记录清理事件
    append_jsonl(
        events_path(project),
        {
            "type": "inbox_cleaned",
            "removed": removed_count,
            "remaining": len(unconsumed_events),
            "ts": now_iso(),
        },
    )

    print_json({
        "status": "ok",
        "removed": removed_count,
        "remaining": len(unconsumed_events),
    })


def cmd_doctor(args: argparse.Namespace) -> None:
    project = resolve_project(args.project)
    checks: list[dict[str, Any]] = []

    checks.append({"name": "python", "status": "ok", "value": sys.version.split()[0]})
    checks.append({"name": "skill-root", "status": "ok" if skill_root().exists() else "error", "value": str(skill_root())})
    checks.append({"name": "shell-assets", "status": "ok" if shell_source_dir().exists() else "error", "value": str(shell_source_dir())})
    try:
        import fastapi  # type: ignore
        import uvicorn  # type: ignore

        checks.append({"name": "fastapi", "status": "ok", "value": getattr(fastapi, "__version__", "unknown")})
        checks.append({"name": "uvicorn", "status": "ok", "value": getattr(uvicorn, "__version__", "unknown")})
    except Exception as exc:
        checks.append({"name": "server-deps", "status": "error", "value": str(exc)})

    writable = project.exists() and project.is_dir() and os_access_write(project)
    checks.append({"name": "project-writable", "status": "ok" if writable else "error", "value": str(project)})
    checks.append({"name": "localweb-initialized", "status": "ok" if state_path(project).exists() else "missing", "value": str(localweb_dir(project))})
    if state_path(project).exists():
        checks.append({
            "name": "shell-write-token",
            "status": "ok" if shell_supports_write_token(project) else "error",
            "value": str(shell_dir(project) / "app.js"),
            "hint": f"uv run scripts/localweb.py init --project {project} --shell-only",
        })

    status = "ok" if all(c["status"] in {"ok", "missing"} for c in checks) else "error"
    print_json({"status": status, "project_root": str(project), "checks": checks})


def os_access_write(path: Path) -> bool:
    probe = path / f".localweb-write-test-{uuid.uuid4().hex}"
    try:
        probe.write_text("", encoding="utf-8")
        probe.unlink()
        return True
    except OSError:
        return False


def is_port_free(host: str, port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            sock.bind((host, port))
        except OSError:
            return False
    return True


def choose_port(host: str, requested: int) -> int:
    for port in range(requested, requested + 50):
        if is_port_free(host, port):
            return port
    raise SystemExit(f"No free port found from {requested} to {requested + 49}")


def ensure_inside(root: Path, candidate: Path) -> Path:
    resolved_root = root.resolve()
    resolved = candidate.resolve()
    try:
        resolved.relative_to(resolved_root)
    except ValueError as exc:
        raise PermissionError(f"Path escapes {resolved_root}: {resolved}") from exc
    return resolved


def create_app(project: Path):
    from fastapi import FastAPI, HTTPException, Request
    from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, StreamingResponse

    app = FastAPI(title="LocalWeb", docs_url=None, redoc_url=None)
    lw_root = localweb_dir(project).resolve()

    async def request_json_object(request: Request) -> dict[str, Any]:
        try:
            body = await request.json()
        except json.JSONDecodeError as exc:
            raise HTTPException(status_code=400, detail="invalid JSON body") from exc
        if not isinstance(body, dict):
            raise HTTPException(status_code=400, detail="JSON body must be an object")
        return body

    def require_write_token(request: Request, state: dict[str, Any]) -> None:
        expected = str(state.get("write_token") or "")
        received = request.headers.get("x-localweb-token", "")
        if not expected or not received or not secrets.compare_digest(received, expected):
            raise HTTPException(status_code=403, detail="invalid LocalWeb write token")

    def file_response(root: Path, rel_path: str) -> FileResponse:
        try:
            target = ensure_inside(root, root / rel_path)
        except PermissionError as exc:
            raise HTTPException(status_code=403, detail=str(exc)) from exc
        if not target.exists() or not target.is_file():
            raise HTTPException(status_code=404, detail="not found")
        return FileResponse(target)

    @app.get("/")
    async def index() -> HTMLResponse:
        index_path = shell_dir(project) / "index.html"
        if not index_path.exists():
            raise HTTPException(status_code=404, detail="shell not initialized")
        return HTMLResponse(index_path.read_text(encoding="utf-8"))

    @app.get("/api/state")
    async def api_state() -> JSONResponse:
        return JSONResponse(load_state(project))

    @app.get("/api/stream")
    async def api_stream():
        async def event_stream():
            last_state = 0.0
            while True:
                try:
                    current = state_path(project).stat().st_mtime
                    if current != last_state:
                        last_state = current
                        state = load_state(project)
                        yield f"event: state\ndata: {json.dumps(state, ensure_ascii=False)}\n\n"
                except FileNotFoundError:
                    yield "event: error\ndata: {\"message\":\"state missing\"}\n\n"
                await asyncio.sleep(0.5)

        return StreamingResponse(event_stream(), media_type="text/event-stream")

    @app.post("/api/choice")
    async def api_choice(request: Request) -> JSONResponse:
        body = await request_json_object(request)
        state = load_state(project)
        require_write_token(request, state)
        active_choice_id = str(state.get("active_choice_id") or "").strip()
        choice_id = str(body.get("choice_id") or active_choice_id).strip()
        value = str(body.get("value") or "").strip()
        if not choice_id or not value:
            raise HTTPException(status_code=400, detail="choice_id and value are required")
        if not active_choice_id or choice_id != active_choice_id:
            raise HTTPException(status_code=409, detail="choice_id is not active")
        allowed_choices = {
            str(choice.get("id") or choice.get("value") or "").strip()
            for choice in state.get("choices", [])
            if isinstance(choice, dict)
        }
        if value not in allowed_choices:
            raise HTTPException(status_code=400, detail="value is not an active choice")
        label = body.get("label") or value
        event = {
            "event_id": uuid.uuid4().hex,
            "type": "choice",
            "choice_id": str(choice_id),
            "value": str(value),
            "label": str(label),
            "session_id": state.get("session_id", DEFAULT_SESSION),
            "ts": now_iso(),
        }
        append_jsonl(inbox_path(project), event)
        append_jsonl(events_path(project), {**event, "type": "choice_received"})
        return JSONResponse({"status": "ok", "event": event})

    @app.post("/api/panel-input")
    async def api_panel_input(request: Request) -> JSONResponse:
        body = await request_json_object(request)
        state = load_state(project)
        require_write_token(request, state)
        input_id = str(body.get("input_id") or body.get("id") or "").strip()
        text = body.get("text")
        if not input_id or not re.fullmatch(r"[a-zA-Z0-9_-]+", input_id):
            raise HTTPException(status_code=400, detail="input_id must contain only letters, digits, '_' or '-'")
        if not isinstance(text, str) or not text.strip():
            raise HTTPException(status_code=400, detail="text is required")
        if len(text) > MAX_PANEL_INPUT_CHARS:
            raise HTTPException(status_code=413, detail=f"text exceeds {MAX_PANEL_INPUT_CHARS} characters")
        meta = body.get("meta")
        if meta is not None and not isinstance(meta, dict):
            raise HTTPException(status_code=400, detail="meta must be an object")

        obsolete_old_panel_inputs(project, input_id)
        event = {
            "event_id": uuid.uuid4().hex,
            "type": "panel_input",
            "input_id": input_id,
            "text": text,
            "label": str(body.get("label") or ""),
            "panel_id": str(body.get("panel_id") or state.get("active_panel") or ""),
            "meta": meta or {},
            "session_id": state.get("session_id", DEFAULT_SESSION),
            "ts": now_iso(),
        }
        append_jsonl(inbox_path(project), event)
        append_jsonl(events_path(project), {**event, "type": "panel_input_received"})
        return JSONResponse({"status": "ok", "event": event})

    @app.get("/shell/{rel_path:path}")
    async def shell_asset(rel_path: str) -> FileResponse:
        return file_response(shell_dir(project), rel_path)

    @app.get("/panels/{rel_path:path}")
    async def panel_asset(rel_path: str) -> FileResponse:
        return file_response(panels_dir(project), rel_path)

    @app.get("/assets/{rel_path:path}")
    async def asset(rel_path: str) -> FileResponse:
        return file_response(assets_dir(project), rel_path)

    @app.get("/health")
    async def health() -> JSONResponse:
        return JSONResponse({"status": "ok", "project_root": str(project), "localweb_dir": str(lw_root)})

    return app


def cmd_serve(args: argparse.Namespace) -> None:
    project = resolve_project(args.project)
    if not state_path(project).exists():
        if args.init:
            init_project(project)
        else:
            raise SystemExit(f"{localweb_dir(project)} is not initialized. Run init or pass --init.")
    require_current_shell(project)

    host = args.host
    if host != "127.0.0.1" and not args.allow_remote:
        raise SystemExit("Refusing non-local host without --allow-remote")

    port = choose_port(host, args.port)
    url = f"http://{host}:{port}"
    print_json(
        {
            "status": "ok",
            "url": url,
            "host": host,
            "port": port,
            "project_root": str(project),
            "localweb_dir": str(localweb_dir(project)),
            "note": "Press Ctrl+C to stop.",
        }
    )
    sys.stdout.flush()

    import uvicorn

    uvicorn.run(create_app(project), host=host, port=port, log_level=args.log_level)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="localweb.py", description="Project-level HTML companion for CLI agents.")
    sub = parser.add_subparsers(dest="command", required=True)

    def add_project(p: argparse.ArgumentParser) -> None:
        p.add_argument("--project", help="Project root. Defaults to current working directory.")

    p = sub.add_parser("init", help="Initialize project-level .localweb directory.")
    add_project(p)
    p.add_argument("--force", action="store_true", help="Overwrite default files and shell assets.")
    p.add_argument("--shell-only", action="store_true", help="Refresh shell assets without touching state, inbox, or panels.")
    p.set_defaults(func=cmd_init)

    p = sub.add_parser("doctor", help="Check runtime health.")
    add_project(p)
    p.set_defaults(func=cmd_doctor)

    p = sub.add_parser("serve", help="Serve the local browser companion.")
    add_project(p)
    p.add_argument("--host", default="127.0.0.1")
    p.add_argument("--port", type=int, default=8765)
    p.add_argument("--init", action="store_true", help="Initialize .localweb first if missing.")
    p.add_argument("--allow-remote", action="store_true", help="Allow binding to a non-local host.")
    p.add_argument("--log-level", default="warning")
    p.set_defaults(func=cmd_serve)

    p = sub.add_parser("panel", help="Register an HTML panel.")
    add_project(p)
    p.add_argument("--id", required=True)
    p.add_argument("--file", required=True)
    p.add_argument("--title")
    p.add_argument("--context", action="append", help="Context item as Label=Value. Repeatable.")
    p.add_argument("--activate", action=argparse.BooleanOptionalAction, default=True)
    p.add_argument("--wait-id", help="Declare that this panel expects browser input and emit the matching wait command.")
    p.add_argument("--wait-type", choices=("choice", "panel", "any"), default="panel", help="Input type for --wait-id.")
    p.set_defaults(func=cmd_panel)

    p = sub.add_parser("learn", help="Render a structured learning panel.")
    add_project(p)
    p.add_argument("--file", required=True, help="Lesson JSON file.")
    p.add_argument("--id", help="Panel id. Defaults to lesson id/title with a learn- prefix.")
    p.add_argument("--title", help="Shell title. Defaults to lesson title.")
    p.add_argument("--context", action="append", help="Extra context item as Label=Value. Repeatable.")
    p.add_argument("--activate", action=argparse.BooleanOptionalAction, default=True)
    p.add_argument("--input-id", help="Panel input id. Defaults to the generated panel id.")
    p.add_argument(
        "--wait",
        action=argparse.BooleanOptionalAction,
        default=None,
        help="Whether to enter waiting mode. Defaults to true when the lesson has questions.",
    )
    p.set_defaults(func=cmd_learn)

    p = sub.add_parser("status", help="Update shell status.")
    add_project(p)
    p.add_argument("--state")
    p.add_argument("--title")
    p.add_argument("--session-id")
    p.add_argument("--panel")
    p.add_argument("--context", action="append", help="Context item as Label=Value. Repeatable.")
    p.add_argument("--wait-id", help="Declare that this status update expects browser input and emit the matching wait command.")
    p.add_argument("--wait-type", choices=("choice", "panel", "any"), default="panel", help="Input type for --wait-id.")
    p.set_defaults(func=cmd_status)

    p = sub.add_parser("choice", help="Offer lightweight browser choices.")
    add_project(p)
    p.add_argument("--id", required=True)
    p.add_argument("--title")
    p.add_argument("--option", action="append", required=True, help="Choice as A=Label. Repeatable.")
    p.set_defaults(func=cmd_choice)

    p = sub.add_parser("wait", help="Wait for browser input and print its value.")
    add_project(p)
    p.add_argument("--id", required=True)
    p.add_argument("--type", choices=("choice", "panel", "any"), default="choice", help="Input type to consume.")
    p.add_argument("--timeout", type=float, default=-1, help="Seconds to wait. Negative means forever.")
    p.add_argument("--interval", type=float, default=0.2)
    p.add_argument("--cli-fallback", action="store_true", help="Allow typed TTY input as an explicit fallback.")
    p.set_defaults(func=cmd_wait)

    p = sub.add_parser("emit", help="Append an event to events.jsonl.")
    add_project(p)
    p.add_argument("--type", required=True)
    p.add_argument("--message")
    p.add_argument("--data", help="Extra JSON object merged into the event.")
    p.set_defaults(func=cmd_emit)

    p = sub.add_parser("clean", help="Clean consumed and obsoleted events from inbox.")
    add_project(p)
    p.set_defaults(func=cmd_clean)

    return parser


def main(argv: list[str] | None = None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)
    args.func(args)


if __name__ == "__main__":
    main()
