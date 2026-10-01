"""Stack the .xlsx files in input/ into one table, then describe every column
on one screen, with enough detail to make up a realistic fake version.

Put in input/: the .xlsx files to combine (any names). Each file's first
sheet is used. Files with different columns are fine: a column missing from
one file is left blank for that file's rows.

Creates:
  output/combined.csv          every row from every file, plus a source_file
                               column saying which file the row came from
  output/simulation_spec.xlsx  one row per column: its type, how often it is
                               blank, its range or most common values, and an
                               example; the top lines give the row count
"""

# %% Load
import pandas as pd

from kit import load_inputs, save_output

files = load_inputs("*.xlsx")

# %% Combine
# Excel dates come in as "2031-03-16 00:00:00"; the time part is always zero.
combined = pd.concat(
    [df.assign(source_file=name) for name, df in files.items()],
    ignore_index=True,
).fillna("")
combined = combined[["source_file"] + [c for c in combined.columns if c != "source_file"]]
combined = combined.replace(r"^(\d{4}-\d{2}-\d{2}) 00:00:00$", r"\1", regex=True)

save_output(combined, "combined.csv")

# %% Describe each column


def describe(name, values):
    """One spec row: what a fake version of this column should look like."""
    filled = values[values.str.strip() != ""]
    row = {
        "Column": name,
        "Type": "",
        "Blank %": round(100 * (1 - len(filled) / len(values)), 1),
        "Distinct values": filled.nunique(),
        "Min": "",
        "Median": "",
        "Max": "",
        "Most common values (share of filled rows)": "",
        "Example": filled.iloc[0] if len(filled) else "",
    }
    if filled.empty:
        row["Type"] = "always blank"
        return row

    numbers = pd.to_numeric(filled.str.replace(",", ""), errors="coerce")
    dates = pd.to_datetime(filled, errors="coerce", format="mixed")
    distinct = filled.nunique()

    if numbers.notna().mean() >= 0.95 and distinct > 20:
        whole = (numbers.dropna() % 1 == 0).all()
        row["Type"] = "whole number" if whole else "decimal number"
        digits = 0 if whole else 2
        row["Min"] = round(numbers.min(), digits)
        row["Median"] = round(numbers.median(), digits)
        row["Max"] = round(numbers.max(), digits)
    elif dates.notna().mean() >= 0.95 and numbers.isna().mean() >= 0.95:
        row["Type"] = "date"
        row["Min"] = dates.min().date().isoformat()
        row["Median"] = dates.median().date().isoformat()
        row["Max"] = dates.max().date().isoformat()
    elif distinct == len(filled):
        row["Type"] = "ID (unique per row)"
    elif distinct <= 20 or distinct / len(filled) < 0.05:
        row["Type"] = "category"
    else:
        row["Type"] = "free text"

    if row["Type"] in ("category", "free text") or distinct <= 20:
        shares = filled.value_counts(normalize=True).head(5)
        row["Most common values (share of filled rows)"] = ", ".join(
            f"{value} {share:.0%}" for value, share in shares.items()
        )
    if row["Type"] in ("ID (unique per row)", "free text"):
        lengths = filled.str.len()
        row["Min"] = f"{lengths.min()} chars"
        row["Max"] = f"{lengths.max()} chars"
    return row


spec = pd.DataFrame([describe(c, combined[c]) for c in combined.columns])

# %% Columns not in every file
partial = [
    f"{c} (only in {', '.join(n for n, df in files.items() if c in df.columns)})"
    for c in combined.columns
    if c != "source_file" and not all(c in df.columns for df in files.values())
]

# %% Save
per_file = ", ".join(f"{name} ({len(df):,})" for name, df in files.items())
save_output(
    spec,
    "simulation_spec.xlsx",
    notes=[
        "Simulation spec: one row per column of output/combined.csv",
        f"Rows to generate: {len(combined):,}    Columns: {len(spec)}    From: {per_file}",
        "Columns not in every file: " + ("; ".join(partial) or "none"),
    ],
)
