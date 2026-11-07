from __future__ import annotations

from pathlib import Path

import openpyxl
import pytest

from iagent.tools.spreadsheet import diff_xlsx, read_xlsx, summarize_xlsx


def _make_wb(path: Path, *, rows: int = 3, cols: int = 3) -> None:
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Data"
    for r in range(1, rows + 1):
        for c in range(1, cols + 1):
            ws.cell(row=r, column=c, value=f"r{r}c{c}")
    wb.save(path)


def test_summarize_xlsx_reports_sheet_count_names_sizes(tmp_path: Path) -> None:
    p = tmp_path / "multi.xlsx"
    wb = openpyxl.Workbook()
    wb.active.title = "First"
    ws2 = wb.create_sheet("Second")
    ws2["D4"] = "x"  # force a larger extent
    wb.save(p)
    out = summarize_xlsx(p)
    assert "2 sheet(s): First, Second" in out
    assert "[sheet: 'First']" in out
    assert "[sheet: 'Second']" in out
    assert "max_row=" in out and "max_col=" in out


def test_summarize_xlsx_reads_no_values(tmp_path: Path) -> None:
    p = tmp_path / "secret.xlsx"
    wb = openpyxl.Workbook()
    wb.active["A1"] = "TOP_SECRET_VALUE"
    wb.save(p)
    out = summarize_xlsx(p)
    assert "TOP_SECRET_VALUE" not in out


def test_summarize_xlsx_missing_file_raises(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError, match="No such workbook"):
        summarize_xlsx(tmp_path / "absent.xlsx")


def test_summarize_xlsx_bad_suffix_raises(tmp_path: Path) -> None:
    p = tmp_path / "data.csv"
    p.write_text("a,b\n", encoding="utf-8")
    with pytest.raises(ValueError, match="Unsupported spreadsheet type"):
        summarize_xlsx(p)


def test_read_xlsx_renders_sheet_and_values(tmp_path: Path) -> None:
    p = tmp_path / "book.xlsx"
    _make_wb(p)
    out = read_xlsx(p)
    assert "workbook: book.xlsx" in out
    assert "[sheet: 'Data']" in out
    assert "A1:'r1c1' | B1:'r1c2' | C1:'r1c3'" in out


def test_read_xlsx_blanks_are_empty(tmp_path: Path) -> None:
    p = tmp_path / "gaps.xlsx"
    wb = openpyxl.Workbook()
    ws = wb.active
    ws["A1"] = "x"
    ws["C1"] = "z"  # B1 left blank
    wb.save(p)
    out = read_xlsx(p)
    assert "A1:'x' | B1:blank | C1:'z'" in out


def test_read_xlsx_truncates_and_notes(tmp_path: Path) -> None:
    p = tmp_path / "big.xlsx"
    _make_wb(p, rows=50, cols=50)
    out = read_xlsx(p, max_rows=5, max_cols=4)
    assert "D5:'r5c4'" in out
    assert "'r6c1'" not in out
    assert "window clipped to 5 rows and 4 cols" in out


def test_read_xlsx_single_sheet_selection(tmp_path: Path) -> None:
    p = tmp_path / "multi.xlsx"
    wb = openpyxl.Workbook()
    wb.active.title = "First"
    wb.create_sheet("Second")
    wb.save(p)
    out = read_xlsx(p, sheet="Second")
    assert "[sheet: 'Second']" in out
    assert "[sheet: 'First']" not in out


def test_read_xlsx_missing_sheet_raises(tmp_path: Path) -> None:
    p = tmp_path / "one.xlsx"
    _make_wb(p)
    with pytest.raises(ValueError, match="No sheet named"):
        read_xlsx(p, sheet="Nope")


def test_read_xlsx_missing_file_raises(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError, match="No such workbook"):
        read_xlsx(tmp_path / "absent.xlsx")


def test_read_xlsx_bad_suffix_raises(tmp_path: Path) -> None:
    p = tmp_path / "data.csv"
    p.write_text("a,b,c\n", encoding="utf-8")
    with pytest.raises(ValueError, match="Unsupported spreadsheet type"):
        read_xlsx(p)


def test_read_xlsx_nonpositive_bounds_raise(tmp_path: Path) -> None:
    p = tmp_path / "ok.xlsx"
    _make_wb(p)
    with pytest.raises(ValueError, match="must be positive"):
        read_xlsx(p, max_rows=0)


def test_read_xlsx_range_starts_away_from_origin(tmp_path: Path) -> None:
    p = tmp_path / "lower.xlsx"
    _make_wb(p, rows=45, cols=8)
    out = read_xlsx(p, cell_range="B40:C41")
    assert "range=B40:C41" in out
    assert "B40:'r40c2'" in out
    assert "C41:'r41c3'" in out
    assert "A1:" not in out


def test_read_xlsx_shows_formula_cache_blank_and_format(tmp_path: Path) -> None:
    p = tmp_path / "kinds.xlsx"
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Data"
    ws["A1"] = 0
    ws["B1"] = "0"
    ws["C1"] = None
    ws["D1"] = "=A1+1"
    ws["D1"].number_format = "0.00"
    wb.save(p)
    out = read_xlsx(p, cell_range="A1:D1")
    assert "A1:0" in out
    assert "B1:'0'" in out
    assert "C1:blank" in out
    assert "D1:=A1+1 cache=(none) fmt=0.00" in out


def test_read_xlsx_invalid_range_raises(tmp_path: Path) -> None:
    p = tmp_path / "ok.xlsx"
    _make_wb(p)
    with pytest.raises(ValueError, match="Invalid cell range"):
        read_xlsx(p, cell_range="not-a-range")


def test_read_xlsx_range_on_many_sheets_needs_a_sheet(tmp_path: Path) -> None:
    p = tmp_path / "multi.xlsx"
    wb = openpyxl.Workbook()
    wb.active.title = "First"
    wb.create_sheet("Second")
    wb.save(p)
    with pytest.raises(ValueError, match="needs a sheet"):
        read_xlsx(p, cell_range="A1:A1")


def test_diff_xlsx_reports_changed_cells_only(tmp_path: Path) -> None:
    original = tmp_path / "input.xlsx"
    edited = tmp_path / "output.xlsx"
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Data"
    ws["A1"] = 1
    ws["B1"] = None
    wb.save(original)
    ws["B1"] = 0
    ws["C1"] = "0"
    wb.save(edited)
    out = diff_xlsx(edited, original)
    assert "changed: 2 cell(s)" in out
    assert "Data!B1: input=blank output=0" in out
    assert "Data!C1: input=blank output='0'" in out
    assert "Data!A1:" not in out


def test_diff_xlsx_missing_file_raises(tmp_path: Path) -> None:
    original = tmp_path / "input.xlsx"
    _make_wb(original)
    with pytest.raises(FileNotFoundError, match="No such workbook"):
        diff_xlsx(tmp_path / "missing.xlsx", original)
