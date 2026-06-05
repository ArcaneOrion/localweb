# HTML Panel Patterns

Generate self-contained HTML panels when visual structure beats prose.

## Learning Explainer

Use for concepts, repo behavior, APIs, protocols, and algorithms.

Panel ingredients:

- TL;DR banner
- clickable or hoverable process diagram
- glossary strip
- tabs for examples
- A/B/C/D next-step choices in the shell, not inside risky panel logic

## Code Understanding

Use for unfamiliar packages, modules, execution paths, or dependency maps.

Panel ingredients:

- module boxes and arrows
- highlighted hot path
- entry points
- test surface
- risk markers

## Planning and Comparison

Use when alternatives must be compared spatially.

Panel ingredients:

- side-by-side approaches
- trade-off matrix
- timeline
- risk table
- recommended path

## Debugging and Review

Use for incident timelines, failing tests, annotated diffs, and root cause analysis.

Panel ingredients:

- chronological event rail
- failing command and output snippets
- suspected causes
- verification checklist

## Output Rules

- Prefer one complete HTML document per panel.
- Inline CSS and JavaScript.
- Avoid remote assets unless the user explicitly allows them.
- Make the panel responsive inside an iframe.
- Mark visible text with `data-lw-text` when practical.

