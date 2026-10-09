"""Stack the .xlsx files in input/ into one table.

Put in input/: the .xlsx files to combine (any names). Each file's first
sheet is used. Files with different columns are fine: a column missing from
one file is left blank for that file's rows.

Creates:
  output/combined.csv          every row from every file, columns from most to
                               least important, plus a source_file column (last)
                               saying which file the row came from
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
# Most important first: identifiers used to tell bonds apart, then the
# columns the analysis uses, then the rest.
ORDER = [
    "Ultimate Parent", "Issuer Name", "Sec Short Desc", "ISIN", "Series",
    "Amt Out", "Currency", "MiFID Bond Seniority", "Maturity", "Mty Type", "Coupon", "Coupon Type", "BBG Composite",
    "Ticker", "CUSIP", "Bloomberg ID", "TLAC / MREL Desig", "Amt Issued", "Cntry of Domicile",
]
first = [c for c in ORDER if c in combined.columns]
combined = combined[first + [c for c in combined.columns if c not in first + ["source_file"]] + ["source_file"]]
combined = combined.replace(r"^(\d{4}-\d{2}-\d{2}) 00:00:00$", r"\1", regex=True)

# %% Save
save_output(combined, "combined.csv")
