"""Small custom prompt_toolkit widgets that questionary doesn't provide.

`multicolumn_checkbox` lays grouped options out in N columns so long lists
(e.g. all NYC neighborhoods) fit on screen instead of scrolling one-per-line.
"""

from __future__ import annotations


def build_grid(
    grouped: list[tuple[str, list[str]]],
    columns: int,
) -> tuple[list[str], list[list[int]], list[tuple[str, list[list[int]]]]]:
    """Flatten grouped options into:

    - items: flat list of option labels (index = stable id)
    - grid:  rows of item indices across all groups (for up/down navigation)
    - blocks: (group_label, rows) for rendering, rows being lists of indices
    """
    items = [name for _, names in grouped for name in names]
    grid: list[list[int]] = []
    blocks: list[tuple[str, list[list[int]]]] = []
    base = 0
    for label, names in grouped:
        rows = []
        for r in range(0, len(names), columns):
            row = list(range(base + r, base + min(r + columns, len(names))))
            rows.append(row)
            grid.append(row)
        blocks.append((label, rows))
        base += len(names)
    return items, grid, blocks


def multicolumn_checkbox(
    message: str,
    grouped: list[tuple[str, list[str]]],
    columns: int = 2,
    instruction: str = "(arrows move · space selects · enter submits)",
) -> list[str]:
    """Multi-select grouped options in a columnar layout. Returns chosen labels.

    Raises KeyboardInterrupt if the user aborts (Ctrl-C / Esc).
    """
    from prompt_toolkit.application import Application
    from prompt_toolkit.key_binding import KeyBindings
    from prompt_toolkit.layout.containers import HSplit, Window
    from prompt_toolkit.layout.controls import FormattedTextControl
    from prompt_toolkit.layout.layout import Layout
    from prompt_toolkit.styles import Style

    items, grid, blocks = build_grid(grouped, columns)
    if not items:
        return []

    selected: set[int] = set()
    state = {"cursor": 0}
    col_width = max(len(n) for n in items) + 6

    def get_text():
        frags: list[tuple[str, str]] = [("class:question", f"? {message}\n")]
        for label, rows in blocks:
            frags.append(("class:separator", f"\n  ── {label} ──\n"))
            for row in rows:
                for i in row:
                    mark = "x" if i in selected else " "
                    cell = f" [{mark}] {items[i]}".ljust(col_width)
                    frags.append(("class:pointer" if i == state["cursor"] else "", cell))
                frags.append(("", "\n"))
        frags.append(("class:instruction", f"\n{instruction}\n"))
        return frags

    def move_vert(delta: int) -> None:
        c = state["cursor"]
        for ri, row in enumerate(grid):
            if c in row:
                ci = row.index(c)
                nrow = grid[min(max(ri + delta, 0), len(grid) - 1)]
                state["cursor"] = nrow[min(ci, len(nrow) - 1)]
                return

    kb = KeyBindings()

    @kb.add("left")
    @kb.add("h")
    def _(_e):
        state["cursor"] = max(0, state["cursor"] - 1)

    @kb.add("right")
    @kb.add("l")
    def _(_e):
        state["cursor"] = min(len(items) - 1, state["cursor"] + 1)

    @kb.add("down")
    @kb.add("j")
    def _(_e):
        move_vert(1)

    @kb.add("up")
    @kb.add("k")
    def _(_e):
        move_vert(-1)

    @kb.add("space")
    def _(_e):
        c = state["cursor"]
        selected.discard(c) if c in selected else selected.add(c)

    @kb.add("enter")
    def _(e):
        e.app.exit(result=[items[i] for i in sorted(selected)])

    @kb.add("c-c")
    @kb.add("escape")
    def _(e):
        e.app.exit(exception=KeyboardInterrupt)

    style = Style.from_dict({
        "question": "bold",
        "separator": "#5f8700 bold",
        "pointer": "reverse",
        "instruction": "#808080 italic",
    })

    window = Window(content=FormattedTextControl(get_text, focusable=True, show_cursor=False), wrap_lines=True)
    app = Application(layout=Layout(HSplit([window])), key_bindings=kb, full_screen=False, style=style)
    return app.run()
