"""
Shared file handling for every project in this repo, so analysis scripts
don't have to deal with file paths.

Each project folder has two data folders next to its scripts:
  input/   where you put the files a script reads
  output/  where the script saves its results
Each is created automatically the first time it is needed. Git ignores
them, so pulling new code never touches your data.

Scripts use two functions:
  df = load_input("*.csv")              # read the one matching file in input/
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
    path = matches[0]

    if path.suffix.lower() in (".xlsx", ".xls"):
        df = pd.read_excel(path, dtype=str, keep_default_na=False)
    else:
        try:
            df = pd.read_csv(path, dtype=str, keep_default_na=False)
        except UnicodeDecodeError:
            df = pd.read_csv(path, dtype=str, keep_default_na=False, encoding="latin-1")
        except pd.errors.EmptyDataError:
            raise InputProblem(f"{path.name} is empty")

    missing = [c for c in (require or []) if c not in df.columns]
    if missing:
        raise InputProblem(
            f"{path.name} is missing column(s) {', '.join(missing)}; "
            f"it has: {', '.join(df.columns)}"
        )

    print(f"Loaded input/{path.name}: {len(df):,} rows, {len(df.columns)} columns")
    return df


def save_output(df, filename):
    """Save a table to output/ as .csv or .xlsx, based on the filename."""
    path = _folder("output") / filename
    if path.suffix.lower() == ".xlsx":
        df.to_excel(path, index=False)
    else:
        df.to_csv(path, index=False)
    print(f"Saved output/{filename}: {len(df):,} rows")
    return path
