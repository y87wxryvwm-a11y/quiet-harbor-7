"""
Shared file handling for every project in this repo, so analysis scripts
don't have to deal with file paths.

Each project folder has two data folders next to its scripts:
  input/   where you put the files a script reads
  output/  where the script saves its results
Each is created automatically the first time it is needed. Git ignores
them, so pulling new code never touches your data.

Scripts use these functions:
  df = load_input("*.csv")              # read the one matching file in input/
  files = load_inputs("*.xlsx")         # read every matching file in input/
  save_output(df, "results.csv")        # save to output/

This file creates nothing except those two folders.

One-time Spyder setup so scripts can find this file:
Tools > PYTHONPATH manager > Add path > choose the research folder.
"""

import os
import sys
from pathlib import Path

import pandas as pd


class InputProblem(Exception):
    """Something is wrong with the files in input/. The message says what."""


def _project_dir():
    # The folder of the script that called load_input/save_output.
    # Running one cell in Spyder may not tell us the script, so fall back
    # to Spyder's working folder, which is the script's folder by default.
    frame = sys._getframe(1)
    while frame:
        path = frame.f_globals.get("__file__")
        if path and Path(path).resolve() != Path(__file__).resolve():
            return Path(path).resolve().parent
        frame = frame.f_back
    return Path(os.getcwd())


def _folder(name):
    folder = _project_dir() / name
    folder.mkdir(exist_ok=True)
    return folder


def load_input(pattern="*.csv", require=None):
    """Read the one file in input/ matching `pattern` (e.g. "*.csv", "*.xlsx").

    Every value is read as text, exactly as it appears in the file, so nothing
    is silently converted. `require` is an optional list of column names that
    must be present.
    """
    folder = _folder("input")
    matches = sorted(folder.glob(pattern))
    if not matches:
        raise InputProblem(f"No {pattern} file found in {folder}")
    if len(matches) > 1:
        names = ", ".join(m.name for m in matches)
        raise InputProblem(f"Expected one {pattern} file in {folder}, found {len(matches)}: {names}")
    return _read(matches[0], require)


def load_inputs(pattern="*.xlsx", require=None):
    """Read every file in input/ matching `pattern`, in name order.

    Returns {file name: table}. Same rules as load_input for each file.
    """
    folder = _folder("input")
    matches = sorted(folder.glob(pattern))
    if not matches:
        raise InputProblem(f"No {pattern} files found in {folder}")
    return {path.name: _read(path, require) for path in matches}


def _read(path, require):
    if path.suffix.lower() in (".xlsx", ".xls"):
        df = pd.read_excel(path, dtype=str, keep_default_na=False)
    else:
        try:
            df = pd.read_csv(path, dtype=str, keep_default_na=False)
        except UnicodeDecodeError:
            df = pd.read_csv(path, dtype=str, keep_default_na=False, encoding="latin-1")
        except pd.errors.EmptyDataError:
            raise InputProblem(f"{path.name} is empty")
    if df.empty:
        raise InputProblem(f"{path.name} has column names but no rows")

    missing = [c for c in (require or []) if c not in df.columns]
    if missing:
        raise InputProblem(
            f"{path.name} is missing column(s) {', '.join(missing)}; "
            f"it has: {', '.join(df.columns)}"
        )

    print(f"Loaded input/{path.name}: {len(df):,} rows, {len(df.columns)} columns")
    return df


def save_output(df, filename, notes=None):
    """Save a table to output/ as .csv or .xlsx, based on the filename.

    For .xlsx: bold header row that stays put when scrolling, columns sized
    to fit. `notes` is an optional list of lines written above the table
    (the first one bold, as a title).
    """
    path = _folder("output") / filename
    if path.suffix.lower() != ".xlsx":
        df.to_csv(path, index=False)
    else:
        from openpyxl.styles import Alignment, Font, PatternFill
        from openpyxl.utils import get_column_letter

        top = len(notes) + 1 if notes else 0
        with pd.ExcelWriter(path, engine="openpyxl") as writer:
            df.to_excel(writer, index=False, startrow=top)
            sheet = writer.sheets["Sheet1"]
            for i, line in enumerate(notes or [], start=1):
                sheet.cell(i, 1, line).font = Font(bold=(i == 1), size=13 if i == 1 else 11)
            for cell in sheet[top + 1]:
                cell.font = Font(bold=True, color="FFFFFF")
                cell.fill = PatternFill("solid", fgColor="305496")
                cell.alignment = Alignment(wrap_text=True, vertical="top")
            for i, name in enumerate(df.columns, start=1):
                longest = max([len(str(name))] + [len(str(v)) for v in df[name]])
                sheet.column_dimensions[get_column_letter(i)].width = min(longest + 2, 45)
            sheet.freeze_panes = sheet.cell(top + 2, 2)
    print(f"Saved output/{filename}: {len(df):,} rows")
    return path
