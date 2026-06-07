# LocalWeb Learn

`localweb learn` is a focused learning panel mode. It renders a structured lesson JSON into a self-contained HTML panel with concept cards, a structure map, examples, and optional active-recall questions.

The browser remains a visual worksheet. The CLI remains the tutor, main context, and control surface.

## Contract

- Source templates and schemas live in this `learn/` directory.
- Runtime panels are generated into the target project's `.localweb/panels/`.
- Browser answers return through the existing `panel_input` inbox path.
- No new server protocol, permission path, or hidden browser-side agent context is introduced.

## Usage

```bash
uv run scripts/localweb.py learn \
  --file learn/examples/epsilon-delta.json \
  --id epsilon-delta
```

If the lesson contains questions, `learn` enters `waiting_for_user` by default and prints the matching `wait` command:

```bash
uv run scripts/localweb.py wait --id learn-epsilon-delta --type panel
```

Use `--no-wait` for a pure display panel, or `--wait` to force an answer round even when a lesson has no questions.

## Lesson Shape

The schema is intentionally small:

- `title`, `subtitle`, `stage`, `summary`
- `objectives`
- `concepts`
- `structure.nodes` and `structure.edges`
- `examples`
- `questions`
- `next`

Use one lesson JSON per knowledge point. Reuse the default template across stages unless the learning activity needs a fundamentally different interface, such as proof-step sorting, a code sandbox, a dense graph browser, or a long-term review dashboard.

