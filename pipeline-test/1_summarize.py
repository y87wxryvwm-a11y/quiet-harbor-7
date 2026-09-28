"""
Summarize a dataset: for each column, its type, how many values are filled
or blank (and the percent blank), how many are distinct, and one example value.

Put one .csv file in input/, then run this file.

Creates:
  output/summary.csv   one row per column of your file, with the counts above
"""

# %% Load
import pandas as pd

from kit import load_input, save_output

df = load_input("*.csv")

# %% Summarize each column
rows = []
for col in df.columns:
    filled = df[col].str.strip().replace("", pd.NA).dropna()
    is_number = pd.to_numeric(filled.str.replace(",", ""), errors="coerce").notna().all()
    rows.append({
        "column": col,
        "type": "number" if len(filled) and is_number else "text",
        "filled": len(filled),
        "blank": len(df) - len(filled),
        "pct_blank": round(100 * (len(df) - len(filled)) / len(df), 1),
        "distinct": filled.nunique(),
        "example": filled.iloc[0] if len(filled) else "",
    })
summary = pd.DataFrame(rows)

# %% Save
save_output(summary, "summary.csv")
