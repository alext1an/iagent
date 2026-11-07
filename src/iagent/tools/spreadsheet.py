"""Read-only spreadsheet inspection.

`summarize_xlsx` reports sheet names and sizes. `read_xlsx` renders a window of
cells, including a caller-supplied range, with formulas and cached values side
by side. `diff_xlsx` lists cells that differ between an edited workbook and the
input it was copied from.
"""

from __future__ import annotations

from pathlib import Path

import openpyxl
from openpyxl.utils import get_column_letter, range_boundaries
from openpyxl.worksheet.worksheet import Worksheet

ALLOWED_SUFFIXES: frozenset[str] = frozenset({".xlsx", ".xlsm"})

DEFAULT_MAX_ROWS = 20
DEFAULT_MAX_COLS = 20
MAX_DIFF_LINES = 200


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


def _literal(value: object) -> str:
    """Render a stored value so text, numbers, and booleans stay distinct."""
    if isinstance(value, str):
        return repr(value)
    if isinstance(value, bool):
        return "TRUE" if value else "FALSE"
    return str(value)


def _describe(formula_value: object, cached_value: object, number_format: str | None) -> str:
    """One cell: formula plus cache, or a literal, with blank distinct from 0."""
    fmt = "" if not number_format or number_format == "General" else f" fmt={number_format}"
    is_formula = isinstance(formula_value, str) and formula_value.startswith("=")
    if is_formula:
        cache = "(none)" if cached_value is None else _literal(cached_value)
        return f"{formula_value} cache={cache}{fmt}"
    if formula_value is None:
        return f"blank{fmt}"
    return f"{_literal(formula_value)}{fmt}"


def _parse_range(cell_range: str) -> tuple[str | None, int, int, int, int]:
    text = cell_range.strip()
    if not text:
        raise ValueError("cell_range must be an A1 range such as 'B40:N80'")
    sheet_name: str | None = None
    if "!" in text:
        sheet_part, text = text.split("!", 1)
        sheet_name = sheet_part.strip().strip("'")
        text = text.strip()
    try:
        min_col, min_row, max_col, max_row = range_boundaries(text)
    except ValueError as exc:
        raise ValueError(f"Invalid cell range {cell_range!r}") from exc
    return sheet_name, min_col, min_row, max_col, max_row


def _select_sheets(wb: openpyxl.Workbook, sheet: str | None) -> list[Worksheet]:
    if sheet is None:
        return list(wb.worksheets)
    if sheet not in wb.sheetnames:
        available = ", ".join(wb.sheetnames)
        raise ValueError(f"No sheet named {sheet!r}; available: {available}")
    return [wb[sheet]]


def _window(
    ws: Worksheet,
    *,
    cell_range: str | None,
    max_rows: int,
    max_cols: int,
) -> tuple[int, int, int, int, bool]:
    """Return min_row, min_col, max_row, max_col, and whether the window was clipped."""
    if cell_range is None:
        min_row, min_col = 1, 1
        full_rows = ws.max_row or 1
        full_cols = ws.max_column or 1
        max_row = min(full_rows, max_rows)
        max_col = min(full_cols, max_cols)
        clipped = full_rows > max_rows or full_cols > max_cols
        return min_row, min_col, max_row, max_col, clipped

    _sheet, min_col, min_row, full_max_col, full_max_row = _parse_range(cell_range)
    max_row = min(full_max_row, min_row + max_rows - 1)
    max_col = min(full_max_col, min_col + max_cols - 1)
    clipped = max_row < full_max_row or max_col < full_max_col
    return min_row, min_col, max_row, max_col, clipped


def _render_sheet(
    ws_formula: Worksheet,
    ws_cached: Worksheet,
    *,
    cell_range: str | None,
    max_rows: int,
    max_cols: int,
) -> list[str]:
    min_row, min_col, max_row, max_col, clipped = _window(
        ws_formula, cell_range=cell_range, max_rows=max_rows, max_cols=max_cols
    )
    start = f"{get_column_letter(min_col)}{min_row}"
    end = f"{get_column_letter(max_col)}{max_row}"
    lines = [
        f"[sheet: {ws_formula.title!r}] range={start}:{end} "
        f"max_row={ws_formula.max_row} max_col={ws_formula.max_column}"
    ]
    for row in range(min_row, max_row + 1):
        cells = []
        for col in range(min_col, max_col + 1):
            formula_cell = ws_formula.cell(row=row, column=col)
            cached_cell = ws_cached.cell(row=row, column=col)
            coord = f"{get_column_letter(col)}{row}"
            text = _describe(formula_cell.value, cached_cell.value, formula_cell.number_format)
            cells.append(f"{coord}:{text}")
        lines.append(f"  r{row}: {' | '.join(cells)}")
    if clipped:
        lines.append(f"  ... (window clipped to {max_rows} rows and {max_cols} cols)")
    return lines


