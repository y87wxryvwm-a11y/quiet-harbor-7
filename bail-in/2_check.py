"""Check the combined Bloomberg data before computing any statistics. Answers:
which parents are in it, whether amounts are in each bond's own currency or
already converted, how bond types are coded, and what needs cleaning
(perpetuals, matured bonds, duplicates, missing values).

Put in input/: nothing new. Reads output/combined.csv from 1_combine.py.

Creates:
  output/checks.xlsx   six sheets, each meant to fit one screen:
                       Parents     bonds per ultimate parent, with issuers,
                                   countries and currencies
                       Currencies  size of Amt Out per currency (tells whether
                                   amounts were converted to one currency)
                       Values      every value of the short coded columns
                       Seniority   bond types by MiFID seniority
                       Series      the 30 most common Series values
                       Checks      counts of problems to clean, with examples
"""

# %% Load
from datetime import date

import pandas as pd

from kit import load_output, save_output

df = load_output("combined.csv", require=["Ultimate Parent", "Amt Out", "Currency"])

NA = "#N/A Field Not Applicable"
amt_out = pd.to_numeric(df["Amt Out"].str.replace(",", ""), errors="coerce")
amt_issued = pd.to_numeric(df["Amt Issued"].str.replace(",", ""), errors="coerce")
coupon = pd.to_numeric(df["Coupon"], errors="coerce")
maturity = pd.to_datetime(df["Maturity"], errors="coerce", format="mixed")


def top(values, n=3):
    """The n most common values, with counts, as one line of text."""
    counts = values[values != ""].value_counts().head(n)
    return ", ".join(f"{v} ({c})" for v, c in counts.items())


# %% Parents
parents = (
    df.groupby("Ultimate Parent")
    .agg(
        Bonds=("Ultimate Parent", "size"),
        Issuers=("Issuer Name", "nunique"),
        Countries=("Cntry of Domicile", top),
        Currencies=("Currency", top),
    )
    .sort_values("Bonds", ascending=False)
    .reset_index()
)
parents.insert(2, "Share", (parents["Bonds"] / len(df)).map("{:.1%}".format))

# %% Currencies
# If amounts are in each bond's own currency, yen medians are ~150x dollar
# medians. If Bloomberg converted them, all currencies look alike.
by_cur = df.assign(amt=amt_out, whole=(amt_out % 1 == 0)).groupby("Currency")
currencies = (
    by_cur.agg(
        Bonds=("Currency", "size"),
        Min=("amt", "min"),
        Median=("amt", "median"),
        Max=("amt", "max"),
        Whole=("whole", "mean"),
        Example=("Sec Short Desc", "first"),
    )
    .sort_values("Bonds", ascending=False)
    .reset_index()
)
for col in ["Min", "Median", "Max"]:
    currencies[col] = currencies[col].map("{:,.0f}".format)
currencies["Whole"] = currencies["Whole"].map("{:.0%}".format)
currencies = currencies.rename(columns={"Min": "Amt Out min", "Median": "Amt Out median",
                                        "Max": "Amt Out max", "Whole": "% whole numbers"})

# %% Values of the coded columns
values = pd.concat(
    [
        df[col].value_counts().rename_axis("Value").reset_index(name="Bonds").assign(Column=col)
        for col in ["MiFID Bond Seniority", "Coupon Type", "Mty Type", "BBG Composite"]
    ]
)[["Column", "Value", "Bonds"]]
values["Share"] = (values["Bonds"] / len(df)).map("{:.1%}".format)

# %% Bond types by seniority
seniority = pd.concat(
    [
        pd.crosstab("Mty Type: " + df["Mty Type"], df["MiFID Bond Seniority"]),
        pd.crosstab("Coupon Type: " + df["Coupon Type"], df["MiFID Bond Seniority"]),
    ]
).rename_axis(index="Bond feature", columns=None).reset_index()

# %% Series
series = df["Series"].value_counts().head(30).rename_axis("Series").reset_index(name="Bonds")
series["Share"] = (series["Bonds"] / len(df)).map("{:.1%}".format)
series["Top parents"] = series["Series"].map(lambda s: top(df.loc[df["Series"] == s, "Ultimate Parent"], 2))

# %% Checks
real_isin = df["ISIN"].where(df["ISIN"].str.len() == 12, "")
twins = df.duplicated(["Ultimate Parent", "Coupon", "Maturity", "Currency", "Amt Out"], keep=False)
checks = {
    "Amt Out blank": amt_out.isna(),
    "Amt Out is zero": amt_out == 0,
    "Amt Out larger than Amt Issued": amt_out > amt_issued,
    "Amt Issued blank": amt_issued.isna(),
    "Amt Out not a whole number": amt_out % 1 > 0,
    "Maturity not a date": maturity.isna(),
    "Maturity already passed": maturity < pd.Timestamp(date.today()),
    "Mty Type says perpetual": df["Mty Type"].str.contains("PERP"),
    "Perpetual but Maturity is a date": df["Mty Type"].str.contains("PERP") & maturity.notna(),
    "ISIN missing or #N/A": real_isin == "",
    "ISIN appears more than once": real_isin.duplicated(keep=False) & (real_isin != ""),
    "Bloomberg ID appears more than once": df["Bloomberg ID"].duplicated(keep=False),
    "Same parent, coupon, maturity, currency, amount": twins,
    "CUSIP same as Bloomberg ID": df["CUSIP"] == df["Bloomberg ID"],
    "CUSIP different from Bloomberg ID": df["CUSIP"] != df["Bloomberg ID"],
    "ISIN starts with US": real_isin.str.startswith("US"),
    "ISIN starts with XS (international)": real_isin.str.startswith("XS"),
    "Series mentions 144A": df["Series"].str.contains("144A"),
    "Series mentions REG S": df["Series"].str.upper().str.replace(" ", "").str.contains("REGS"),
    "Zero coupon type but Coupon above 0": (df["Coupon Type"] == "ZERO COUPON") & (coupon > 0),
    "Coupon above 15": coupon > 15,
}
checks = pd.DataFrame(
    [
        {
            "Check": name,
            "Bonds": int(hit.sum()),
            "Share": f"{hit.mean():.1%}",
            "Examples (Sec Short Desc | Maturity | Amt Out)": "; ".join(
                " | ".join(row) for row in df.loc[hit, ["Sec Short Desc", "Maturity", "Amt Out"]].head(3).values
            ),
        }
        for name, hit in checks.items()
    ]
)

# %% Save
save_output(
    {
        "Parents": parents,
        "Currencies": currencies,
        "Values": values,
        "Seniority": seniority,
        "Series": series,
        "Checks": checks,
    },
    "checks.xlsx",
    notes={
        "Parents": [f"Bonds per ultimate parent ({len(df):,} bonds, {len(parents)} parents)"],
        "Currencies": ["Amt Out by currency: if JPY medians are ~150x USD medians, amounts are in each bond's own currency"],
        "Values": ["Every value of the coded columns"],
        "Seniority": ["Bonds by MiFID seniority (SNDB senior, SBOD subordinated, JUND junior)"],
        "Series": [f"30 most common Series values (of {df['Series'].nunique()})"],
        "Checks": [f"Things to clean before statistics (today = {date.today()})"],
    },
)
