# HTML Panel Patterns

Generate self-contained HTML panels when visual structure beats prose.

## Learning Explainer

Use for concepts, repo behavior, APIs, protocols, and algorithms.

Panel ingredients:

- TL;DR banner
- clickable or hoverable process diagram
- glossary strip
- tabs for examples
- optional context controls such as hotspots, filters, ranking chips, small forms, or next-step cards when the CLI agent needs a user signal

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
- Pure display is a first-class output. Add interactions only when they help the user express context that is hard to provide in CLI text.
- Mark visible text with `data-lw-text` when practical.
