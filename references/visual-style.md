# Default Shell Visual Style

The default shell is a yellow-black cartoon terminal deck. It is a replaceable skin over the stable file protocol.

## Direction

- Hard black outlines.
- Yellow as the primary attention color.
- Dark brown/black terminal background.
- Small radii, never soft pill-heavy UI.
- Dense but legible terminal-like layout.
- A top status rail, left context stack, central HTML stage, and optional interaction tray.

## Palette

```text
Ink:    #050505
Base:   #17140b
Panel:  #241f10
Yellow: #ffd43b
Cream:  #fff3bf
Orange: #ff8f1f
Cyan:   #24d7ff
```

## Layout

```text
compact top status bar
narrow context stack | dominant central iframe stage
optional interaction tray under the stage, hidden when inactive
```

The central panel content is intentionally not constrained to this style. The shell frames the output; the agent-generated panel owns its own visual language. The interaction tray should disappear or recede when there is no active user input request.

Layout defaults:

- Keep the top rail near 56px on desktop.
- Keep the context column narrow, roughly 160-220px, and hide it when no useful context exists.
- Let the central stage take the remaining space; do not reserve empty space for inactive choices.
- On mobile, show the stage before secondary context.
