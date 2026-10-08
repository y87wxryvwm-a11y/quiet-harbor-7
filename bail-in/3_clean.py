"""Turn the combined Bloomberg list into one row per outstanding TLAC bond of
the 16 non-US, non-China G-SIB groups, and add the columns the statistics
need. Amounts are in US dollars (Bloomberg was set to USD).

Cleaning steps, in order:
  1. Keep only the 16 G-SIB groups (drops US and Chinese parents that came
     in through subsidiaries abroad).
  2. Drop bonds with nothing outstanding (Amt Out zero or blank).
  3. Drop bonds whose maturity date has already passed.
  4. Drop lines with no ISIN that repeat another line of the same bond
     (same parent, coupon, maturity, currency and amount, with an ISIN).
  5. Count each 144A / Reg S pair once. The same deal is often listed twice,
     once for US buyers (144A) and once for buyers abroad (Reg S), and both
     lines carry the full amount. Lines with the same parent, coupon,
     maturity, currency and amount are merged when one is 144A or Reg S, or
     when one has a US ISIN and another doesn't.

Added columns:
  G-SIB             short group name
  Home country      the group's home country (not the issuing subsidiary's)
  Type              AT1 (junior, incl. CoCos), Tier 2 (subordinated), Senior
  Perpetual         Yes if the bond has no maturity date
  Years to maturity from today; blank for perpetuals
  US market         Yes if sold into the US market: Series is 144A, or the
                    ISIN is US + a digit (a US CUSIP) and Series isn't Reg S.
                    US + a letter is a foreign-style code often used for
                    Reg S lines, so it alone doesn't count. A merged pair is
                    Yes if any of its lines is.
  Series clean      Series in capitals, #N/A as blank
  Currency group    USD, EUR, GBP, CAD, JPY, AUD, CHF or Other
  Lines merged      how many Bloomberg lines this row stands for (usually 1)

Put in input/: nothing new. Reads output/combined.csv from 1_combine.py.

Creates:
  output/clean.csv           the cleaned bonds, one row each
  output/clean_report.xlsx   what cleaning did, three sheets:
                             Steps   bonds and dollars removed at each step
                             Merged  the largest 144A / Reg S pairs merged
                             Kept    same-terms lines NOT merged, to check
"""

# %% Load
from datetime import date

import pandas as pd

from kit import load_output, save_output

df = load_output("combined.csv", require=["Ultimate Parent", "Amt Out", "Maturity", "ISIN", "Series"])

# Ultimate Parent starts with -> (short name, home country).
# Bloomberg cuts parent names at 30 characters, so match on the start.
GSIBS = {
    "Royal Bank of Canada": ("RBC", "Canada"),
    "Toronto-Dominion": ("TD", "Canada"),
    "BNP Paribas": ("BNP Paribas", "France"),
    "Credit Agricole": ("Credit Agricole", "France"),
    "Societe Generale": ("Societe Generale", "France"),
    "Groupe BPCE": ("BPCE", "France"),
    "Deutsche Bank": ("Deutsche Bank", "Germany"),
    "Mitsubishi UFJ": ("MUFG", "Japan"),
    "Mizuho": ("Mizuho", "Japan"),
    "Sumitomo Mitsui": ("SMFG", "Japan"),
    "ING Groep": ("ING", "Netherlands"),
    "Banco Santander": ("Santander", "Spain"),
    "UBS Group": ("UBS", "Switzerland"),
    "Barclays": ("Barclays", "United Kingdom"),
    "HSBC": ("HSBC", "United Kingdom"),
    "Standard Chartered": ("Standard Chartered", "United Kingdom"),
}
NA = "#N/A Field Not Applicable"

df["Amt Out"] = pd.to_numeric(df["Amt Out"].str.replace(",", ""), errors="coerce")
df["Coupon"] = pd.to_numeric(df["Coupon"], errors="coerce")
df["Maturity"] = pd.to_datetime(df["Maturity"].replace(NA, ""), errors="coerce", format="mixed")
steps = [("Bloomberg lines (both files)", len(df), df["Amt Out"].sum())]


def step(name, keep):
    """Apply one cleaning step and record what it removed."""
    global df
    df = df[keep].copy()
    steps.append((name, len(df), df["Amt Out"].sum()))


# %% 1. The 16 G-SIB groups
match = df["Ultimate Parent"].map(lambda p: next((v for k, v in GSIBS.items() if p.startswith(k)), None))
dropped_parents = df.loc[match.isna(), "Ultimate Parent"].value_counts()
df["G-SIB"] = match.str[0]
df["Home country"] = match.str[1]
step("Keep the 16 G-SIB groups", match.notna())

# %% 2-3. Outstanding today
step("Drop: nothing outstanding", df["Amt Out"] > 0)
step("Drop: already matured", ~(df["Maturity"] < pd.Timestamp(date.today())))

# %% 4. Lines without an ISIN that repeat a bond
terms = ["Ultimate Parent", "Coupon", "Maturity", "Currency", "Amt Out"]


