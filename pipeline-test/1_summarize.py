"""
Summarize whatever CSV is in input/: one row per column with its type,
blank count, distinct count, and an example value.

Run with F5 in Spyder. No paths to set.
  reads:  input/<the one .csv file you put there>
  writes: output/summary.csv, output/run_log.txt

If something is wrong the script prints one line starting with a code
(E1, E2, ...) or X for an unexpected crash. Relay that line exactly.
"""

import sys
import traceback
from datetime import datetime
from pathlib import Path

import pandas as pd

SCRIPT = "1_summarize.py"


class StepError(Exception):
    """A problem the script checks for, with a short code to relay."""

    def __init__(self, code, message):
        super().__init__(message)
        self.code = code


def project_folder():
    try:
        return Path(__file__).resolve().parent
    except NameError:
        raise StepError("E0", "run the whole file with F5, not a selection or cell")


def find_input_csv(input_dir):
    files = sorted(input_dir.glob("*.csv"))
    if not files:
        raise StepError("E1", f"no .csv file in {input_dir}")
    if len(files) > 1:
        names = ", ".join(f.name for f in files)
        raise StepError("E2", f"input/ has {len(files)} .csv files, expected 1 ({names})")
    return files[0]


def read_csv(path):
    try:
        df = pd.read_csv(path, dtype=str, keep_default_na=False)
    except pd.errors.EmptyDataError:
        raise StepError("E3", f"{path.name} is empty")
    except UnicodeDecodeError:
        df = pd.read_csv(path, dtype=str, keep_default_na=False, encoding="latin-1")
    if df.empty:
        raise StepError("E3", f"{path.name} has headers but no rows")
    return df


def summarize(df):
    rows = []
    for col in df.columns:
        values = df[col].str.strip()
        filled = values[values != ""]
        numeric = pd.to_numeric(filled.str.replace(",", ""), errors="coerce")
        kind = "number" if len(filled) and numeric.notna().all() else "text"
        rows.append({
            "column": col,
            "type": kind,
            "filled": len(filled),
            "blank": len(values) - len(filled),
            "distinct": filled.nunique(),
            "example": filled.iloc[0] if len(filled) else "",
        })
    return pd.DataFrame(rows)


def main(log):
    here = project_folder()
    input_dir = here / "input"
    output_dir = here / "output"
    input_dir.mkdir(exist_ok=True)
    output_dir.mkdir(exist_ok=True)

    source = find_input_csv(input_dir)
    df = read_csv(source)
    log.append(f"read    input/{source.name}: {len(df):,} rows x {len(df.columns)} columns")

    summary = summarize(df)
    out = output_dir / "summary.csv"
    summary.to_csv(out, index=False)
    log.append(f"wrote   output/{out.name}: {len(summary)} rows")
    return output_dir


def crash_line(exc):
    """One retypable line for an unexpected error: where and what."""
    frames = [f for f in traceback.extract_tb(exc.__traceback__) if f.filename.endswith(SCRIPT)]
    where = f"line {frames[-1].lineno} ({frames[-1].name})" if frames else "unknown line"
    return f"X {SCRIPT} {where}: {type(exc).__name__}: {exc}"


def run():
    log = [f"{SCRIPT}  {datetime.now():%Y-%m-%d %H:%M:%S}"]
    output_dir = None
    try:
        output_dir = main(log)
        status = f"OK {SCRIPT}: done"
    except StepError as e:
        status = f"{e.code} {SCRIPT}: {e}"
    except Exception as e:
        status = crash_line(e)
    log.append(status)
    print("\n".join(log[1:]))
    try:
        folder = output_dir or project_folder() / "output"
        folder.mkdir(exist_ok=True)
        (folder / "run_log.txt").write_text("\n".join(log) + "\n", encoding="utf-8")
    except Exception:
        pass
    return status


if __name__ == "__main__":
    run()