def read_xlsx(
    path: str | Path,
    *,
    sheet: str | None = None,
    cell_range: str | None = None,
    max_rows: int = DEFAULT_MAX_ROWS,
    max_cols: int = DEFAULT_MAX_COLS,
) -> str:
    """Return a text view of a workbook window for inspection.

    Each cell shows its stored value, or its formula and cached value together.
    An empty cell is `blank`, which is different from the number `0` and the
    text `'0'`. A formula whose file has no calculated result shows
    `cache=(none)`. Number formats other than General are included.

    Args:
        path: Path to the `.xlsx`/`.xlsm` workbook to read.
        sheet: Name of a single sheet to render. If omitted, every sheet is shown.
        cell_range: A1 range to read, such as `B40:N80` or `'Data'!B40:N80`.
            The window starts at this range instead of A1. When the workbook has
            more than one sheet, pass `sheet` or include the sheet in the range.
        max_rows: Maximum rows rendered, counted from the start of the window.
        max_cols: Maximum columns rendered, counted from the start of the window.

    Returns:
        One header line per sheet, then one line per rendered row.

    Raises:
        FileNotFoundError: The path does not exist.
        ValueError: The suffix is not an allowed spreadsheet type, the bounds are
            not positive, the range or sheet name is invalid, or a range on a
            multi-sheet workbook does not name its sheet.
    """
    p = Path(path)
    if max_rows < 1 or max_cols < 1:
        raise ValueError("max_rows and max_cols must be positive")
    _check_path(p)

    range_sheet: str | None = None
    if cell_range is not None:
        range_sheet, _min_col, _min_row, _max_col, _max_row = _parse_range(cell_range)
        if range_sheet and sheet and range_sheet != sheet:
            raise ValueError(
                f"cell_range sheet {range_sheet!r} does not match sheet {sheet!r}"
            )

    formulas = openpyxl.load_workbook(p, data_only=False)
    cached = openpyxl.load_workbook(p, data_only=True)
    try:
        chosen = range_sheet or sheet
        if cell_range is not None and chosen is None and len(formulas.sheetnames) != 1:
            available = ", ".join(formulas.sheetnames)
            raise ValueError(f"cell_range needs a sheet; available: {available}")
        worksheets = _select_sheets(formulas, chosen)
        out = [f"workbook: {p.name} (sheets: {', '.join(formulas.sheetnames)})"]
        for ws in worksheets:
            out.extend(
                _render_sheet(
                    ws,
                    cached[ws.title],
                    cell_range=cell_range,
                    max_rows=max_rows,
                    max_cols=max_cols,
                )
            )
        return "\n".join(out)
    finally:
        formulas.close()
        cached.close()


def diff_xlsx(
    output_path: str | Path,
    input_path: str | Path,
    *,
    sheet: str | None = None,
) -> str:
    """List cells where an edited workbook differs from its input workbook.

    Compares stored values, formulas, cached values, and number formats. `blank`,
    `0`, and the text `'0'` are different. Does not read a golden or answer file.

    Args:
        output_path: Workbook written by the edit.
        input_path: Workbook the edit started from.
        sheet: If given, compare only this sheet. It must exist in at least one file.

    Returns:
        A header with the change count, sheet additions and removals, then one
        line per changed cell up to 200 lines.

    Raises:
        FileNotFoundError: Either path does not exist.
        ValueError: A suffix is not an allowed spreadsheet type, or `sheet` is
            absent from both workbooks.
    """
    output = Path(output_path)
    original = Path(input_path)
    _check_path(output)
    _check_path(original)

    out_formula = openpyxl.load_workbook(output, data_only=False)
    out_cached = openpyxl.load_workbook(output, data_only=True)
    in_formula = openpyxl.load_workbook(original, data_only=False)
    in_cached = openpyxl.load_workbook(original, data_only=True)
    try:
        known = set(out_formula.sheetnames) | set(in_formula.sheetnames)
        if sheet is not None and sheet not in known:
            raise ValueError(f"No sheet named {sheet!r} in either workbook")
        out_names = [sheet] if sheet else list(out_formula.sheetnames)
        in_names = [sheet] if sheet else list(in_formula.sheetnames)
        lines = [f"output: {output.name}", f"input: {original.name}"]
        notes: list[str] = []
        for name in out_names:
            if name not in in_formula.sheetnames:
                notes.append(f"sheet {name!r} added")
        for name in in_names:
            if name not in out_formula.sheetnames:
                notes.append(f"sheet {name!r} removed")

        changes: list[str] = []
        shared = [name for name in out_names if name in in_formula.sheetnames]
        for name in shared:
            out_ws = out_formula[name]
            in_ws = in_formula[name]
            max_row = max(out_ws.max_row or 1, in_ws.max_row or 1)
            max_col = max(out_ws.max_column or 1, in_ws.max_column or 1)
            for row in range(1, max_row + 1):
                for col in range(1, max_col + 1):
                    after = _describe(
                        out_ws.cell(row=row, column=col).value,
                        out_cached[name].cell(row=row, column=col).value,
                        out_ws.cell(row=row, column=col).number_format,
                    )
                    before = _describe(
                        in_ws.cell(row=row, column=col).value,
                        in_cached[name].cell(row=row, column=col).value,
                        in_ws.cell(row=row, column=col).number_format,
                    )
                    if after != before:
                        coord = f"{get_column_letter(col)}{row}"
                        changes.append(f"  {name}!{coord}: input={before} output={after}")

        lines.append(f"changed: {len(changes)} cell(s)")
        lines.extend(notes)
        hidden = max(0, len(changes) - MAX_DIFF_LINES)
        lines.extend(changes[:MAX_DIFF_LINES])
        if hidden:
            lines.append(f"  ... ({hidden} more changed cells not shown)")
        return "\n".join(lines)
    finally:
        out_formula.close()
        out_cached.close()
        in_formula.close()
        in_cached.close()