def same_terms():
    """Group lines with the same parent, coupon, maturity, currency, amount."""
    return df.fillna({"Maturity": pd.Timestamp("2200-01-01")}).groupby(terms, dropna=False)


has_isin = df["ISIN"].str.len() == 12
repeats = same_terms()["ISIN"].transform(lambda s: (s.str.len() == 12).any())
step("Drop: no-ISIN line repeating a bond", has_isin | ~repeats)

# %% 5. 144A / Reg S pairs
df["Series clean"] = df["Series"].str.upper().str.replace(" ", "").replace({NA.upper().replace(" ", ""): ""})
df["US ISIN"] = df["ISIN"].str.startswith("US")
group = same_terms()
df["Lines merged"] = group["ISIN"].transform("size")
pair = (
    group["Series clean"].transform(lambda s: s.isin(["144A", "REGS"]).any())
    | (group["US ISIN"].transform("any") & ~group["US ISIN"].transform("all"))
)
df["US market"] = (df["Series clean"] == "144A") | (
    df["ISIN"].str.match(r"US\d") & (df["Series clean"] != "REGS")
)
df["US market"] = df["US market"] | (pair & same_terms()["US market"].transform("any"))
df["Twin"] = (df["Lines merged"] > 1) & pair
df["Group id"] = group.ngroup()

merged = (
    df[df["Twin"]]
    .groupby("Group id")
    .agg(
        **{
            "G-SIB": ("G-SIB", "first"),
            "Bond": ("Sec Short Desc", "first"),
            "Amt Out ($m)": ("Amt Out", "first"),
            "Lines": ("ISIN", "size"),
            "Series": ("Series clean", lambda s: ", ".join(s)),
            "ISINs": ("ISIN", lambda s: ", ".join(s)),
        }
    )
    .sort_values("Amt Out ($m)", ascending=False)
)
kept = (
    df[(df["Lines merged"] > 1) & ~df["Twin"]]
    .groupby("Group id")
    .agg(
        **{
            "G-SIB": ("G-SIB", "first"),
            "Bond": ("Sec Short Desc", "first"),
            "Amt Out ($m)": ("Amt Out", "first"),
            "Lines": ("ISIN", "size"),
            "Series": ("Series clean", lambda s: ", ".join(s)),
            "ISINs": ("ISIN", lambda s: ", ".join(s)),
        }
    )
    .sort_values("Amt Out ($m)", ascending=False)
)
# Keep one line per pair, preferring the US one; other lines stand for themselves.
df = df.sort_values("US market", ascending=False)
step("Count each 144A / Reg S pair once", ~(df["Twin"] & df.duplicated("Group id")))
df.loc[~df["Twin"], "Lines merged"] = 1

# %% Added columns
perpetual = df["Maturity"].isna()
df["Type"] = "Senior"
df.loc[df["MiFID Bond Seniority"] == "SBOD", "Type"] = "Tier 2"
df.loc[(df["MiFID Bond Seniority"] == "JUND") | perpetual, "Type"] = "AT1"
df["Perpetual"] = perpetual.map({True: "Yes", False: "No"})
df["Years to maturity"] = ((df["Maturity"] - pd.Timestamp(date.today())).dt.days / 365.25).round(2)
df["US market"] = df["US market"].map({True: "Yes", False: "No"})
main = ["USD", "EUR", "GBP", "CAD", "JPY", "AUD", "CHF"]
df["Currency group"] = df["Currency"].where(df["Currency"].isin(main), "Other")
df["Maturity"] = df["Maturity"].dt.strftime("%Y-%m-%d")
df = df.drop(columns=["US ISIN", "Twin", "Group id"]).sort_values(["G-SIB", "Maturity"])

# %% Report
report = pd.DataFrame(steps, columns=["Step", "Bonds left", "Amt Out left"])
report.insert(1, "Bonds removed", (-report["Bonds left"].diff()).fillna(0).astype(int))
report["Amt Out removed ($bn)"] = (-report["Amt Out left"].diff() / 1e9).fillna(0).round(1)
report["Amt Out left ($bn)"] = (report["Amt Out left"] / 1e9).round(1)
report = report.drop(columns="Amt Out left")
for table in (merged, kept):
    table["Amt Out ($m)"] = (table["Amt Out ($m)"] / 1e6).round(1)

# %% Save
save_output(df, "clean.csv")
save_output(
    {"Steps": report, "Merged": merged.head(30), "Kept": kept.head(30)},
    "clean_report.xlsx",
    notes={
        "Steps": [
            "Cleaning steps (amounts in US dollars)",
            "Parents dropped in step 1: "
            + ", ".join(f"{p} ({n})" for p, n in dropped_parents.items()),
        ],
        "Merged": [f"144A / Reg S pairs counted once: {len(merged)} deals, "
                   f"{int(merged['Lines'].sum()) - len(merged)} lines removed; largest 30 shown"],
        "Kept": [
            f"Same parent, coupon, maturity, currency and amount, but NOT merged: {len(kept)} groups, largest 30",
            "No 144A / Reg S sign. Likely separate notes with equal terms; check the biggest.",
        ],
    },
)
