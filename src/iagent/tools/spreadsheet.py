"""Read-only spreadsheet inspection.

A single pure function, `read_xlsx`, that renders an `.xlsx` workbook as compact
text an LLM can reason over: sheet names, dimensions, and a truncated top-left
block of cell values per sheet. Kept capability-agnostic on purpose so it can be
wired into a Pydantic AI `FunctionToolset` (or called directly in tests) now, and
folded into a richer file capability later.
"""

from __future__ import annotations

from pathlib import Path

import openpyxl

ALLOWED_SUFFIXES: frozenset[str] = frozenset({".xlsx", ".xlsm"})

DEFAULT_MAX_ROWS = 20
DEFAULT_MAX_COLS = 20


def _check_path(p: Path) -> None:
    """Validate that `p` exists and is an allowed spreadsheet type."""
    if not p.is_file():
        raise FileNotFoundError(f"No such workbook: {p}")
    if p.suffix.lower() not in ALLOWED_SUFFIXES:
        allowed = ", ".join(sorted(ALLOWED_SUFFIXES))
        raise ValueError(f"Unsupported spreadsheet type {p.suffix!r}; allowed: {allowed}")


def summarize_xlsx(path: str | Path) -> str:
    """Return cheap metadata about a workbook: no cell values are read.

    Use this first to learn the shape of a workbook before deciding how much to
    load with `read_xlsx`. Reports the number of sheets, their names, and the
    size (dimensions and max row/column) of each sheet.

    Args:
        path: Path to the `.xlsx`/`.xlsm` workbook to inspect.

    Returns:
        A string with a workbook header line followed by one line per sheet.

    Raises:
        FileNotFoundError: The path does not exist.
        ValueError: The suffix is not an allowed spreadsheet type.
    """
    p = Path(path)
    _check_path(p)

    wb = openpyxl.load_workbook(p, read_only=True)
    try:
        names = wb.sheetnames
        out = [f"workbook: {p.name} ({len(names)} sheet(s): {', '.join(names)})"]
        for ws in wb.worksheets:
            out.append(
                f"  [sheet: {ws.title!r}] dims={ws.calculate_dimension()} "
                f"max_row={ws.max_row} max_col={ws.max_column}"
            )
        return "\n".join(out)
    finally:
        wb.close()


def _cell(value: object) -> str:
    """Render one cell value for the text grid; blanks become empty strings."""
    return "" if value is None else str(value)


def _render_sheet(ws: object, max_rows: int, max_cols: int) -> list[str]:
    lines = [
        f"[sheet: {ws.title!r}] "  # type: ignore[attr-defined]
        f"dims={ws.dimensions} max_row={ws.max_row} max_col={ws.max_column}"  # type: ignore[attr-defined]
    ]  # noqa: E501
    truncated_rows = ws.max_row > max_rows  # type: ignore[attr-defined]
    truncated_cols = ws.max_column > max_cols  # type: ignore[attr-defined]
    for r, row in enumerate(
        ws.iter_rows(max_row=max_rows, max_col=max_cols, values_only=True),  # type: ignore[attr-defined]
        start=1,
    ):
        cells = " | ".join(_cell(v) for v in row)
        lines.append(f"  r{r}: {cells}")
    if truncated_rows or truncated_cols:
        notes = []
        if truncated_rows:
            notes.append(f"rows >{max_rows} hidden")
        if truncated_cols:
            notes.append(f"cols >{max_cols} hidden")
        lines.append(f"  ... ({', '.join(notes)})")
    return lines


def read_xlsx(
    path: str | Path,
    *,
    sheet: str | None = None,
    max_rows: int = DEFAULT_MAX_ROWS,
    max_cols: int = DEFAULT_MAX_COLS,
    data_only: bool = True,
) -> str:
    """Return a compact text view of an Excel workbook for inspection.

    Args:
        path: Path to the `.xlsx`/`.xlsm` workbook to read.
        sheet: Name of a single sheet to render. If omitted, every sheet is shown.
        max_rows: Max rows rendered per sheet (from the top). Must be positive.
        max_cols: Max columns rendered per sheet (from the left). Must be positive.
        data_only: If True, show cached computed values for formula cells; if False,
            show the formula text instead. Cached values exist only if the file was
            last saved by a spreadsheet application.

    Returns:
        A human/LLM-readable string: one header line per sheet with dimensions,
        followed by a truncated grid of cell values.

    Raises:
        FileNotFoundError: The path does not exist.
        ValueError: The suffix is not an allowed spreadsheet type, max_rows/max_cols
            are not positive, or the named sheet is absent.
    """
    p = Path(path)
    if max_rows < 1 or max_cols < 1:
        raise ValueError("max_rows and max_cols must be positive")
    _check_path(p)

    # Not read_only: inspection needs reliable `.dimensions`/`.max_row`/`.max_column`,
    # which ReadOnlyWorksheet does not expose until rows are iterated. Inspected
    # workbooks are small, so the full in-memory load is acceptable.
    wb = openpyxl.load_workbook(p, data_only=data_only)
    try:
        if sheet is not None:
            if sheet not in wb.sheetnames:
                available = ", ".join(wb.sheetnames)
                raise ValueError(f"No sheet named {sheet!r}; available: {available}")
            worksheets = [wb[sheet]]
        else:
            worksheets = list(wb.worksheets)

        out = [f"workbook: {p.name} (sheets: {', '.join(wb.sheetnames)})"]
        for ws in worksheets:
            out.extend(_render_sheet(ws, max_rows, max_cols))
        return "\n".join(out)
    finally:
        wb.close()
